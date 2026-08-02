"""Global Markets Daily Brief — 主入口

使用方法:
  python main.py                      # 生成报告到默认路径
  python main.py --send-email         # 生成并发送邮件
  python main.py --output ./my.docx   # 指定输出路径
  python main.py --bbg ./paste.txt    # 指定 Bloomberg ASKB 粘贴文件
  python main.py --askb-auto          # 自动驱动 ASKB 抓取回复并生成报告(需 pyautogui)
"""
import sys
import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 确保能找到同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from storage import db
from reconcile.quality import reconcile
from reconcile.verify import (
    cross_check_fx, web_verify, multi_source_summary,
    load_web_evidence, web_evidence_verify,
)
from collectors.yahoo import fetch_market_data, fetch_fx_rates_yahoo
from collectors.finnhub import fetch_market_news
from collectors.newsapi_collector import fetch_macro_news
from collectors.fred import fetch_fred_data
from collectors.alpha_vantage import fetch_fx_rates
from collectors.calendar import generate_calendar, overlay_db_earnings
from generators.report import generate_report
from senders.email_sender import send_report
# Bloomberg ASKB 主源（粘贴解析 + 跨源交叉校验）
from bbg.ingest import load_bbg, default_bbg_path
from bbg.crosscheck import run_crosscheck


def collect_all_data(run_id: str = None) -> dict:
    """采集所有数据源（带 run_id 审计写库）"""
    print("=" * 50)
    print("  Global Markets Daily Brief — Data Collection")
    print("=" * 50)

    print("\n[1/7] Fetching market data (Yahoo Finance)...")
    market_data = fetch_market_data(run_id=run_id)
    indices_count = len(market_data.get("indices", {}))
    print(f"  → {indices_count} indices, {len(market_data.get('rates',{}))} rates, "
          f"{len(market_data.get('commodities',{}))} commodities")

    print("\n[2/7] Fetching market news (Finnhub)...")
    finnhub_news = fetch_market_news()
    print(f"  → {len(finnhub_news)} articles")

    print("\n[3/7] Fetching global news (NewsAPI)...")
    newsapi_articles = fetch_macro_news()
    print(f"  → {len(newsapi_articles)} articles")

    print("\n[4/7] Fetching economic indicators (FRED)...")
    economic_data = fetch_fred_data(run_id=run_id)
    print(f"  → {len(economic_data)} series")

    print("\n[5/7] Fetching FX rates — Yahoo (primary)...")
    fx_rates = fetch_fx_rates_yahoo(run_id=run_id)
    print(f"  → {len(fx_rates)} pairs (Yahoo)")

    print("\n[6/7] Fetching FX rates — Alpha Vantage (supplement for reconcile)...")
    av_fx = fetch_fx_rates(run_id=run_id, pairs_limit=5)
    print(f"  → {len(av_fx)} pairs (AV)")
    # 合并：Yahoo 为主源，AV 仅补充缺失项
    for pair, info in av_fx.items():
        fx_rates.setdefault(pair, info)

    print("\n[7/7] Generating event calendar...")
    calendar_events = generate_calendar()
    calendar_events = overlay_db_earnings(calendar_events)
    print(f"  → {len(calendar_events)} events")

    # 合并新闻
    all_articles = finnhub_news + newsapi_articles
    # 去重
    seen = set()
    deduped = []
    for a in all_articles:
        url = a.get("url", "")
        if url and url not in seen:
            seen.add(url)
            deduped.append(a)

    print(f"\n  Total unique articles: {len(deduped)}")
    print(f"  Calendar events: {len(calendar_events)}")

    return {
        "market_data": market_data,
        "economic_data": economic_data,
        "fx_rates": fx_rates,
        "av_fx": av_fx,
        "news_articles": deduped,
        "calendar_events": calendar_events,
    }


def _build_hunyuan_verifier():
    """构造基于 Hunyuan 的 FX 方向/量级校验器（仅作辅助，无 Key 时返回 None）。"""
    if not Config.HUNYUAN_API_KEY:
        return None
    import json
    import urllib.request

    def verifier(quotes: dict) -> list:
        fx = quotes.get("fx_rates", {})
        payload = {p: info.get("change_pct") for p, info in fx.items()}
        prompt = (
            "你是全球市场日报的数据校验员。下面是由 Yahoo Finance 抓取的 FX 涨跌幅(%)，"
            "请基于公开市场知识判断是否存在明显异常（方向或量级可疑）。\n"
            f"数据: {json.dumps(payload, ensure_ascii=False)}\n"
            "仅返回 JSON 数组（元素为字符串告警），无异常则返回 []。"
        )
        try:
            body = json.dumps({
                "model": "hunyuan-standard",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }).encode("utf-8")
            req = urllib.request.Request(
                Config.HUNYUAN_BASE_URL.rstrip("/") + "/chat/completions",
                data=body,
                headers={"Authorization": f"Bearer {Config.HUNYUAN_API_KEY}",
                         "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return json.loads(data["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"  [verify] Hunyuan 调用失败（忽略）: {e}")
            return []

    return verifier


def _build_web_verifier(evidence: dict):
    """构造网页核验 verifier（ENABLE_WEB_VERIFY 时注入）。

    组合两层：
      1) 证据交叉校验（web_evidence_verify）——把 pipeline 报价与自动化锁定的
         独立网页核验证据做价格/方向比对，是网页搜索多重校验的核心，不依赖外部 API。
      2) Hunyuan FX 辅助校验（仅在配置了 HUNYUAN_API_KEY 时叠加）。
    任一层失败都静默降级，不阻断链路。
    """
    hunyuan = _build_hunyuan_verifier()

    def verifier(quotes: dict) -> list:
        alerts: list = []
        # 层 1：证据交叉校验（核心）
        if evidence:
            alerts += web_evidence_verify(
                quotes.get("market_data", {}),
                quotes.get("fx_rates", {}),
                evidence,
            )
        # 层 2：Hunyuan FX 辅助校验（可选）
        if hunyuan:
            try:
                alerts += hunyuan(quotes)
            except Exception as e:
                print(f"  [verify] Hunyuan 辅助校验异常（忽略）: {e}")
        return alerts

    return verifier


def run(send_email: bool = False, output_path: str = None, bbg_path: str = None, askb_auto: bool = False, recipients: list[str] = None) -> str:
    """运行日报生成流程"""
    # 初始化审计/校验存储层
    db.init_db()
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc) + timedelta(hours=8)
    as_of_date = now.strftime("%Y-%m-%d")
    print(f"  [Audit] run_id={run_id} as_of={as_of_date}")

    # 默认输出路径
    if not output_path:
        date_str = now.strftime("%Y-%m-%d")
        output_dir = Config.OUTPUT_DIR
        output_path = os.path.join(output_dir, f"bbg-morning-macro-briefing-{date_str}.docx")

    # ── Bloomberg ASKB 主源加载 ──
    bbg = None
    if bbg_path is None:
        bbg_path = default_bbg_path()
    if askb_auto:
        # 自动驱动 Bloomberg ASKB（需 pyautogui/pyperclip），抓取回复写入默认粘贴路径
        print("  [Bloomberg] --askb-auto: 正在驱动 ASKB 抓取回复...")
        try:
            import askb_automate
            askb_automate.capture()
            bbg_path = default_bbg_path()
        except Exception as e:
            print(f"  [Bloomberg] ⚠ ASKB 自动抓取失败：{e}；回退到手动粘贴。")
    if bbg_path and os.path.exists(bbg_path):
        bbg = load_bbg(bbg_path)
        print(f"  [Bloomberg] Loaded ASKB paste from {bbg_path}")
    else:
        print("  [Bloomberg] No ASKB paste found — using free sources only.")

    # 采集数据
    data = collect_all_data(run_id=run_id)

    # ── 跨源交叉校验（Bloomberg 主源 vs 佐证源）──
    crosscheck = run_crosscheck(bbg, data["market_data"], data["fx_rates"], data["economic_data"]) if bbg else None
    if crosscheck:
        print(f"  [Bloomberg] {crosscheck['summary']}")
        for a in crosscheck["alerts"]:
            print(f"     ⚠ {a}")

    # 发布前 reconcile / 质量断言
    print(f"\n{'=' * 50}")
    print("  Reconciling & Quality Checks...")
    print(f"{'=' * 50}")
    qa = reconcile(
        run_id=run_id,
        market_data=data["market_data"],
        news_articles=data["news_articles"],
        as_of_date=as_of_date,
    )
    quality_alerts = qa["alerts"]

    # ── 多源检测 + 网页校验（原思考者机制）──
    print(f"\n{'=' * 50}")
    print("  Multi-source Verification...")
    print(f"{'=' * 50}")
    verify_alerts = cross_check_fx(data["fx_rates"], data.get("av_fx", {}))

    # 网页核验证据（由每日 06:00 Hunyuan 自动化基于多源网页搜索 + 多数投票锁定）
    evidence = {}
    if Config.ENABLE_WEB_VERIFY:
        evidence_path = os.path.join(
            Config.WEB_EVIDENCE_DIR,
            f"web_evidence_{as_of_date}.json",
        )
        evidence = load_web_evidence(evidence_path)
        print(f"  [verify] ENABLE_WEB_VERIFY=1; 证据文件={evidence_path} "
              f"({'已载入' if evidence else '未找到→降级'})")
        # 网页证据驱动的偏差校正（多重校验闭环：发现偏离 → 用多源证据修正）
        if evidence:
            from reconcile.correct import apply_evidence_corrections
            corrections = apply_evidence_corrections(
                data["market_data"], data["fx_rates"], data["economic_data"],
                evidence, run_id=run_id,
            )
            if corrections:
                print(f"  [correct] 网页证据校正 {len(corrections)} 项:")
                for c in corrections:
                    print(f"     • {c}")
                verify_alerts.append(
                    f"[correct] 网页证据多重校验校正 {len(corrections)} 项: " + "; ".join(corrections))
        verify_alerts += web_verify(data, _build_web_verifier(evidence))
    else:
        verify_alerts += web_verify(data, None)
    if verify_alerts:
        print(f"  ⚠ {len(verify_alerts)} verification alert(s):")
        for a in verify_alerts:
            print(f"     • {a}")
        quality_alerts = quality_alerts + verify_alerts
    else:
        print("  ✓ Multi-source checks passed.")

    if quality_alerts:
        print(f"  [汇总] 共 {len(quality_alerts)} 条质量/校验告警。")
    else:
        print("  ✓ No quality alerts; all sources consistent.")

    # 生成报告
    print(f"\n{'=' * 50}")
    print("  Generating Report...")
    print(f"{'=' * 50}")
    report_path = generate_report(
        market_data=data["market_data"],
        economic_data=data["economic_data"],
        fx_rates=data["fx_rates"],
        news_articles=data["news_articles"],
        calendar_events=data["calendar_events"],
        output_path=output_path,
        quality_alerts=quality_alerts,
        bbg=bbg,
        crosscheck=crosscheck,
    )

    # 发送邮件
    if send_email:
        print(f"\n{'=' * 50}")
        print("  Sending Email...")
        print(f"{'=' * 50}")
        success = send_report(report_path, recipients=recipients)
        if success:
            print("  ✅ Email sent successfully!")
        else:
            print("  ⚠️  Email sending failed (check config)")
    else:
        print("\n  (Use --send-email to also send via email)")

    print(f"\n{'=' * 50}")
    print(f"  ✅ Done! Report: {report_path}")
    print(f"{'=' * 50}")

    return report_path


if __name__ == "__main__":
    send_email = "--send-email" in sys.argv
    askb_auto = "--askb-auto" in sys.argv

    output_path = None
    bbg_path = None
    recipients = None
    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]
        elif arg == "--bbg" and i + 1 < len(sys.argv):
            bbg_path = sys.argv[i + 1]
        elif arg == "--to" and i + 1 < len(sys.argv):
            # 逗号或空格分隔的收件人列表，覆盖 .env 中的 RECIPIENT_EMAILS
            recipients = [r.strip() for r in sys.argv[i + 1].replace(" ", ",").split(",") if r.strip()]

    run(send_email=send_email, output_path=output_path, bbg_path=bbg_path, askb_auto=askb_auto, recipients=recipients)
