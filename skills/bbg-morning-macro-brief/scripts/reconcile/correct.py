"""
网页证据驱动的偏差校正（多重校验闭环的“修正”环节）

采集环节发现的偏差分两类：
  1) Yahoo 主标的存在“最新会话收盘缺失”的数据空洞 → yahoo.py 已标记 stale 并尽量用备选标的兜底；
  2) 剩余与多源网页证据（Hunyuan 检索锁定）偏离 > 阈值，或仍 stale 的项。

本模块在生成报告前，用“多源网页证据（confidence>=2）”覆盖这些偏差项，使最终报告
核心字段（价格<0.5%、涨跌幅方向全对、宏观正确）达成阈值内一致。
"""
from __future__ import annotations

import os
import json


# 价格偏离阈值（%）。超过且证据置信度>=2 即触发覆盖校正。
PRICE_TOL_PCT = 0.5
MIN_CONFIDENCE = 2


def _dev_pct(cur, bench):
    try:
        cur = float(cur)
        bench = float(bench)
    except (TypeError, ValueError):
        return None
    if bench == 0:
        return None
    return abs(cur - bench) / abs(bench) * 100


def apply_evidence_corrections(market_data: dict, fx_rates: dict, economic_data: dict,
                               evidence: dict, run_id: str = None, price_tol: float = PRICE_TOL_PCT) -> list:
    """用网页证据覆盖偏离/陈旧项，返回校正清单字符串列表。"""
    corrections: list = []
    if not evidence:
        return corrections

    # ── 股指 / 利率 / 商品 ──
    for cat in ("indices", "rates", "commodities"):
        ev_cat = evidence.get(cat, {})
        for sym, info in market_data.get(cat, {}).items():
            ev = ev_cat.get(sym)
            if not ev:
                continue
            bench = ev.get("yield") if cat == "rates" else ev.get("price")
            cur = info.get("price")
            dev = _dev_pct(cur, bench)
            # 触发条件：数据陈旧 / 备选标的兜底 / 已校正 / 偏离超阈值（证据置信度足够）
            trigger = (
                bool(info.get("stale"))
                or info.get("settlement") == "alt_ticker_fallback"
                or bool(info.get("corrected"))
                or (dev is not None and dev > price_tol)
            )
            if not trigger or ev.get("confidence", 0) < MIN_CONFIDENCE:
                continue
            old_price = info.get("price")
            info["price"] = round(float(bench), 2)
            if ev.get("change_pct") is not None:
                info["change_pct"] = round(float(ev["change_pct"]), 2)
                info["change"] = round(info["price"] * float(ev["change_pct"]) / 100.0, 2)
            info["stale"] = False
            info["corrected"] = True
            info["source"] = f"Web-verified ({ev.get('note', 'multi-source')})"
            corrections.append(
                f"{cat}/{sym}: 价格 {old_price} -> {info['price']} "
                f"(涨跌 {ev.get('change_pct')}%, 方向 {ev.get('dir')})"
            )

    # ── 外汇 ──
    ev_fx = evidence.get("fx", {})
    for pair, info in fx_rates.items():
        ev = ev_fx.get(pair)
        if not ev or ev.get("rate") is None:
            continue
        cur = info.get("rate")
        dev = _dev_pct(cur, ev["rate"])
        if (dev is None or dev <= price_tol) or ev.get("confidence", 0) < MIN_CONFIDENCE:
            continue
        old_rate = info.get("rate")
        info["rate"] = round(float(ev["rate"]), 4)
        if ev.get("change_pct") is not None:
            info["change_pct"] = round(float(ev["change_pct"]), 2)
        info["source"] = "Web-verified (ECB/multi-source)"
        corrections.append(f"fx/{pair}: {old_rate} -> {info['rate']}")

    # ── 宏观（FRED 计算值与官方网页口径偏离时，以官方口径校正）──
    ev_macro = evidence.get("macro", {})
    for sid, info in economic_data.items():
        ev = ev_macro.get(sid)
        if not ev or ev.get("value") is None or ev.get("confidence", 0) < MIN_CONFIDENCE:
            continue
        if info.get("value") == ev["value"]:
            continue
        old_val = info.get("value")
        info["value"] = ev["value"]
        if ev.get("prev_value") is not None:
            info["prev_value"] = ev["prev_value"]
        info["corrected"] = True
        info["source"] = f"Web-verified ({ev.get('note', 'official')})"
        corrections.append(f"macro/{sid}: {old_val} -> {ev['value']}")

    return corrections


def load_web_evidence(path: str) -> dict:
    """载入网页核验证据 JSON；不存在返回 {}。"""
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  [correct] 证据载入失败 {path}: {e}")
    return {}
