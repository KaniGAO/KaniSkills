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
