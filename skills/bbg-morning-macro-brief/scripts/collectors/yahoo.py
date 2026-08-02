"""Yahoo Finance 市场数据采集（修复版）

关键修复：
1. 结算守卫：判断最新日线是否已定稿；若仍处交易时段（in-progress）则丢弃当日 bar，
   改用上一根已定稿日线作为 current，根治"抓到盘中价导致方向/数值错"。
2. 保存"一周前绝对收盘价"（one_week_ago_price），供 Key Levels Dashboard 真实展示 1W Ago。
3. 每源采集后写 raw_pulls（带 run_id/source/is_settled/close/prev_close）做审计存证。
4. 新增 fetch_fx_rates_yahoo() 作为 FX 主源（DXY + 主要货币对），避免 FX 段空白。
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

from storage import db


MARKET_TICKERS = {
    "indices": {
        "^GSPC": "S&P 500",
        "^IXIC": "Nasdaq Composite",
        "^DJI": "Dow Jones",
        "^N225": "Nikkei 225",
        "^HSI": "HSI",
        "000300.SS": "CSI 300",
        "^STOXX50E": "Euro Stoxx 50",
    },
    "rates": {
        "^TNX": "US 10Y Treasury Yield",
        "^FVX": "US 5Y Treasury Yield",
        "^TYX": "US 30Y Treasury Yield",
        "^IRX": "US 13W Treasury Bill",
    },
    "fx": {
        "DX-Y.NYB": "US Dollar Index (DXY)",
    },
    "commodities": {
        "GC=F": "Gold",
        "SI=F": "Silver",
        "CL=F": "WTI Crude Oil",
        "BZ=F": "Brent Crude",
        "HG=F": "Copper",
    },
    "volatility": {
        "^VIX": "VIX Volatility Index",
    },
}

# 各市场现金收盘时间（交易所本地时区 + 小时:分钟）。
# 用于判断 yfinance 返回的"今日"日线 bar 是否已定稿。
MARKET_CLOSE = {
    # US 现金盘 16:00 ET；期货/收益率/DXY 一并用此作为日线 bar 定稿参考
    "US": ("America/New_York", 16, 0),
    "EU": ("Europe/Paris", 17, 30),       # Euro Stoxx 50 收盘 17:30 CET
    "JP": ("Asia/Tokyo", 15, 0),           # Nikkei 15:00 JST
    "HK": ("Asia/Hong_Kong", 16, 0),       # HSI 16:00 HKT
    "CN": ("Asia/Shanghai", 15, 0),        # CSI 300 15:00 CST
}

# 标的 → 市场分组
TICKER_MARKET = {}
for _sym in ["^GSPC", "^IXIC", "^DJI", "^TNX", "^FVX", "^TYX", "^IRX",
             "GC=F", "SI=F", "CL=F", "BZ=F", "HG=F", "^VIX", "DX-Y.NYB"]:
    TICKER_MARKET[_sym] = "US"
TICKER_MARKET["^STOXX50E"] = "EU"
TICKER_MARKET["^N225"] = "JP"
TICKER_MARKET["^HSI"] = "HK"
TICKER_MARKET["000300.SS"] = "CN"


def _is_settled(ticker: str, last_bar_date, now_utc: datetime) -> bool:
    """判断最新日线 bar 是否已定稿。

    - last_bar_date: 该 bar 的日期（无时区，交易所本地日历日）。
    - 若 bar 日期早于交易所"今日" → 必已定稿。
    - 若 bar 日期 == 交易所"今日" → 仅当当前 UTC 时间已过该市场收盘时间才算定稿。
    """
    market = TICKER_MARKET.get(ticker, "US")
    tz_name, ch, cm = MARKET_CLOSE.get(market, ("America/New_York", 16, 0))
    try:
        from zoneinfo import ZoneInfo
        exch_now = datetime.now(ZoneInfo(tz_name))
        if last_bar_date < exch_now.date():
            return True
        if last_bar_date > exch_now.date():
            return True  # 未来日期（异常），按已定稿处理避免误用
        # 同日：判断是否已过收盘
        close_dt = exch_now.replace(hour=ch, minute=cm, second=0, microsecond=0)
        return exch_now >= close_dt
    except Exception:
        # 无法判定时区时保守视为已定稿（保留原有行为），但不阻断
        return True


def fetch_market_data(run_id: str = None) -> dict:
    """获取所有市场数据（含结算守卫与审计写库）。"""
    results = {}
    raw_rows: list[dict] = []

    for category, tickers in MARKET_TICKERS.items():
        symbols = list(tickers.keys())
        batch_size = 8
        category_data = {}

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            try:
                data = yf.download(batch, period="10d", interval="1d",
                                   progress=False, auto_adjust=True)
                if data.empty:
                    continue

                if isinstance(data.columns, pd.MultiIndex):
                    price_levels = data.columns.get_level_values(0).unique()
                    ticker_levels = data.columns.get_level_values(1).unique()

                    for sym in batch:
                        if sym not in ticker_levels:
                            continue
                        name = tickers[sym]
                        try:
                            raw_closes = data["Close"][sym]
                            # 最新会话是否存在“有开/成交量但无收盘”的数据空洞（Yahoo 尚未发布收盘）
                            missing_close = bool(pd.isna(raw_closes.iloc[-1]))
                            closes = raw_closes.dropna()
                            highs = data["High"][sym].dropna()
                            lows = data["Low"][sym].dropna()

                            if closes.empty:
                                continue

                            # ── 结算守卫 ──
                            last_bar_date = pd.to_datetime(closes.index[-1]).date()
                            settled = _is_settled(sym, last_bar_date, datetime.now(timezone.utc))
                            if not settled and len(closes) > 1:
                                # 丢弃未定稿的当日 bar，改用上一根已定稿日线
                                settled_closes = closes.iloc[:-1]
                                settled_highs = highs.iloc[:-1] if not highs.empty else highs
                                settled_lows = lows.iloc[:-1] if not lows.empty else lows
                                settlement = "intraday_fallback"
                            else:
                                settled_closes = closes
                                settled_highs = highs
                                settled_lows = lows
                                settlement = "settled"

                            if settled_closes.empty:
                                continue

                            # 若最新会话收盘缺失（Yahoo 数据空洞），标记 stale 交由网页证据校正兜底
                            if missing_close:
                                stale = True
                                if settlement == "settled":
                                    settlement = "stale_missing_close"
                            else:
                                stale = False

                            current = float(settled_closes.iloc[-1])
                            prev_close = float(settled_closes.iloc[-2]) if len(settled_closes) > 1 else current
                            high = float(settled_highs.iloc[-1]) if not settled_highs.empty else None
                            low = float(settled_lows.iloc[-1]) if not settled_lows.empty else None

                            change = current - prev_close
                            change_pct = (change / prev_close * 100) if prev_close else 0
                            # 一周前绝对收盘价（窗口内最早的一根 ≈ 7 个交易日前）
                            one_week_ago_price = float(settled_closes.iloc[0]) if len(settled_closes) >= 3 else prev_close
                            weekly_change_pct = ((current - one_week_ago_price) / one_week_ago_price * 100) if one_week_ago_price else 0

                            if weekly_change_pct > 0.5:
                                trend = "▲"
                            elif weekly_change_pct < -0.5:
                                trend = "▼"
                            else:
                                trend = "→"

                            category_data[sym] = {
                                "name": name,
                                "price": round(current, 2),
                                "change": round(change, 2),
                                "change_pct": round(change_pct, 2),
                                "weekly_change_pct": round(weekly_change_pct, 2),
                                "one_week_ago_price": round(one_week_ago_price, 2),
                                "high": round(high, 2) if high else None,
                                "low": round(low, 2) if low else None,
                                "trend": trend,
                                "settlement": settlement,
                                "stale": stale,
                                "source": COMMODITY_SOURCES.get(sym, "Yahoo Finance") if category == "commodities" else "Yahoo Finance",
                            }

                            # 审计存证
                            raw_rows.append({
                                "run_id": run_id,
                                "source": "yfinance",
                                "ticker": sym,
                                "close": current,
                                "prev_close": prev_close,
                                "is_settled": settled,
                            })
                        except Exception as e:
                            print(f"  [Yahoo] {sym}: {e}")
                else:
                    # 单标的返回普通 DataFrame
                    sym = batch[0]
                    name = tickers[sym]
                    try:
                        raw_closes = data["Close"]
                        missing_close = bool(pd.isna(raw_closes.iloc[-1]))
                        closes = raw_closes.dropna()
                        if closes.empty:
                            continue
                        last_bar_date = pd.to_datetime(closes.index[-1]).date()
                        settled = _is_settled(sym, last_bar_date, datetime.now(timezone.utc))
                        settled_closes = closes if (settled or len(closes) <= 1) else closes.iloc[:-1]
                        if settled_closes.empty:
                            continue
                        current = float(settled_closes.iloc[-1])
                        prev_close = float(settled_closes.iloc[-2]) if len(settled_closes) > 1 else current
                        change = current - prev_close
                        change_pct = (change / prev_close * 100) if prev_close else 0
                        one_week_ago_price = float(settled_closes.iloc[0]) if len(settled_closes) >= 3 else prev_close
                        weekly_change_pct = ((current - one_week_ago_price) / one_week_ago_price * 100) if one_week_ago_price else 0
                        trend = "▲" if weekly_change_pct > 0.5 else ("▼" if weekly_change_pct < -0.5 else "→")
                        category_data[sym] = {
                            "name": name,
                            "price": round(current, 2),
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2),
                            "weekly_change_pct": round(weekly_change_pct, 2),
                            "one_week_ago_price": round(one_week_ago_price, 2),
                            "high": None,
                            "low": None,
                            "trend": trend,
                            "settlement": ("stale_missing_close" if missing_close else ("settled" if settled else "intraday_fallback")),
                            "stale": missing_close,
                            "source": COMMODITY_SOURCES.get(sym, "Yahoo Finance") if category == "commodities" else "Yahoo Finance",
                        }
                        raw_rows.append({
                            "run_id": run_id,
                            "source": "yfinance",
                            "ticker": sym,
                            "close": current,
                            "prev_close": prev_close,
                            "is_settled": settled,
                        })
                    except Exception as e:
                        print(f"  [Yahoo] {sym}: {e}")

            except Exception as e:
                print(f"  [Yahoo] batch error {batch}: {e}")

        results[category] = category_data

    # ── 备选标的兜底：主标的缺失最新收盘时回退到同指数备选 ticker ──
    FALLBACK_TICKERS = {"000300.SS": ["399300.SZ"]}
    for primary, alts in FALLBACK_TICKERS.items():
        for category in results:
            item = results[category].get(primary)
            if not item:
                continue
            if item.get("stale") or item.get("settlement") == "stale_missing_close":
                for alt in alts:
                    try:
                        d = yf.download(alt, period="10d", interval="1d", progress=False, auto_adjust=True)
                        close = d["Close"]
                        if isinstance(close, pd.DataFrame):
                            close = close.iloc[:, 0]
                        c = close.dropna()
                        if not c.empty:
                            cur = float(c.iloc[-1])
                            prev = float(c.iloc[-2]) if len(c) > 1 else cur
                            chg = ((cur - prev) / prev * 100) if prev else 0
                            item["price"] = round(cur, 2)
                            item["change"] = round(cur - prev, 2)
                            item["change_pct"] = round(chg, 2)
                            # 注：周基准(one_week_ago_price/weekly_change_pct)保留主标的原值，
                            # 备选标的窗口常不足一周，避免将其错误清零；日涨跌由证据校正兜底。
                            item["stale"] = False
                            item["settlement"] = "alt_ticker_fallback"
                            item["source"] = f"Yahoo Finance ({alt} fallback)"
                            print(f"  [Yahoo] {primary}: 回退至备选标的 {alt} → {cur}")
                            break
                    except Exception as e:
                        print(f"  [Yahoo] fallback {alt}: {e}")

    # 批量写审计
    if run_id and raw_rows:
        db.write_raw_pulls_batch(raw_rows)

    return results


def fetch_yield_curve(run_id: str = None) -> list[dict]:
    """获取收益率曲线"""
    tenors = {"^IRX": "3M", "^FVX": "5Y", "^TNX": "10Y", "^TYX": "30Y"}
    result = []
    for sym, label in tenors.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period="10d")
            if not h.empty:
                last_bar_date = pd.to_datetime(h.index[-1]).date()
                settled = _is_settled(sym, last_bar_date, datetime.now(timezone.utc))
                h_used = h if (settled or len(h) <= 1) else h.iloc[:-1]
                y = float(h_used["Close"].iloc[-1])
                p = float(h_used["Close"].iloc[-2]) if len(h_used) > 1 else y
                result.append({"tenor": label, "yield": round(y, 3), "previous": round(p, 3)})
                if run_id:
                    db.write_raw_pull(run_id, "yfinance", sym, y, p, is_settled=settled)
        except Exception:
            pass
    return result


# ── FX 主源（Yahoo）─────────────────────────────────────────────
YAHOO_FX = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X",
    "USD/CNH": "USDCNH=X",
    "USD/HKD": "USDHKD=X",
    "USD/SGD": "USDSGD=X",
    "USD/KRW": "USDKRW=X",
    "USD/MXN": "USDMXN=X",
}

# 商品标的 → 交易所（用于报告标注数据源，落实可溯源原则）
COMMODITY_SOURCES = {
    "GC=F": "COMEX", "SI=F": "COMEX", "HG=F": "COMEX",
    "CL=F": "NYMEX", "BZ=F": "ICE",
}


def _fx_settled(series) -> bool:
    """FX 日线以纽约 17:00 收盘定稿；最新 bar 属今日且未过 17:00 ET 视为未结算。

    废止原先统一用 DXY('DX-Y.NYB') 判定所有货币对的一刀切做法，
    改为依据各货币对自身的日线 bar 日期 + 纽约收盘时点判定，
    确保 AUD/USD、USD/MXN 等非美时段货币对取到完整会话的 prev/close，
    从采集层消除涨跌幅符号反转的隐患。
    """
    if series is None or len(series) < 2:
        return True
    last_dt = pd.to_datetime(series.index[-1])
    try:
        from zoneinfo import ZoneInfo
        ny = datetime.now(ZoneInfo("America/New_York"))
        if last_dt.date() != ny.date():
            return True
        close_dt = ny.replace(hour=17, minute=0, second=0, microsecond=0)
        return ny >= close_dt
    except Exception:
        return True


def fetch_fx_rates_yahoo(run_id: str = None) -> dict:
    """用 Yahoo Finance 抓取主要货币对，作为 FX 主源（无额度限制）。

    返回 {pair: {rate, change_pct, bid, ask, last_refreshed, source}}。
    """
    fx_rates = {}
    syms = list(YAHOO_FX.values())
    pair_by_sym = {v: k for k, v in YAHOO_FX.items()}
    raw_rows = []

    # 批量下载
    try:
        data = yf.download(syms, period="5d", interval="1d", progress=False, auto_adjust=True)
        if data.empty:
            return fx_rates

        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"]
            for sym in syms:
                pair = pair_by_sym[sym]
                try:
                    s = closes[sym].dropna()
                    if s.empty:
                        continue
                    settled = _fx_settled(s)
                    s_used = s if (settled or len(s) <= 1) else s.iloc[:-1]
                    if s_used.empty:
                        continue
                    current = float(s_used.iloc[-1])
                    prev = float(s_used.iloc[-2]) if len(s_used) > 1 else current
                    change_pct = ((current - prev) / prev * 100) if prev else 0
                    fx_rates[pair] = {
                        "rate": round(current, 4),
                        "change_pct": round(change_pct, 2),
                        "bid": "",
                        "ask": "",
                        "last_refreshed": datetime.now(timezone.utc).isoformat(),
                        "source": "yfinance",
                    }
                    raw_rows.append({
                        "run_id": run_id, "source": "yfinance_fx",
                        "ticker": sym, "close": current, "prev_close": prev, "is_settled": settled,
                    })
                except Exception as e:
                    print(f"  [Yahoo FX] {pair}: {e}")
    except Exception as e:
        print(f"  [Yahoo FX] download error: {e}")

    if run_id and raw_rows:
        db.write_raw_pulls_batch(raw_rows)

    return fx_rates
