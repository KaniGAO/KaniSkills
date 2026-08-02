"""FRED 经济数据采集（修复版）

修复点：
1. 月频指数水平（CPIAUCSL/PCEPILFE/GDPC1）换算为同比(YoY)/环比(MoM)率，
   不再直接 dump 332.568 这类原始指数水平让读者困惑。
2. 清晰标注参考期（date 列即 FRED 观测日，= 数据所属月份的首日）。
3. 过滤 FRED 的缺失值标记 "."。
4. 写审计 raw_pulls（写入数值便于追溯）。
"""
import requests
from config import Config


# 关注的 FRED 序列；type 决定如何呈现
FRED_SERIES = {
    "T10Y2Y":    {"label": "US 10Y-2Y Spread",          "type": "rate"},
    "T10YIE":    {"label": "US 10Y Breakeven Inflation", "type": "rate"},
    "UNRATE":    {"label": "US Unemployment Rate",       "type": "rate"},
    "CPIAUCSL":  {"label": "US CPI (All Items, YoY)",    "type": "index"},
    "PCEPILFE":  {"label": "US Core PCE Price Index (YoY)", "type": "index"},
    "FEDFUNDS":  {"label": "Federal Funds Rate",         "type": "fed_funds"},
    "GDPC1":     {"label": "US Real GDP (YoY)",          "type": "index"},
    "DFII10":    {"label": "US 10Y TIPS Yield",          "type": "rate"},
    "DGS10":     {"label": "US 10Y Treasury Yield",      "type": "rate"},
    "DGS2":      {"label": "US 2Y Treasury Yield",       "type": "rate"},
    "DTWEXBGS":  {"label": "US Dollar Index (Broad)",    "type": "index"},
}


def _to_float(v):
    try:
        f = float(v)
        if v in (".", "", None):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _fed_target_range(mid):
    """由 FRED FEDFUNDS(有效利率≈目标区间中点) 推导规范目标区间。

    FOMC 目标区间为 25bp 步进，故中点 m 与区间满足 [m-0.125, m+0.125]，
    落在 0.25 网格上。从中点反推，避免硬编码锚点。
    """
    if mid is None:
        return "N/A"
    lo = round((mid - 0.125) * 4) / 4
    hi = round((mid + 0.125) * 4) / 4
    return f"{lo:.2f}–{hi:.2f}% (target range)"


def fetch_fred_data(run_id: str = None) -> dict:
    """获取所有 FRED 经济指标，指数水平序列换算为同比/环比率。"""
    if not Config.FRED_API_KEY or Config.FRED_API_KEY == "YOUR_FRED_API_KEY":
        print("  [FRED] No API key configured")
        return {}

    results = {}
    errors = []
    raw_rows = []

    for series_id, meta in FRED_SERIES.items():
        label = meta["label"]
        stype = meta["type"]
        # 指数序列需取足够历史以算同比（月频 14 期、季频 6 期）
        limit = 14 if stype == "index" else 2
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}"
            f"&api_key={Config.FRED_API_KEY}"
            f"&file_type=json"
            f"&sort_order=desc&limit={limit}"
        )
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                errors.append(f"{series_id}: HTTP {resp.status_code}")
                continue

            data = resp.json()
            obs = data.get("observations", [])
            # 过滤缺失值
            obs = [o for o in obs if o.get("value") not in (".", "", None)]
            if not obs:
                continue

            latest = obs[0]
            latest_val = _to_float(latest.get("value"))

            if stype == "fed_funds":
                # FRED FEDFUNDS 为有效利率，约等于 FOMC 目标区间中点；
                # 渲染为规范目标区间（由中点反推，非硬编码锚点）。
                series = {
                    "label": label,
                    "value": _fed_target_range(latest_val),
                    "date": latest.get("date"),
                    "reference_period": latest.get("date"),
                }
                if len(obs) >= 2:
                    pv = _to_float(obs[1].get("value"))
                    series["prev_value"] = _fed_target_range(pv)
                    series["prev_date"] = obs[1].get("date")
                raw_rows.append({
                    "run_id": run_id, "source": "fred", "ticker": series_id,
                    "close": latest_val, "prev_close": _to_float(obs[1].get("value")) if len(obs) >= 2 else None,
                    "is_settled": True,
                })
            elif stype == "rate":
                # 已是率，直接呈现
                series = {
                    "label": label,
                    "value": f"{latest_val:.2f}%" if latest_val is not None else "N/A",
                    "date": latest.get("date"),
                    "reference_period": latest.get("date"),
                }
                if len(obs) >= 2:
                    pv = _to_float(obs[1].get("value"))
                    series["prev_value"] = f"{pv:.2f}%" if pv is not None else "N/A"
                    series["prev_date"] = obs[1].get("date")
                raw_rows.append({
                    "run_id": run_id, "source": "fred", "ticker": series_id,
                    "close": latest_val, "prev_close": _to_float(obs[1].get("value")) if len(obs) >= 2 else None,
                    "is_settled": True,
                })
            else:
                # 指数水平 → 同比/环比
                vals = [_to_float(o.get("value")) for o in obs]
                vals = [v for v in vals if v is not None]
                if not vals:
                    continue
                latest_v = vals[0]
                # 同比：与 12 期前比较（月频）；季频(GDP)与 4 期前比较
                yoy_shift = 4 if series_id == "GDPC1" else 12
                yoy = ((latest_v - vals[yoy_shift]) / vals[yoy_shift] * 100) if len(vals) > yoy_shift else None
                mom = ((latest_v - vals[1]) / vals[1] * 100) if len(vals) > 1 else None
                # 上期同比（用于 Previous 列）
                prev_yoy = None
                if len(vals) > yoy_shift + 1:
                    prev_yoy = ((vals[1] - vals[yoy_shift + 1]) / vals[yoy_shift + 1] * 100)

                series = {
                    "label": label,
                    "value": f"{yoy:+.1f}% YoY" if yoy is not None else f"{latest_v:.2f}",
                    "prev_value": f"{prev_yoy:+.1f}% YoY" if prev_yoy is not None else "N/A",
                    "date": latest.get("date"),
                    "reference_period": latest.get("date"),
                    "raw_level": round(latest_v, 3),
                    "mom_pct": round(mom, 2) if mom is not None else None,
                    "yoy_pct": round(yoy, 2) if yoy is not None else None,
                }
                raw_rows.append({
                    "run_id": run_id, "source": "fred", "ticker": series_id,
                    "close": latest_v, "prev_close": vals[1] if len(vals) > 1 else None,
                    "is_settled": True,
                })

            results[series_id] = series
        except requests.RequestException as e:
            errors.append(f"{series_id}: {e}")

    if errors:
        print(f"  [FRED] Errors: {errors[:3]}...")

    # 写审计
    if run_id and raw_rows:
        try:
            from storage import db
            db.write_raw_pulls_batch(raw_rows)
        except Exception as e:
            print(f"  [FRED] audit write failed: {e}")

    return results
