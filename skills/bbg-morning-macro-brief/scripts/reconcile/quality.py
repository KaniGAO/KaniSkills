"""发布前数据质量校验与多源 reconcile。

职责：
1. reconcile：对同 ticker 多 source 的 close 做差异比对，|Δ|>tol 则降级 confidence 并告警。
2. 数据质量断言：
   - current == prev_close（无变化）→ 告警（可能数据源异常）。
   - 日涨跌幅超阈值（默认 |change_pct|>8%）且无相关新闻 → 告警。
3. 产出：已校验报价列表 + 告警列表，供 main.py 写 reconciled_quotes 并传给 report.py 渲染。

校验数据来源：从 DB raw_pulls 取本次 run_id 的所有原始抓取记录。
"""
from datetime import datetime, timezone, timedelta


# 多源比对容忍度（按价位量级）
RECON_TOL_PCT = 0.5   # 同一 ticker 不同源 close 相对偏差 >0.5% 视为不一致
# 单日涨跌幅异常阈值
SHOCK_THRESHOLD_PCT = 8.0
# 预期长期稳定的序列/标的（相邻交易日几乎不变属正常，不应报"数据源未更新"）
# FEDFUNDS=FOMC 目标利率（两次会议间不变）；USDCNH≈ 离岸人民币管理浮动（常日度持平）
STABLE_TICKERS = {"FEDFUNDS", "USDCNH=X"}


def reconcile(run_id: str, market_data: dict = None, news_articles: list = None,
              as_of_date: str = None) -> dict:
    """对本次 run 做 reconcile 与质量断言。

    返回:
        {
            "quotes": [{ticker, value, change_pct, confidence}],
            "alerts": [str, ...],
            "confidence_map": {ticker: "high"|"low"},
        }
    """
    from storage import db

    alerts: list[str] = []
    quotes: list[dict] = []
    confidence_map: dict = {}

    if not run_id:
        return {"quotes": quotes, "alerts": alerts, "confidence_map": confidence_map}

    if as_of_date is None:
        as_of_date = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")

    # 取本次 run 的全部原始抓取
    pulls = db.get_raw_pulls(run_id=run_id)

    # 按 ticker 分组
    by_ticker: dict[str, list[dict]] = {}
    for p in pulls:
        by_ticker.setdefault(p["ticker"], []).append(p)

    news_articles = news_articles or []
    news_blob = " ".join((a.get("title", "") + " " + a.get("summary", "")) for a in news_articles).lower()

    for ticker, rows in by_ticker.items():
        # 取已定稿的最近一条作为该 ticker 的代表报价
        settled_rows = [r for r in rows if r["is_settled"]]
        chosen = settled_rows[-1] if settled_rows else (rows[-1] if rows else None)
        if not chosen or chosen["close"] is None:
            continue

        close = chosen["close"]
        prev = chosen["prev_close"]
        change_pct = ((close - prev) / prev * 100) if prev else 0.0

        # ── 多源一致性（同一 ticker 不同 source 的 close 比较）──
        sources = {}
        for r in rows:
            if r["close"] is not None:
                sources.setdefault(r["source"], r["close"])
        confidence = "high"
        if len(sources) >= 2:
            vals = list(sources.values())
            spread = (max(vals) - min(vals)) / max(abs(v) for v in vals) * 100 if vals else 0
            if spread > RECON_TOL_PCT:
                confidence = "low"
                alerts.append(
                    f"Reconcile mismatch {ticker}: sources={sources} spread={spread:.2f}% > {RECON_TOL_PCT}%"
                )

        # ── 质量：current == prev ──
        if prev is not None and close == prev:
            if ticker in STABLE_TICKERS:
                alerts.append(
                    f"No change {ticker}: close==prev_close={close}（政策/锚定利率，会议间持平属正常，非数据源异常）"
                )
            else:
                alerts.append(f"No change {ticker}: close==prev_close={close} (疑似数据源未更新)")

        # ── 质量：涨跌幅超阈值且无新闻 ──
        if abs(change_pct) > SHOCK_THRESHOLD_PCT:
            # 用 ticker 名/相关关键词在新闻里搜
            kw = ticker.lower().replace("^", "").replace("=f", "")
            if kw not in news_blob:
                alerts.append(
                    f"Large move {ticker}: {change_pct:+.2f}% 且未检索到相关新闻（需人工核实）"
                )

        quotes.append({
            "ticker": ticker,
            "value": round(close, 4),
            "change_pct": round(change_pct, 2),
            "confidence": confidence,
        })
        confidence_map[ticker] = confidence

        # 写已校验报价
        db.upsert_reconciled_quote(as_of_date, ticker, round(close, 4), round(change_pct, 2), confidence)

    # ── market_data 层面的补充断言（覆盖 DB 未记录的字段）──
    if market_data:
        for category, tickers in market_data.items():
            for sym, info in tickers.items():
                if not isinstance(info, dict):
                    continue
                # 结算状态告警：若大量标的回退到 intraday_fallback
                if info.get("settlement") == "intraday_fallback":
                    alerts.append(
                        f"Settlement fallback {sym} ({info.get('name','')}): 采集时该市场未收盘，已改用上一已定稿日线"
                    )

    return {"quotes": quotes, "alerts": alerts, "confidence_map": confidence_map}
