---
name: bbg-morning-macro-brief
description: |
  Generates a Global Markets Daily Briefing in DOCX with Bloomberg ASKB as the
  PRIMARY data source, corroborated by free sources (Yahoo Finance, FRED, Alpha
  Vantage). Use when the user wants a Bloomberg-driven morning macro brief, pastes
  a Bloomberg "ask KB" / ASKB output, or asks to "run the BBG morning brief".
  Expected flow: the user pastes Bloomberg ASKB text (or saves it to
  input/bbg_paste.txt); the skill then collects corroborating data, cross-checks
  the two, and produces the report.
---

# BBG Morning Macro Brief

A Bloomberg-ASKB–powered morning macro briefing. **Bloomberg is the PRIMARY
source**; Yahoo Finance / FRED / Alpha Vantage **corroborate** and flag
discrepancies. The report keeps the same 8-section format as
`global-markets-brief`, with Bloomberg driving the narrative sections.

## Concept

1. Each morning you run **Bloomberg ASKB** (Terminal / PORT / CRM) with the
   workflow in `references/bbg_askb_prompts.md`, then copy the reply.
2. Save it as a **DATE-STAMPED** file `input/bbg_paste_YYYY-MM-DD.txt` (UTF-8) —
   the date comes from the `AS OF:` line in the paste, else today. This preserves
   the daily history and never overwrites a previous day's paste. Alternatively,
   paste it into chat and ask the agent to "run the BBG morning brief".
3. The skill loads the paste, fetches corroborating free-source data, runs a
   cross-check, and generates the `.docx`.

## Agent self-driving (chained downstream skills) — IMPORTANT

When the user pastes a Bloomberg ASKB output (in chat) **or** points you at a
paste file, you MUST NOT stop after saving it. Treat the paste as the trigger to
**chain into the downstream skills** and run the whole pipeline to completion:

1. **Save** the paste to `input/bbg_paste_YYYY-MM-DD.txt` (dated; see Paste
   protocol). Prefer `bbg.ingest.save_paste(text)` so the date is derived from the
   `AS OF:` line — it returns the saved path you pass to step 2.
2. **Continue → generate the report (the downstream skill):** immediately run
   `python scripts/main.py --bbg <saved_dated_path>`. Do not ask "what next?".
3. If the user also wants delivery, **continue** with the email step:
   `python scripts/main.py --bbg <path> --send-email`.
4. Surface the final `.docx` path and a one-line summary of the
   cross-source flags. Only stop once the report file exists.

The rule: **paste-in → dated file → report-out**, fully chained. The agent is the
orchestrator; the Bloomberg paste is just the first input, not the final step.

## Bloomberg side — how to ask ASKB

See `references/bbg_askb_prompts.md` for the exact English prompts and the
required **output schema**. In short, ask ASKB to emit **delimited markdown**
with these sections (the parser keys off the headers):

- Tables: `## EQUITIES`, `## RATES`, `## COMMODITIES`, `## FX`
- Narrative / table: `## MACRO DEVELOPMENTS`, `## CENTRAL BANK`,
  `## INTERVIEW TALKING POINTS`, `## ASIA DAY AHEAD`, `## KEY LEVELS`

Instruct ASKB to cite Bloomberg tickers (e.g. `CMPX`, `USGGB10`, `XAU Curncy`,
`EURUSD Curncy`), numeric levels with % changes, and as-of timestamps, and to
flag anything it is uncertain about.

## Paste protocol

- **Option A (file):** save ASKB's reply as `input/bbg_paste_YYYY-MM-DD.txt`
  (date = `AS OF` date from the paste, else today). Each day gets its own file;
  past days are never overwritten. The legacy `input/bbg_paste.txt` still works
  as a fallback.
- **Option B (chat):** paste the reply into chat. The agent saves it via
  `bbg.ingest.save_paste(text)` → `input/bbg_paste_YYYY-MM-DD.txt`, then
  **immediately chains** into report generation (see Agent self-driving above).

## Run (agent side)

- Auto-load today's dated paste: `python scripts/main.py`
  (resolves `input/bbg_paste_YYYY-MM-DD.txt` for today, else `bbg_paste.txt`)
- Custom paste file: `python scripts/main.py --bbg input/bbg_paste_2026-07-27.txt`
- Email delivery (chains after generation): `python scripts/main.py --bbg <path> --send-email`
- ASKB auto-capture: `python scripts/main.py --askb-auto`
- Output: `<OUTPUT_DIR>/bbg-morning-macro-briefing-YYYY-MM-DD.docx`
  (default `OUTPUT_DIR = /Users/gaokanglin/CodeBuddy/Claw/reports`)

## Cross-check methodology

- **Bloomberg = authoritative primary** for both numbers and narrative.
- **Free sources = corroboration only.**
- **Rule 1:** if a free source is missing a field Bloomberg has → trust Bloomberg.
- **Rule 2:** if `|Δ%| > 1.0` or the change-direction signs conflict → flag it in
  the "Appendix: Data Quality & Reconciliation Log" (end of report) for review.
- **Rule 3:** qualitative narrative is always Bloomberg; free sources never
  override it.
- The agent (LLM) performs the **final calibration** when it reads both sources
  together before generating the report.

## Report format (10-minute readable)

Designed to be fully readable in **under 10 minutes** (body <= 8 pages):

- **Page 1 = Executive Summary (TL;DR)**: top story + biggest mover per asset
  class + a cross-asset snapshot table, followed by a live Word TOC field
  (right-click → Update Field to refresh page numbers).
- **Sections**: Monthly Macro Calendar + Today's Events → Overnight Market Recap
  (unified tables: right-aligned numerics, green/red change coloring, zebra rows;
  each starts with a bold "So what" line) → Latest Macro Developments + Central
  Bank Monitor → Interview Talking Points → Day Ahead (Asia) → Key Levels
  (support/resistance only — spot prices are NOT repeated).
- **Per-section budget**: max 1 table + a handful of bullets; overflow lines sink
  to the appendix, never bloating the body.
- **Scannable narrative items** (Sections 4/6): every item renders as a **bold
  lead-in** (headline / claim, smart title-cased — no ALL-CAPS shouting) followed
  by a body trimmed to <= 2 sentences (~48 words). Full untrimmed text is
  preserved in the appendix. This follows F-pattern scanning research: readers
  can skim bold anchors only and still get the storyline.
- **Appendix: Data Quality & Reconciliation Log**: all pipeline notices
  (settlement fallbacks, `close==prev_close`, unresolved tickers), cross-source
  flags and over-budget detail live here — engineering state never appears in
  the narrative body. Internal markers (`[BBG-EXCLUSIVE]`, `unconfirmed`,
  `level not available`) are stripped before rendering.

When Bloomberg input is present, the narrative sections and Section-3 tables are
**Bloomberg-driven** and captioned `Source: Bloomberg ASKB (primary)`; if no
paste is supplied, the skill falls back to the free-source behavior.

## Requirements

Same API keys as `global-markets-brief` for the free sources:
`FINNHUB_API_KEY`, `ALPHA_VANTAGE_KEY`, `NEWSAPI_KEY`, `FRED_API_KEY`.
**Bloomberg data requires no API key** in the skill — it comes from your Terminal
paste.
