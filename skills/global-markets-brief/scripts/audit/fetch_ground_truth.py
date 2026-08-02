"""地面真值采集（历史收盘价，as of 报告日期）。

复用 collectors.yahoo 的标的映射 (MARKET_TICKERS / YAHOO_FX)，
用 yfinance 拉取报告日附近的日线，回算 current/prev/1W 及涨跌幅，
作为「反查报告写没写对」的参照基准。

不调用任何 LLM API —— 纯数据抓取 + 回算。
"""
from collections import Counter
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd

try:
    from collectors.yahoo import MARKET_TICKERS, YAHOO_FX
except ImportError:  # 作为独立脚本运行时也保证能定位到 collectors
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from collectors.yahoo import MARKET_TICKERS, YAHOO_FX


def _window_close(ticker: str, as_of: str) -> dict | None:
    """取 as_of 当日（或之前最近一个交易日）的收盘，并回算 prev / 1W。"""
    as_of_d = datetime.strptime(as_of, "%Y-%m-%d")
    start = (as_of_d - timedelta(days=21)).strftime("%Y-%m-%d")
    end = (as_of_d + timedelta(days=2)).strftime("%Y-%m-%d")
    try:
        df = yf.download(ticker, start=start, end=end, interval="1d",
                         progress=False, auto_adjust=True)
    except Exception as e:
        print(f"  [truth] {ticker}: download error {e}")
        return None
    if df is None or df.empty:
        return None
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    if close.empty:
        return None

    as_of_ts = pd.Timestamp(as_of_d)
    le = close.index[close.index <= as_of_ts]
    if len(le) == 0:
        return None
    last_dt = le[-1]
    series = close.loc[:last_dt]
    current = float(series.iloc[-1])
    prev = float(series.iloc[-2]) if len(series) > 1 else current
    one_wk = float(series.iloc[0]) if len(series) >= 6 else prev
    return {
        "data_date": last_dt.strftime("%Y-%m-%d"),
        "price": round(current, 4),
        "prev_close": round(prev, 4),
        "change_pct": round((current - prev) / prev * 100, 2) if prev else 0.0,
        "one_week_ago_price": round(one_wk, 4),
        "weekly_change_pct": round((current - one_wk) / one_wk * 100, 2) if one_wk else 0.0,
    }


def fetch_ground_truth(as_of_date: str) -> dict:
    """返回与报告结构同构的地面真值 dict。"""
    print(f"  [truth] Fetching historical ground truth as of {as_of_date} ...")
    result = {"as_of_date": as_of_date, "indices": {}, "rates": {}, "commodities": {}, "fx": {}}
    cats = ["indices", "rates", "commodities"]
    for cat in cats:
        for sym, name in MARKET_TICKERS.get(cat, {}).items():
            g = _window_close(sym, as_of_date)
            if g:
                result[cat][name] = g
    for pair, sym in YAHOO_FX.items():
        g = _window_close(sym, as_of_date)
        if g:
            result["fx"][pair] = g

    dates = ([v["data_date"] for c in cats for v in result[c].values()]
             + [v["data_date"] for v in result["fx"].values()])
    result["truth_data_date"] = Counter(dates).most_common(1)[0][0] if dates else None
    n = sum(len(result[c]) for c in cats) + len(result["fx"])
    print(f"  [truth] OK: {n} instruments (truth_data_date={result['truth_data_date']})")
    return result
