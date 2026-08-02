"""把报告里的数值断言，对照地面真值做偏差核查（确定性，无 LLM）。"""

PRICE_TOL_PCT = 0.5   # 点位相对偏差容忍（%）
CHG_TOL_PP = 0.3      # 涨跌幅绝对偏差容忍（百分点）


def _cmp_price(reported, expected, tol=PRICE_TOL_PCT):
    if reported is None or expected in (None, 0):
        return None
    dev = abs(reported - expected) / abs(expected) * 100
    return dev <= tol, dev


def _cmp_chg(reported, expected, tol=CHG_TOL_PP):
    if reported is None or expected is None:
        return None
    dev = abs(reported - expected)
    return dev <= tol, dev


def check_accuracy(parsed: dict, truth: dict) -> dict:
    disc = []

    def add(asset, metric, reported, expected, ok, dev, unit=""):
        if ok is None:
            status = "NO_TRUTH"
        else:
            status = "OK" if ok else "MISMATCH"
        disc.append({
            "asset": asset, "metric": metric,
            "reported": reported, "expected": expected,
            "deviation": round(dev, 3) if dev is not None else None,
            "unit": unit, "status": status,
        })

    for e in parsed["recap"]["equities"]:
        t = truth["indices"].get(e["name"])
        if not t:
            add(e["name"], "price", e["last"], None, None, None); continue
        r = _cmp_price(e["last"], t["price"])
        add(e["name"], "price", e["last"], t["price"], r[0], r[1])
        r = _cmp_chg(e["chg_pct"], t["change_pct"])
        add(e["name"], "chg_pct", e["chg_pct"], t["change_pct"], r[0], r[1], "pp")

    for c in parsed["recap"]["commodities"]:
        t = truth["commodities"].get(c["name"])
        if not t:
            add(c["name"], "price", c["last"], None, None, None); continue
        r = _cmp_price(c["last"], t["price"])
        add(c["name"], "price", c["last"], t["price"], r[0], r[1])
        r = _cmp_chg(c["chg_pct"], t["change_pct"])
        add(c["name"], "chg_pct", c["chg_pct"], t["change_pct"], r[0], r[1], "pp")

    for rt in parsed["recap"]["rates"]:
        t = truth["rates"].get(rt["name"])
        if not t:
            add(rt["name"], "yield", rt["yield"], None, None, None); continue
        r = _cmp_price(rt["yield"], t["price"])
        add(rt["name"], "yield", rt["yield"], t["price"], r[0], r[1])
        r = _cmp_chg(rt["w1_change"], t["weekly_change_pct"])
        add(rt["name"], "1w_change", rt["w1_change"], t["weekly_change_pct"], r[0], r[1], "pp")

    for f in parsed["recap"]["fx"]:
        t = truth["fx"].get(f["pair"])
        if not t:
            add(f["pair"], "rate", f["rate"], None, None, None); continue
        r = _cmp_price(f["rate"], t["price"])
        add(f["pair"], "rate", f["rate"], t["price"], r[0], r[1])
        r = _cmp_chg(f["change_pct"], t["change_pct"])
        add(f["pair"], "chg_pct", f["change_pct"], t["change_pct"], r[0], r[1], "pp")

    mismatches = [d for d in disc if d["status"] == "MISMATCH"]
    no_truth = [d for d in disc if d["status"] == "NO_TRUTH"]
    ok = len(disc) - len(mismatches) - len(no_truth)
    summary = {
        "total_checks": len(disc),
        "ok": ok,
        "mismatches": len(mismatches),
        "no_truth": len(no_truth),
        "accuracy_rate": round(ok / len(disc) * 100, 1) if disc else None,
    }
    return {"discrepancies": disc, "summary": summary}
