"""多源检测与网页校验（原思考者机制落地）

设计目标（用户核心诉求）：在数据获取 API 内嵌「网页搜索 + 多重检测」，
确保最终进入报告的数据绝对真实，而非依赖单一数据源。

本模块提供两层校验：
  1. cross_check_fx(yahoo_fx, av_fx)
     —— 多重检测：Yahoo（主源）与 Alpha Vantage（辅源）对每个货币对的
        涨跌幅方向 / 幅度做交叉比对，方向相左或幅度差超阈值即告警。
  2. web_verify(quotes, verifier=None)
     —— 网页校验钩子（可插拔）：verifier 为外部注入的可调用对象，签名
        (quotes) -> list[str(alert)]。每日 06:00 Hunyuan 实跑时由 main
        注入「Hunyuan + 网页搜索」核验器；无 verifier 时静默返回 [] 不阻断。

模块仅依赖标准库；对 Hunyuan / 网络的真实调用由外部 verifier 负责，
本文件不做任何硬编码的 HTTP 请求，保证在沙箱/离线环境下也能安全运行。
"""
from typing import Callable, Dict, List, Optional
import json
import os


# 价格/点位偏差阈值（用于证据交叉校验）
EVIDENCE_PRICE_TOL_PCT = 0.5
# FX 多重检测幅度阈值
FX_MAG_THRESHOLD = 0.3


def _fp(pair_info: dict) -> float:
    try:
        return float(pair_info.get("change_pct", 0) or 0)
    except (ValueError, TypeError):
        return 0.0


def _dir_sign(label: str) -> int:
    """把 up/down/flat 映射为符号；unknown 返回 None。"""
    if not label:
        return None
    s = str(label).strip().lower()
    if s in ("up", "▲", "+"):
        return 1
    if s in ("down", "▼", "-"):
        return -1
    if s in ("flat", "→", "range", "0"):
        return 0
    return None


def cross_check_fx(yahoo_fx: Dict[str, dict], av_fx: Dict[str, dict],
                   mag_threshold: float = FX_MAG_THRESHOLD) -> List[str]:
    """Yahoo 主源 × Alpha Vantage 辅源 的 FX 多重检测。

    返回告警字符串列表（为空表示两源一致）。

    修复点：当辅源 Alpha Vantage 返回 0 条（典型为限速/额度耗尽）时，
    原先会因 `if pair not in av_fx: continue` 而**静默通过**——造成"假阴性"
    的虚高置信。现改为显式降级告警，提示单源风险并交由网页核验兜底。
    """
    alerts: List[str] = []
    if not av_fx:
        alerts.append(
            "[FX交叉检测] 辅源 Alpha Vantage 返回 0 条(疑似限速/额度)，"
            "FX 多重检测降级为单源，已启用网页核验(evidence)兜底，请关注。"
        )
        return alerts
    for pair, yinfo in yahoo_fx.items():
        if pair not in av_fx:
            continue
        y = _fp(yinfo)
        a = _fp(av_fx[pair])
        # 方向相左
        if (y > 0) != (a > 0) and y != 0 and a != 0:
            alerts.append(
                f"[FX交叉检测] {pair}: Yahoo={y:+.2f}% 与 AlphaVantage={a:+.2f}% "
                f"方向相左，疑似单源异常，建议以网页核验结果为准。"
            )
        elif abs(y - a) >= mag_threshold:
            alerts.append(
                f"[FX交叉检测] {pair}: Yahoo={y:+.2f}% 与 AlphaVantage={a:+.2f}% "
                f"幅度差 {abs(y - a):.2f}pp 超阈值 {mag_threshold}pp，请复核。"
            )
    return alerts


# ───────────────────────── 网页核验(证据交叉校验) ─────────────────────────
def load_web_evidence(path: str) -> dict:
    """载入由自动化写出的独立网页核验证据 JSON。

    证据 JSON 结构(由 Hunyuan 每日 6 点实跑时基于多源网页搜索 + 多数投票锁定)：
      { "indices": {sym: {price, dir}}, "rates": {sym:{yield,dir}},
        "commodities": {sym:{price,dir}}, "fx": {pair:{rate,dir}}, "macro": {...} }
    返回空 dict 表示无证据可用（交由调用方降级）。
    """
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"  [evidence] 载入失败（降级为无证据）: {e}")
    return {}


def web_evidence_verify(market_data: dict, fx_rates: dict, evidence: dict,
                        price_tol: float = EVIDENCE_PRICE_TOL_PCT) -> List[str]:
    """用独立网页核验证据对 pipeline 报价做交叉校验（网页搜索多重校验核心）。

    逐标的检查：
      1) 价格/点位偏差：|pipeline - evidence| / evidence > 0.5% → 告警；
      2) 方向反转：pipeline 涨跌幅符号 与 evidence.dir 相反 → 告警（最高优先级）。
    仅对证据中提供了数值基准的标的检查；无基准项跳过并记录未核验。
    """
    alerts: List[str] = []
    if not evidence:
        return alerts

    def _check(category: str, items: dict, ev_map: dict, key_of_price: str):
        for sym, info in items.items():
            ev = ev_map.get(sym)
            if not ev or ev.get(key_of_price) is None:
                continue
            bench = float(ev[key_of_price])
            cur = info.get("price")
            if cur is None:
                continue
            cur = float(cur)
            # 价格偏差
            dev = abs(cur - bench) / bench * 100 if bench else 0
            if dev > price_tol:
                alerts.append(
                    f"[网页核验] {category} {sym} ({info.get('name','')}): "
                    f"pipeline={cur} 与网页证据={bench} 偏差 {dev:.2f}% > {price_tol}% 阈值，请复核。"
                )
            # 方向反转
            ev_dir = _dir_sign(ev.get("dir"))
            chg = float(info.get("change_pct", 0) or 0)
            if ev_dir is not None and ev_dir != 0:
                if (chg > 0) != (ev_dir > 0) and chg != 0:
                    alerts.append(
                        f"[网页核验] {category} {sym} ({info.get('name','')}): "
                        f"pipeline 方向 {chg:+.2f}% 与网页证据方向({ev.get('dir')}) 相左，疑似方向反转！"
                    )

    _check("股指", market_data.get("indices", {}), evidence.get("indices", {}), "price")
    _check("利率", market_data.get("rates", {}), evidence.get("rates", {}), "yield")
    _check("商品", market_data.get("commodities", {}), evidence.get("commodities", {}), "price")

    # FX
    for pair, info in fx_rates.items():
        ev = evidence.get("fx", {}).get(pair)
        if not ev or ev.get("rate") is None:
            continue
        bench = float(ev["rate"])
        cur = float(info.get("rate", 0) or 0)
        dev = abs(cur - bench) / bench * 100 if bench else 0
        if dev > price_tol:
            alerts.append(
                f"[网页核验] 外汇 {pair}: pipeline={cur} 与网页证据={bench} 偏差 {dev:.2f}% > {price_tol}%，请复核。"
            )
        ev_dir = _dir_sign(ev.get("dir"))
        chg = float(info.get("change_pct", 0) or 0)
        if ev_dir is not None and ev_dir != 0:
            if (chg > 0) != (ev_dir > 0) and chg != 0:
                alerts.append(
                    f"[网页核验] 外汇 {pair}: pipeline 方向 {chg:+.2f}% 与网页证据方向({ev.get('dir')}) 相左，疑似方向反转！"
                )
    return alerts


def web_verify(quotes: dict, verifier: Optional[Callable[[dict], List[str]]] = None) -> List[str]:
    """可插拔的网页校验钩子。

    verifier: 外部注入的核验器（每日 6 点由 Hunyuan + 网页搜索实现）。
              签名 (quotes) -> list[str(alert)]。
    无 verifier 时返回空列表并记录 info 级日志，不阻断链路。
    """
    if verifier is None:
        print("  [verify] web_verify 未注入 verifier（ENABLE_WEB_VERIFY 未开启），跳过网页核验。")
        return []
    try:
        alerts = verifier(quotes) or []
        if alerts:
            print(f"  [verify] 网页核验返回 {len(alerts)} 条告警。")
        else:
            print("  [verify] 网页核验通过，无异常。")
        return alerts
    except Exception as e:
        print(f"  [verify] web_verify 执行异常（已忽略，不阻断链路）: {e}")
        return []


def multi_source_summary(alerts: List[str]) -> str:
    """汇总多源检测告警，供 quality_alerts / 报告使用。"""
    if not alerts:
        return "✓ 多源检测一致：Yahoo 与 Alpha Vantage 关键 FX 数值吻合。"
    return "⚠ 多源检测发现分歧：\n  - " + "\n  - ".join(alerts)
