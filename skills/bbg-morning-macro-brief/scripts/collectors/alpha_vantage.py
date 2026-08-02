"""Alpha Vantage 外汇汇率采集（补充源）

定位变更：FX 主源改为 Yahoo（fetch_fx_rates_yahoo，无额度限制），
本模块降级为补充源，用于与 Yahoo 做多源 reconcile 校验。

修复点：
1. 加限流退避（免费版 5 req/min, 25 req/day）：每请求间 sleep，遇限速/超时重试。
2. 额度耗尽时安全返回空，由主流程退化为单源（confidence=low）。
3. 标注 source=alphavantage，便于 reconcile 区分。
"""
import time
import requests
from datetime import datetime, timezone
from config import Config


FX_PAIRS = [
    ("EUR", "USD"), ("GBP", "USD"), ("USD", "JPY"),
    ("USD", "CHF"), ("AUD", "USD"), ("USD", "CAD"),
    ("NZD", "USD"), ("USD", "CNH"), ("USD", "HKD"),
    ("USD", "SGD"), ("USD", "KRW"), ("USD", "MXN"),
    ("EUR", "JPY"), ("GBP", "JPY"),
]

# 免费版限速：约 5 req/min → 每请求间隔 13s 较安全；日限 25 次
REQUEST_INTERVAL_SEC = 13
MAX_RETRIES = 2
RETRY_BACKOFF_SEC = 5


def _fetch_one(from_c: str, to_c: str) -> dict | None:
    """抓单个货币对，带重试。返回 dict 或 None。"""
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=CURRENCY_EXCHANGE_RATE"
        f"&from_currency={from_c}&to_currency={to_c}"
        f"&apikey={Config.ALPHA_VANTAGE_KEY}"
    )
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 429:
                # 限速
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            if resp.status_code != 200:
                return None
            data = resp.json()
            # AV 限速/额度耗尽时返回提示信息而非数据
            if "Realtime Currency Exchange Rate" not in data:
                note = data.get("Note") or data.get("Information") or ""
                if "limit" in note.lower() or "premium" in note.lower():
                    print(f"  [Alpha Vantage] 额度/限速：{note[:80]}")
                    return None
                return None
            return data["Realtime Currency Exchange Rate"]
        except requests.RequestException as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC)
            else:
                print(f"  [Alpha Vantage] Error {from_c}/{to_c}: {e}")
                return None
    return None


def fetch_fx_rates(run_id: str = None, pairs_limit: int = 5) -> dict:
    """获取外汇汇率（补充源）。额度耗尽时返回空。

    pairs_limit: 免费版日限紧张，默认只抓前 5 对用于校验。
    """
    if not Config.ALPHA_VANTAGE_KEY or Config.ALPHA_VANTAGE_KEY == "YOUR_AV_KEY":
        print("  [Alpha Vantage] No API key configured")
        return {}

    fx_rates = {}
    pairs = FX_PAIRS[:pairs_limit]

    for from_c, to_c in pairs:
        r = _fetch_one(from_c, to_c)
        if not r:
            # 命中额度限制后不再继续请求，避免浪费配额
            break
        pair_key = f"{from_c}/{to_c}"
        bid = r.get("8. Bid Price", "")
        ask = r.get("9. Ask Price", "")
        rate = r.get("5. Exchange Rate", "")
        try:
            mid = (float(bid) + float(ask)) / 2 if bid and ask else float(rate)
        except (ValueError, TypeError):
            mid = 0
        fx_rates[pair_key] = {
            "rate": round(mid, 4) if mid else rate,
            "bid": bid,
            "ask": ask,
            "change_pct": r.get("9. Change from previous close (%)", ""),
            "last_refreshed": r.get("6. Last Refreshed", ""),
            "source": "alphavantage",
        }
        # 限速退避
        time.sleep(REQUEST_INTERVAL_SEC)

    return fx_rates
