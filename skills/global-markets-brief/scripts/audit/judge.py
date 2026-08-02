"""Skill 自检入口：把报告当成待审稿件，反查数字是否写对，产出 audit bundle。

用法:
  python judge.py --report <path> [--as-of YYYY-MM-DD] [--output <dir>]

产出:
  <dir>/audit_bundle.json   结构化的「被审稿件 + 地面真值 + 偏差」
  <dir>/audit_bundle.md     人 / agent 可读版

注意：本脚本只做确定性反查，不调用任何 LLM API。
      定性评判由 agent 读取 bundle 后，按 audit/JUDGE_PROMPT.md 的 rubric 完成。
"""
import argparse
import json
import os
import sys

# 保证能 import 同目录模块与上层 collectors
AUDIT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AUDIT_DIR)
sys.path.insert(0, os.path.dirname(AUDIT_DIR))  # scripts/ → collectors 等

from report_parser import parse_report
from fetch_ground_truth import fetch_ground_truth
from accuracy_check import check_accuracy


def _summary_block(parsed):
    r = parsed["recap"]
    return {
        "equities": len(r["equities"]),
        "rates": len(r["rates"]),
        "commodities": len(r["commodities"]),
        "fx": len(r["fx"]),
        "key_levels": len(parsed["key_levels"]),
        "narrative_sections": list(parsed["narrative"].keys()),
        "data_availability": parsed.get("data_availability", {}),
        "dateline": parsed.get("dateline"),
    }


def run(report_path, as_of=None, output_dir=None) -> dict:
    parsed = parse_report(report_path)
    as_of = as_of or parsed["report_date"]
    if not as_of:
        raise SystemExit("无法推断 as_of 日期，请用 --as-of 指定")

    truth = fetch_ground_truth(as_of)
    acc = check_accuracy(parsed, truth)

    bundle = {
        "report_path": report_path,
        "report_date": parsed["report_date"],
        "dateline": parsed.get("dateline"),
        "as_of_date": as_of,
        "truth_data_date": truth.get("truth_data_date"),
        "data_availability": parsed.get("data_availability", {}),
        "ground_truth": truth,
        "parsed_summary": _summary_block(parsed),
        "accuracy": acc,
        "recap": parsed["recap"],
        "key_levels": parsed["key_levels"],
        "narrative": parsed["narrative"],
    }

    output_dir = output_dir or os.path.dirname(os.path.abspath(report_path))
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "audit_bundle.json")
    md_path = os.path.join(output_dir, "audit_bundle.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)
    _write_md(md_path, bundle)

    s = acc["summary"]
    print(f"\n{'=' * 50}\n  Audit Bundle 完成\n{'=' * 50}")
    print(f"  报告日期: {parsed['report_date']}  | 真值基准日: {truth.get('truth_data_date')}")
    print(f"  检查项: {s['total_checks']}  通过: {s['ok']}  偏差: {s['mismatches']}  缺真值: {s['no_truth']}")
    if s["accuracy_rate"] is not None:
        print(f"  数字准确率: {s['accuracy_rate']}%")
    for d in acc["discrepancies"]:
        if d["status"] == "MISMATCH":
            print(f"    • {d['asset']} [{d['metric']}] 报告={d['reported']} 真值={d['expected']} 偏差={d['deviation']}{d['unit']}")
    print(f"\n  → {json_path}\n  → {md_path}")
    print(f"  接下来：按 audit/JUDGE_PROMPT.md 的 rubric 做定性评判。")
    return bundle


def _write_md(path, bundle):
    lines = []
    lines.append(f"# Audit Bundle — {os.path.basename(bundle['report_path'])}")
    lines.append(f"- 报告日期: {bundle['report_date']}  (dateline: {bundle.get('dateline')})")
    lines.append(f"- 真值基准日(as_of): {bundle['as_of_date']} (truth_data_date={bundle['truth_data_date']})")
    avail = bundle.get("data_availability", {})
    avail_str = "  ".join(f"{k}={v}" for k, v in avail.items())
    lines.append(f"- 数据可用性: {avail_str}")
    s = bundle["accuracy"]["summary"]
    lines.append(f"- 数字准确率: {s['accuracy_rate']}%  "
                 f"(检查 {s['total_checks']} / 通过 {s['ok']} / 偏差 {s['mismatches']} / 缺真值 {s['no_truth']})")
    lines.append("")
    lines.append("## 数值偏差明细")
    any_flag = False
    for d in bundle["accuracy"]["discrepancies"]:
        if d["status"] != "OK":
            any_flag = True
            lines.append(f"- [{d['status']}] {d['asset']} {d['metric']}: "
                         f"报告={d['reported']} 真值={d['expected']} 偏差={d['deviation']}{d['unit']}")
    if not any_flag:
        lines.append("- 无偏差")
    lines.append("")
    lines.append("## 叙事正文（供定性评判）")
    for title, text in bundle["narrative"].items():
        lines.append(f"### {title}")
        lines.append(text)
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    run(args.report, as_of=args.as_of, output_dir=args.output)
