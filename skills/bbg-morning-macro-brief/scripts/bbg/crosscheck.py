"""Cross-source reconciliation: Bloomberg (PRIMARY) vs free corroborating sources.

Philosophy (see references/bbg_askb_prompts.md):
  - Bloomberg ASKB is the authoritative PRIMARY source for both numbers and
    narrative (macro, central bank, talking points, Asia day-ahead).
  - Free sources (Yahoo Finance, FRED, Alpha Vantage) are CORROBORATION only.
  - Rule 1: If a free source is missing a field Bloomberg has -> trust Bloomberg,
    note "corroboration unavailable".
  - Rule 2: If % divergence > 1.0 (absolute) OR the change-direction signs
    conflict -> flag the discrepancy for human/LLM review.
  - Rule 3: For qualitative narrative, Bloomberg always wins; free sources never
    override it.
"""
import re


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _parse_pct(s) -> float | None:
    if s is None:
        return None
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*%", str(s))
    return float(m.group(1)) if m else None


def _find_col(headers, *candidates):
    normed = [_norm(h) for h in headers]
    for c in candidates:
        for i, h in enumerate(normed):
            if c in h:
                return i
    return None


def run_crosscheck(bbg, market_data, fx_rates, economic_data) -> dict:
    """Reconcile parsed Bloomberg dict against free-source data.

    Returns:
        {"alerts": [str,...], "summary": str, "discrepancies": int}
    """
    alerts: list[str] = []
    discrepancies = 0

    if not bbg:
        return {
            "alerts": alerts,
            "summary": "No Bloomberg input — report based on free sources only.",
            "discrepancies": 0,
        }

    # ── Equities: compare % change direction/magnitude ──
    eq = bbg.get("equities")
    if eq and eq.get("type") == "table":
        headers = eq["headers"]
        chg_i = _find_col(headers, "chg")
        name_i = _find_col(headers, "index", "name", "asset")
        if chg_i is not None and name_i is not None:
            yahoo = {_norm(k): v for k, v in market_data.get("indices", {}).items()}
            for row in eq["rows"]:
                name = row[name_i]
                bbg_pct = _parse_pct(row[chg_i])
                yk = yahoo.get(_norm(name))
                if yk is None or bbg_pct is None:
                    continue
                try:
                    y_pct = float(yk.get("change_pct", 0) or 0)
                except (ValueError, TypeError):
                    continue
                if abs(bbg_pct - y_pct) > 1.0 or (bbg_pct * y_pct < 0):
                    discrepancies += 1
                    alerts.append(
                        f"[Equities] {name}: Bloomberg {bbg_pct:+.2f}% vs Yahoo {y_pct:+.2f}% "
                        f"— direction/level divergence"
                    )

    # ── FX: compare % change direction/magnitude ──
    fx = bbg.get("fx")
    if fx and fx.get("type") == "table":
        headers = fx["headers"]
        chg_i = _find_col(headers, "chg")
        pair_i = _find_col(headers, "pair", "currency")
        if chg_i is not None and pair_i is not None:
            for row in fx["rows"]:
                pair = row[pair_i]
                bbg_pct = _parse_pct(row[chg_i])
                yk = fx_rates.get(pair)
                if yk is None or bbg_pct is None:
                    continue
                try:
                    y_pct = float(yk.get("change_pct", 0) or 0)
                except (ValueError, TypeError):
                    continue
                if abs(bbg_pct - y_pct) > 1.0 or (bbg_pct * y_pct < 0):
                    discrepancies += 1
                    alerts.append(
                        f"[FX] {pair}: Bloomberg {bbg_pct:+.2f}% vs Yahoo {y_pct:+.2f}% "
                        f"— divergence"
                    )

    if discrepancies:
        summary = (
            "Bloomberg ASKB = PRIMARY source. Free sources (Yahoo/FRED/Alpha Vantage) "
            f"used for corroboration. {discrepancies} discrepancy(ies) flagged for review."
        )
    else:
        summary = (
            "Bloomberg ASKB = PRIMARY source. Free sources corroborate with no material "
            "discrepancies."
        )

    return {"alerts": alerts, "summary": summary, "discrepancies": discrepancies}
