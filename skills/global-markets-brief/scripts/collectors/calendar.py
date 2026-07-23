"""央行事件日历生成"""
from datetime import datetime, timedelta, timezone


def generate_calendar() -> list[dict]:
    """生成未来 2 个月的宏观事件日历"""
    now = datetime.now(timezone.utc)
    hkt = now + timedelta(hours=8)
    today = hkt.strftime("%Y-%m-%d")

    # 依据实际经济数据构建的事件列表
    events = [
        # July 2026
        {"date": "2026-07-22", "event": "Alphabet Q2 Earnings", "country": "US", "type": "earnings", "importance": 3},
        {"date": "2026-07-22", "event": "Tesla Q2 Earnings", "country": "US", "type": "earnings", "importance": 3},
        {"date": "2026-07-23", "event": "ECB Monetary Policy Meeting", "country": "Eurozone", "type": "central_bank", "importance": 5},
        {"date": "2026-07-23", "event": "Intel Q2 Earnings", "country": "US", "type": "earnings", "importance": 2},
        {"date": "2026-07-25", "event": "US PCE Price Index (Jun)", "country": "US", "type": "economic", "importance": 4},
        {"date": "2026-07-25", "event": "Tokyo CPI (Jul)", "country": "Japan", "type": "economic", "importance": 3},
        {"date": "2026-07-28-29", "event": "FOMC Meeting", "country": "US", "type": "central_bank", "importance": 5},
        {"date": "2026-07-30", "event": "BOE Monetary Policy Meeting", "country": "UK", "type": "central_bank", "importance": 5},
        {"date": "2026-07-30-31", "event": "BOJ Monetary Policy Meeting", "country": "Japan", "type": "central_bank", "importance": 5},
        {"date": "2026-07-31", "event": "BOJ Outlook Report", "country": "Japan", "type": "central_bank", "importance": 4},
        {"date": "2026-07-31", "event": "Eurozone GDP Q2 (Prelim)", "country": "Eurozone", "type": "economic", "importance": 4},
        {"date": "2026-07-31", "event": "Eurozone CPI Jul (Flash)", "country": "Eurozone", "type": "economic", "importance": 4},
        {"date": "2026-07-31", "event": "China NBS PMI (Jul)", "country": "China", "type": "economic", "importance": 4},

        # August 2026
        {"date": "2026-08-01", "event": "US ISM Manufacturing PMI (Jul)", "country": "US", "type": "economic", "importance": 4},
        {"date": "2026-08-05", "event": "US ISM Services PMI (Jul)", "country": "US", "type": "economic", "importance": 4},
        {"date": "2026-08-07", "event": "US Nonfarm Payrolls (Jul)", "country": "US", "type": "economic", "importance": 5},
        {"date": "2026-08-09", "event": "China CPI / PPI (Jul)", "country": "China", "type": "economic", "importance": 4},
        {"date": "2026-08-12", "event": "US CPI (Jul)", "country": "US", "type": "economic", "importance": 5},
        {"date": "2026-08-13", "event": "US PPI (Jul)", "country": "US", "type": "economic", "importance": 3},
        {"date": "2026-08-14", "event": "US Retail Sales (Jul)", "country": "US", "type": "economic", "importance": 3},
        {"date": "2026-08-18", "event": "Japan Q2 GDP (Prelim)", "country": "Japan", "type": "economic", "importance": 4},
        {"date": "2026-08-20", "event": "PBOC LPR Decision", "country": "China", "type": "central_bank", "importance": 3},
        {"date": "2026-08-20", "event": "FOMC Minutes (Jul 28-29)", "country": "US", "type": "central_bank", "importance": 4},
        {"date": "2026-08-25", "event": "Jackson Hole Symposium (tentative)", "country": "US", "type": "central_bank", "importance": 5},
        {"date": "2026-08-27", "event": "US PCE (Jul)", "country": "US", "type": "economic", "importance": 4},
        {"date": "2026-08-31", "event": "China NBS PMI (Aug)", "country": "China", "type": "economic", "importance": 4},

        # September 2026
        {"date": "2026-09-01", "event": "US ISM Manufacturing PMI (Aug)", "country": "US", "type": "economic", "importance": 4},
        {"date": "2026-09-03", "event": "US Nonfarm Payrolls (Aug)", "country": "US", "type": "economic", "importance": 5},
        {"date": "2026-09-09", "event": "Canada BoC Rate Decision", "country": "Canada", "type": "central_bank", "importance": 3},
        {"date": "2026-09-10", "event": "ECB Monetary Policy Meeting", "country": "Eurozone", "type": "central_bank", "importance": 5},
        {"date": "2026-09-11", "event": "US CPI (Aug)", "country": "US", "type": "economic", "importance": 5},
        {"date": "2026-09-15", "event": "China Industrial Production (Aug)", "country": "China", "type": "economic", "importance": 3},
        {"date": "2026-09-17", "event": "FOMC Meeting (rate decision)", "country": "US", "type": "central_bank", "importance": 5},
        {"date": "2026-09-18", "event": "BOJ Monetary Policy Meeting", "country": "Japan", "type": "central_bank", "importance": 5},
        {"date": "2026-09-19", "event": "BOE Monetary Policy Meeting", "country": "UK", "type": "central_bank", "importance": 5},
        {"date": "2026-09-20", "event": "PBOC LPR Decision", "country": "China", "type": "central_bank", "importance": 3},
    ]

    # 过滤：只保留今天之后的事件，限定 25 条
    cutoff = (hkt + timedelta(days=60)).strftime("%Y-%m-%d")
    filtered = [e for e in events if e["date"][:10] >= today and e["date"][:10] <= cutoff]
    filtered.sort(key=lambda x: x["date"])

    return filtered[:25]


# 财报事件名 → ticker 映射（用于 DB 表驱动覆盖硬编码日期）
_EARNINGS_TICKER = {
    "Alphabet Q2 Earnings": "GOOGL",
    "Tesla Q2 Earnings": "TSLA",
    "Intel Q2 Earnings": "INTC",
}


def overlay_db_earnings(events: list[dict]) -> list[dict]:
    """用 DB earnings_calendar 表覆盖硬编码财报日期（去硬编码）。

    DB 未初始化或无数据时原样返回。命中即以 DB report_date 为准。
    """
    try:
        from storage import db
        db_rows = {r["ticker"]: r["report_date"] for r in db.get_earnings_calendar()}
    except Exception:
        return events

    if not db_rows:
        return events

    updated = []
    for ev in events:
        if ev.get("type") == "earnings":
            tk = _EARNINGS_TICKER.get(ev["event"])
            if tk and tk in db_rows:
                ev = {**ev, "date": db_rows[tk]}
        updated.append(ev)
    return updated
