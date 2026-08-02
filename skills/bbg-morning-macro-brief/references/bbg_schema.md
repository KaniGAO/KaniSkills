# Bloomberg ASKB Paste — Parser Contract (Schema)

This documents the exact delimited-markdown structure our `scripts/bbg/parse.py`
expects from a Bloomberg ASKB morning-brief paste, and how each section maps into
the final DOCX report.

## Required envelope

```
AS OF: <HH:MM GMT, DATE>

## <SECTION HEADER>
... content (table or bullets) ...
```

- The `AS OF:` line (if present) is preserved in `raw` but not strictly required.
- Section headers are matched **by keyword** (case-insensitive, punctuation
  stripped), so ASKB may reword them slightly — see the keyword map below.
- Tables: first row = header, `|`-delimited, one row per instrument. Separator
  rows (`|---|`) are ignored.
- Narrative sections: one bullet per line (`-`/`*`/`•`). If no bullets, the whole
  block is treated as text.

## Section → canonical key (keyword match, first match wins)

| Canonical key | Keyword triggers | Report section | Exclusive? |
|---------------|------------------|----------------|------------|
| `news_flow` | markets live, news flow, first word, mliv, ni gmm | S4 lead-in (Markets Live) | ✅ |
| `equities` | equit, stock, index | S3 Equities | partially |
| `rates` | rate, fixed income, yield, bond, tenor | S3 Rates & Curves | partially |
| `credit_rates` | credit, swap spread, microstructure, cds, oas, basis | S3 (Bloomberg-exclusive) | ✅ |
| `commodities` | commod, metal, oil, gold | S3 Commodities | partially |
| `fx` | fx, forex, currency, exchange | S3 FX & Forwards | partially |
| `positioning` | positioning, flows, cftc, imm, trace, boos | S3 (Bloomberg-exclusive) | ✅ |
| `macro` | macro, develop | S4 Macro Developments | — |
| `central_bank` | central, bank, cb | S5 Central Bank Monitor | — |
| `talking_points` | talk, interview, point | S6 Interview Talking Points | — |
| `asia_day_ahead` | asia, day ahead, session | S7 Day Ahead — Asia | — |
| `key_levels` | key level, levels | Key Levels Dashboard | — |

> Order matters: `credit_rates` is checked before `rates`; `news_flow`,
> `positioning` are checked early so their broader keywords win.

## Bloomberg-exclusive flag

Sections tagged `[BBG-EXCLUSIVE]` in the header are rendered with the caption
"not externally verifiable" and are **excluded** from the cross-check module
(`crosscheck.py` only reconciles `equities` and `fx` against free sources).

## Parsed output shape

```python
{
  "raw": str,
  "news_flow":    {"type":"bullets"/"text", ...},   # optional
  "equities":     {"type":"table", "headers":[...], "rows":[[...]]},  # optional
  "rates":        {...},                              # optional table
  "credit_rates": {"type":"bullets"/"text", ...},    # optional [EXCLUSIVE]
  "commodities":  {...},                              # optional table
  "fx":           {...},                              # optional table
  "positioning":  {"type":"bullets"/"text", ...},    # optional [EXCLUSIVE]
  "macro":        {...},                              # optional
  "central_bank": {...},                              # optional
  "talking_points":{"type":"bullets","items":[...]}, # optional
  "asia_day_ahead":{...},                             # optional
  "key_levels":   {...},                              # optional table
}
```
