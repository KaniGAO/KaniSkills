"""SQLite 审计与校验存储层。

职责：
- 建表（raw_pulls / reconciled_quotes / expected_central_bank / earnings_calendar）
- 写入原始抓取记录（追加不覆盖，保留完整历史便于审计追溯）
- 写入/读取发布前已校验报价
- 读取央行预期利率、财报日历（去硬编码 TBD）

设计要点：
- schema 字段与 PostgreSQL 兼容，未来迁移仅需换连接串。
- raw_pulls 不做 UPDATE，每次 run 产生新行。
- DB 文件默认落在技能根目录 data/markets.db，首次运行自动建表。
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# 技能根目录：scripts/storage/db.py → 上溯两级为技能根
SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = SKILL_ROOT / "data" / "markets.db"
SEED_SQL_PATH = SKILL_ROOT / "config" / "seed.sql"


SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_pulls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT,
    source      TEXT,
    ticker      TEXT,
    captured_at TEXT,
    is_settled  INTEGER,
    close       REAL,
    prev_close  REAL
);

CREATE TABLE IF NOT EXISTS reconciled_quotes (
    as_of_date  TEXT,
    ticker      TEXT,
    value       REAL,
    change_pct  REAL,
    confidence  TEXT,
    PRIMARY KEY (as_of_date, ticker)
);

CREATE TABLE IF NOT EXISTS expected_central_bank (
    region        TEXT,
    meeting_date  TEXT,
    expected_rate TEXT,
    PRIMARY KEY (region, meeting_date)
);

CREATE TABLE IF NOT EXISTS earnings_calendar (
    ticker       TEXT,
    report_date  TEXT,
    confirmed    INTEGER,
    PRIMARY KEY (ticker, report_date)
);

CREATE INDEX IF NOT EXISTS idx_raw_pulls_run ON raw_pulls(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_pulls_ticker ON raw_pulls(ticker);
"""


def _connect(db_path: str = None) -> sqlite3.Connection:
    path = db_path or os.environ.get("MARKETS_DB_PATH") or str(DEFAULT_DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = None) -> None:
    """建表 + 加载 seed 数据（央行预期/财报日历）。幂等。"""
    conn = _connect(db_path)
    try:
        conn.executescript(SCHEMA)
        if SEED_SQL_PATH.exists():
            conn.executescript(SEED_SQL_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def write_raw_pull(run_id: str, source: str, ticker: str, close: float,
                   prev_close: float, is_settled: bool = True,
                   captured_at: str = None, db_path: str = None) -> None:
    """追加一条原始抓取记录。失败不阻断主流程。"""
    try:
        conn = _connect(db_path)
        try:
            conn.execute(
                "INSERT INTO raw_pulls (run_id, source, ticker, captured_at, is_settled, close, prev_close) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    source,
                    ticker,
                    captured_at or datetime.now(timezone.utc).isoformat(),
                    1 if is_settled else 0,
                    float(close) if close is not None else None,
                    float(prev_close) if prev_close is not None else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"  [DB] write_raw_pull failed for {source}/{ticker}: {e}")


def write_raw_pulls_batch(rows: list[dict], db_path: str = None) -> None:
    """批量写入原始抓取记录。rows: [{run_id, source, ticker, close, prev_close, is_settled, captured_at}]"""
    if not rows:
        return
    try:
        conn = _connect(db_path)
        try:
            conn.executemany(
                "INSERT INTO raw_pulls (run_id, source, ticker, captured_at, is_settled, close, prev_close) "
                "VALUES (:run_id, :source, :ticker, :captured_at, :is_settled, :close, :prev_close)",
                [
                    {
                        "run_id": r.get("run_id"),
                        "source": r.get("source"),
                        "ticker": r.get("ticker"),
                        "captured_at": r.get("captured_at") or datetime.now(timezone.utc).isoformat(),
                        "is_settled": 1 if r.get("is_settled", True) else 0,
                        "close": r.get("close"),
                        "prev_close": r.get("prev_close"),
                    }
                    for r in rows
                ],
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"  [DB] write_raw_pulls_batch failed: {e}")


def upsert_reconciled_quote(as_of_date: str, ticker: str, value: float,
                            change_pct: float, confidence: str, db_path: str = None) -> None:
    """写入/更新一条已校验报价。"""
    try:
        conn = _connect(db_path)
        try:
            conn.execute(
                "INSERT INTO reconciled_quotes (as_of_date, ticker, value, change_pct, confidence) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(as_of_date, ticker) DO UPDATE SET "
                "value=excluded.value, change_pct=excluded.change_pct, confidence=excluded.confidence",
                (as_of_date, ticker, value, change_pct, confidence),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"  [DB] upsert_reconciled_quote failed for {ticker}: {e}")


def get_expected_central_bank_rate(region: str, meeting_date: str, db_path: str = None) -> str:
    """查询某央行某次会议的预期利率，未命中返回 'TBD'。"""
    try:
        conn = _connect(db_path)
        try:
            row = conn.execute(
                "SELECT expected_rate FROM expected_central_bank WHERE region=? AND meeting_date=?",
                (region, meeting_date),
            ).fetchone()
            return row["expected_rate"] if row else "TBD"
        finally:
            conn.close()
    except Exception:
        return "TBD"


def get_all_expected_central_bank(db_path: str = None) -> dict:
    """返回 {(region, meeting_date): expected_rate} 字典。"""
    try:
        conn = _connect(db_path)
        try:
            rows = conn.execute(
                "SELECT region, meeting_date, expected_rate FROM expected_central_bank"
            ).fetchall()
            return {(r["region"], r["meeting_date"]): r["expected_rate"] for r in rows}
        finally:
            conn.close()
    except Exception:
        return {}


def get_earnings_calendar(db_path: str = None) -> list[dict]:
    """返回 [{ticker, report_date, confirmed}]。"""
    try:
        conn = _connect(db_path)
        try:
            rows = conn.execute(
                "SELECT ticker, report_date, confirmed FROM earnings_calendar"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    except Exception:
        return []


def get_raw_pulls(run_id: str = None, ticker: str = None, db_path: str = None) -> list[dict]:
    """审计查询：按 run_id 或 ticker 取原始抓取记录。"""
    try:
        conn = _connect(db_path)
        try:
            if run_id:
                rows = conn.execute(
                    "SELECT * FROM raw_pulls WHERE run_id=? ORDER BY id", (run_id,)
                ).fetchall()
            elif ticker:
                rows = conn.execute(
                    "SELECT * FROM raw_pulls WHERE ticker=? ORDER BY id DESC LIMIT 50", (ticker,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM raw_pulls ORDER BY id DESC LIMIT 100").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    except Exception:
        return []
