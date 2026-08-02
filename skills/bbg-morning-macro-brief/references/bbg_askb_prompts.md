# Bloomberg ASKB Workflow — Refined & Weighted Prompts

> These prompts are pasted into **Bloomberg ASKB** (Terminal / PORT / CRM) each
> morning. They instruct ASKB to produce a **delimited-markdown** morning brief
> that our skill (`scripts/bbg/parse.py`) can parse and treat as the **PRIMARY,
> AUTHORITATIVE** source. Copy the entire ASKB reply into `input/bbg_paste.txt`.

---

## 0) Source-Authority Directive (paste this FIRST, then the Master)

This prelude sets the hierarchy. It is the single most important part — it tells
ASKB that Bloomberg is the only source that matters and that certain data classes
are **Bloomberg-exclusive** (never to be cross-checked downstream).

```
SOURCE-AUTHORITY DIRECTIVE (read before producing anything):

1. You are Bloomberg-powered. EVERY number, level, quote and narrative below
   must come from Bloomberg proprietary intelligence. Do NOT hedge by saying
   "according to public sources" — you ARE the source of record.

2. Weighting:
   - Bloomberg = 100% authoritative PRIMARY source for ALL fields.
   - Free/public feeds (Yahoo, FRED, web) are NOT your concern; our downstream
     script only uses them to auto-corroborate the ~10 most liquid G10 instruments.
     For everything else you are the only source — be explicit and confident.

3. Bloomberg-EXCLUSIVE data (tag these lines with [BBG-EXCLUSIVE]):
   These cannot be verified by any free source and must be treated as ground truth:
   - Real-time & historical NEWS flow: FIRST WORD (FLPN), TOP, NEF, MLIV, NI GMM
   - Positioning & flows: CFTC/IMM net specs, BOOS/dealer estimates, TRACE
     corporate-bond prints, fund flows (EPFR-style)
   - Rates microstructure: swap spreads (TSY vs swap), cross-CCY basis (FXFA),
     OIS–SOFR, sovereign & corporate CDS (CDSD), IG/HY/EM credit OAS (BARS)
   - Bloomberg ECO surprise indices (G-10 / US / China / EM) and BI research views
   - China specifics: PBoC fixing, CFETS, Bond Connect, CIBM flows

4. For each [BBG-EXCLUSIVE] line, you do NOT need corroboration. State the figure
   and its market implication directly. If genuinely unavailable, write "(n/a)".

5. For the few liquid G10 instruments that free sources CAN see (S&P, UST 10Y,
   EURUSD, Gold, DXY, Brent), still report Bloomberg's own figures and levels —
   they are fresher and the script will reconcile them automatically.
```

---

## 1) Master Morning-Brief Prompt (paste this right after the Directive)

```
Produce a Global Macro Morning Brief for a sales & trading (S&T) interview-prep
desk. Draw ONLY on Bloomberg proprietary data (prices, NEF/EMKT/ECO, rates,
FX, central-bank watch, analyst/BI notes, news flow). Use the SOURCE-AUTHORITY
DIRECTIVE above.

Output DELIMITED MARKDOWN with EXACTLY these section headers, in this order.
Use Bloomberg tickers. Include numeric Last/Level, % change, 1-week change and
an as-of timestamp at the very top. For [BBG-EXCLUSIVE] sections, tag the header.

AS OF: <HH:MM GMT, DATE>

## MARKETS LIVE — NEWS FLOW
- <4–6 bullets: what MOVED markets overnight and WHY, in real time. Synthesize
  from FIRST WORD (FLPN), TOP, NEF, MLIV and NI GMM. Name the catalyst, the time,
  and the immediate market reaction (e.g. "08:42 GMT — MLIV: roughly 70% of
  strategists see EURUSD pinned below 1.09 into ECB; bund yields ticked +3bp").
  This is your highest-value section — free sources cannot replicate the timing
  or journalist color.

## EQUITIES
| Index | Ticker | Last | Chg % | 1W Chg % |
| S&P 500 | CMPX | <lvl> | <chg%> | <1w%> |
... (Nasdaq 100 CCMP, Euro Stoxx 50 SX5E, FTSE 100 UKX, Nikkei 225 NKY,
     CSI 300 SH000300, Hang Seng HSI, MSCI EM XMEC)

## RATES & CURVES
| Tenor | Ticker | Yield | 1W Chg (bps) |
| US 10Y | USGGB10 | <yield%> | <bps> |
... (US 2Y, US 30Y, Bund 10Y GUKG10, Gilt 10Y GUKG10, JGB 10Y GJGB10)
- Also state the US 2s10s and 5s30s curve pivots and their 1W change (bps).

## CREDIT & RATES MICROSTRUCTURE [BBG-EXCLUSIVE]
- <bullets, each with a number>:
  • Swap spreads: UST 10Y swap spread (bps) and 1W change.
  • Cross-CCY basis: EURUSD 5Y basis, USDJPY 5Y basis (FXFA) — flag any widening.
  • OIS–SOFR spread (bps).
  • Sovereign CDS: US (CDSD US), Germany (CDSD GR), France (CDSD FR) 5Y (bps).
  • Credit OAS: US IG (BARS), US HY, EM sovereign (EMBIG) — levels and 1W change.
  • Note any dislocation or unusually tight/wide level vs 1Y range.

## COMMODITIES
| Asset | Ticker | Last | Chg % |
| Gold | XAU Curncy | <lvl> | <chg%> |
... (WTI CL1, Brent CO1, Copper HG1, Natural Gas NG1, Silver XAG)

## FX & FORWARDS
| Pair | Ticker | Rate | Chg % |
| EURUSD | EURUSD Curncy | <rate> | <chg%> |
... (USDJPY, GBPUSD, USDCNH, DXY)
- Add 1-line note on dominant FX forward points / carry (e.g. USDJPY 1Y fwd pts).

## POSITIONING & FLOWS [BBG-EXCLUSIVE]
- <bullets, each with a number>:
  • CFTC/IMM net speculative positioning for EUR, JPY, Gold, US 10Y, Brent —
    current net (k contracts) and 1W change; flag CROWDED extremes.
  • BOOS/dealer positioning estimate (where available).
  • TRACE: notable US IG/HY corporate-bond flow color (blocks, client vs pro).
  • Fund flows (EPFR-style): equity vs bond, US vs EM, last week's net.
  • One explicit "where is the crowd wrong?" call.

## MACRO DEVELOPMENTS
- <3–5 bullets>: most important macro prints/data in last 24h WITH figures.
  Lead with Bloomberg ECO surprise indices: US G-10 Surprise (level & direction),
  China (level), EM (level). Explain WHY it matters for rates/FX/equities.

## CENTRAL BANK
- <bullets>: using BECO / POE / BFW / WIR. Upcoming decisions, latest policy
  signals, market-implied hike/cut probabilities, key quotes from
  Fed / ECB / BOJ / PBoC / BOE. State expected policy rate where known.

## INTERVIEW TALKING POINTS
- <5–7 data-driven points a candidate must discuss, EACH tied to a Bloomberg
  number or event>. At least TWO must draw on [BBG-EXCLUSIVE] positioning or
  microstructure (this is your edge over candidates using only public data).

## ASIA DAY AHEAD
- <bullets>: what to watch in the Asia session — China (PBoC fixing, CFETS,
  Bond Connect, CIBM), Japan (BOJ,日元), HK, plus key levels and catalysts.

## KEY LEVELS
| Asset | Support | Resistance | Note |
| S&P 500 | <lvl> | <lvl> | <note> |
... (US 10Y, EURUSD, USDJPY, Gold, Brent)

RULES:
- Cite tickers + numbers; no vague claims.
- Tag Bloomberg-exclusive lines [BBG-EXCLUSIVE]; they are never cross-checked.
- If uncertain about ANY figure, mark it "≈" or "(unconfirmed)".
- Do NOT add commentary outside the sections above.
```

---

## 2) Optional Follow-up A — Deepen Talking Points (with microstructure)

```
For the INTERVIEW TALKING POINTS you just produced, expand each into one sentence
that connects the data point to a trade-able market implication (rates / FX /
equity direction), and explicitly reference the positioning or microstructure
figure behind it (e.g. "record-short JPY IMM specs mean a CPI miss = violent
short-covering rally in USDJPY"). Keep the same numbered list.
```

## 3) Optional Follow-up B — Asia Session Precision

```
Expand ASIA DAY AHEAD with concrete levels for CSI 300, Nikkei 225 and Hang Seng,
referencing prior close, the PBoC fixing bias, and the key macro catalysts from
your MACRO DEVELOPMENTS / MARKETS LIVE sections. Add 1Y FX forward points
(USDCNH) if notable.
```

## 4) Optional Follow-up C — News-Flow Deep Dive (the crown jewel)

```
Expand MARKETS LIVE — NEWS FLOW: for the top 2 catalysts, give the exact
Bloomberg headlines (NI/HP stories), the FIRST WORD timestamp, and the
MLIV strategist consensus view. This section is the differentiator — free
sources cannot reproduce it.
```

---

## Why this weighting (and what is Bloomberg-exclusive)

Bloomberg's moat is NOT the liquid G10 prices (Yahoo/FRED can approximate those).
It is everything around them that is **structurally unverifiable elsewhere**:

| Layer | Bloomberg advantage | Verifiable externally? |
|-------|--------------------|------------------------|
| News | FIRST WORD/MLIV/NEF/TOP — real-time *why*, journalist color, strategist consensus | **No** (timing + context) |
| Positioning | CFTC/IMM, BOOS dealer est., TRACE prints, fund flows | **No** (proprietary) |
| Microstructure | swap spreads, X-CCY basis, OIS-SOFR, sovereign CDS, credit OAS | **No** (deal-level) |
| Surprise indices | Bloomberg ECO surprise (US/China/EM) | **No** (proprietary index) |
| China | PBoC fixing, CFETS, Bond Connect, CIBM | **No / partial** |
| Liquid G10 prices | S&P, UST, EURUSD, Gold, Brent | Yes (used for auto-cross-check) |

Therefore the prompt **over-weights** the top 5 rows and explicitly tags them
`[BBG-EXCLUSIVE]` so our report treats them as authoritative and the
cross-check module never flags them as "discrepancies". Only the last row is
open to automated reconciliation.

## Paste & run

1. Paste Directive (0) + Master (1) into ASKB → copy full reply → `input/bbg_paste.txt`
2. `python scripts/main.py`  (auto-loads the paste; reconciles only liquid G10)
