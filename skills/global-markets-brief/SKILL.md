---
name: global-markets-brief
description: |
  Generates a Global Markets Daily Briefing in DOCX format.
  Collects real-time market data from Yahoo Finance, Finnhub, NewsAPI, FRED,
  and Alpha Vantage, then produces a professional report with 7 analytical
  sections plus a key levels dashboard. Can optionally deliver the report
  via Gmail SMTP. This skill should be used when the user wants a daily
  market briefing, asks to generate a report, or requests current market
  data in document form.
---

# Global Markets Daily Briefing Skill

Generates a comprehensive daily market briefing document (.docx) covering 
equities, fixed income, FX, commodities, economic calendar, and macro 
developments — matching the format of a professional S&T morning briefing.

## Quick Start

```bash
# Install dependencies (one time)
cd ~/.codebuddy/skills/global-markets-brief/scripts
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys

# Generate a report
python main.py

# Generate and email
python main.py --send-email

# Custom output path
python main.py --output /path/to/report.docx
```

## Data Sources

| Module | Source | Data | Auth |
|--------|--------|------|------|
| Live prices | Yahoo Finance | Indices, rates, commodities, VIX | Free |
| Market news | Finnhub | Global market headlines | API key |
| Macro news | NewsAPI | Economy/policy news | API key |
| Economic indicators | FRED (St. Louis Fed) | GDP, CPI, PCE, unemployment | API key |
| FX rates | Alpha Vantage | Major currency pairs | API key |
| Event calendar | Built-in | Central bank/economic calendar | Built-in |

## Scripts

### `scripts/main.py` — Entry point

```bash
python main.py
python main.py --send-email
python main.py --output ./my_report.docx --send-email
```

### `scripts/config.py` — Configuration

Loads API keys from `.env` file or environment variables.

### `scripts/collectors/` — Data collection modules

- `yahoo.py` — Fetches real-time market data
- `finnhub.py` — Fetches market news
- `newsapi_collector.py` — Fetches macro news
- `fred.py` — Fetches economic indicators
- `alpha_vantage.py` — Fetches FX rates
- `calendar.py` — Generates event calendar

### `scripts/generators/report.py` — DOCX report generator

Produces a professionally formatted document with:
1. Monthly Macro Calendar
2. Today's Events
3. Overnight Market Recap (Equities, Rates, Commodities, FX)
4. Latest Macro Developments
5. Central Bank Monitor
6. Interview Talking Points
7. Day Ahead — Asia Session Focus
8. Key Levels Dashboard

### `scripts/senders/email_sender.py` — Email delivery

Sends report as .docx attachment via Gmail SMTP.

## Automation

This skill supports daily automation. Example cron schedule: 6:30 AM HKT 
(Mon-Fri) to generate and deliver the briefing before market open.

## Configuration

Copy `.env.example` to `.env` and fill in:

```bash
FINNHUB_API_KEY=...    # https://finnhub.io
ALPHA_VANTAGE_KEY=...  # https://alphavantage.co
NEWSAPI_KEY=...        # https://newsapi.org
FRED_API_KEY=...       # https://fred.stlouisfed.org
GMAIL_SENDER_EMAIL=... # Gmail address for sending
GMAIL_APP_PASSWORD=... # Gmail App Password
RECIPIENT_EMAILS=[...] # JSON array of recipient emails
OUTPUT_DIR=...         # Report output directory
```

## Verification

To test data collection only:
```bash
cd ~/.codebuddy/skills/global-markets-brief/scripts
python -c "from collectors.yahoo import fetch_market_data; d=fetch_market_data(); print(f'OK: {len(d)} categories')"
```

## Self-Audit (报告自检 / Skill 反查)

当你需要「检验已生成的报告写没写对、质量如何」时，用 `scripts/audit/` 子模块。
设计原则：**确定性反查用 Python，定性评判交给 agent（按 prompt），不在 skill 内再写一套 LLM API。**

### 1) 跑反查，产出 audit bundle
```bash
cd ~/.codebuddy/skills/global-markets-brief/scripts
python audit/judge.py --report ../reports/global-markets-briefing-2026-07-21.docx
# 可选：--as-of 2026-07-21  指定真值基准日（默认取文件名日期）
# 可选：--output <dir>       指定 bundle 输出目录（默认与报告同目录）
```
产出（与报告同目录）：
- `audit_bundle.json` — 结构化：被审稿件 + 独立地面真值 + 数值偏差 + 叙事正文
- `audit_bundle.md` — 人 / agent 可读版

反查逻辑（确定性，无 LLM）：
- `report_parser.py` 解析 .docx，抽取各表数值断言与 Section 4-7 叙事正文
- `fetch_ground_truth.py` 复用 `collectors.yahoo` 的标的映射，用 yfinance 拉取
  **as_of 当日历史收盘**作为真值（避免用今天实时数据误判历史报告）
- `accuracy_check.py` 逐条比报告数值 vs 真值，超容差（点位 0.5% / 涨跌幅 0.3pp）标 MISMATCH

### 2) agent 做定性评判（按 prompt，不调 API）
读取 `audit/audit_bundle.md`（或 `.json`），按 `audit/JUDGE_PROMPT.md` 的 rubric
对报告打分（准确性 / 时效性 / 完整性 / 结构 / 来源 / 无幻觉，满分 30），输出审稿意见
（分数表 + 关键问题清单 + PASS/NEEDS_REVISION/FAIL + 给 skill 的改进建议）。

> 注意：`judge.py` 只产出 bundle，**评判由 agent 完成**——这是刻意设计：
> agent 调用 skill 时本就是 LLM，无需在 skill 里再发起一次外部模型调用。
