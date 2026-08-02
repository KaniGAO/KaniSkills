# Bloomberg ASKB — One-Shot Morning-Brief Workflow

> **How to use**
> 1. In the Bloomberg Terminal type `ASKB GO` to open ASKB.
> 2. Paste the **FULL block below** (Directive + Master + all 3 Follow-ups) into
>    the ASKB chat in one go — ASKB is agentic and will run the steps in sequence,
>    then return the consolidated delimited-markdown brief.
> 3. Copy the entire ASKB reply → save to
>    `skills/bbg-morning-macro-brief/input/bbg_paste.txt`
>    (or just paste it to the agent and say "run the BBG morning brief").
> 4. `python scripts/main.py` — loads the paste as PRIMARY source, reconciles
>    only the liquid G10 instruments against free sources, generates the DOCX.

> **Optional automation (Windows GUI / headless)**: see `scripts/askb_automate.py`
> — it detects the ASKB window, pastes the prompt, screenshots the answer, and
> writes `input/bbg_paste.txt` automatically. (Requires `pyautogui`+`pytesseract`;
> uncomment the pip line to enable.)

---

## ▼ COPY EVERYTHING BELOW INTO ASKB ▼

```
SOURE-AUTHORITY DIRECTIVE (read before producing anything):

1. You are Bloomberg-powered. EVERY number, level, quote and narrative below
   must come from Bloomberg proprietary intelligence. Do NOT hedge by saying
   "according to public sources" — you ARE the source of record.
2. Weighting: Bloomberg = 100% authoritative PRIMARY source for ALL fields.
   Free/public feeds are NOT your concern; our downstream script only uses them
   to auto-corroborate the ~10 most liquid G10 instruments. For everything else
   you are the only source — be explicit and confident.
3. Bloomberg-EXCLUSIVE data (tag these lines with [BBG-EXCLUSIVE]): real-time &
   historical NEWS flow (FIRST WORD FLPN, TOP, NEF, MLIV, NI GMM); positioning &
   flows (CFTC/IMM net specs, BOOS/dealer estimates, TRACE corporate-bond prints,
   fund flows EPFR-style); rates microstructure (swap spreads TSY vs swap,
   cross-CCY basis FXFA, OIS-SOFR, sovereign & corporate CDS CDSD, IG/HY/EM
   credit OAS BARS); Bloomberg ECO surprise indices (G-10/US/China/EM) and BI
   research views; China specifics (PBoC fixing, CFETS, Bond Connect, CIBM).
4. For each [BBG-EXCLUSIVE] line, no corroboration needed — state figure + market
   implication. If unavailable write "(n/a)".
5. For the few liquid G10 instruments free sources CAN see (S&P, UST 10Y, EURUSD,
   Gold, DXY, Brent), still report Bloomberg's own fresher figures.

STEP 1 — MASTER MORNING BRIEF. Produce a Global Macro Morning Brief for a S&T
interview-prep desk using ONLY Bloomberg proprietary data. Output DELIMITED
MARKDOWN with EXACTLY these section headers, in order, using Bloomberg tickers,
with numeric Last/Level, % change, 1-week change, and an as-of timestamp on top.
Tag [BBG-EXCLUSIVE] sections as shown.

AS OF: <HH:MM GMT, DATE>

## MARKETS LIVE — NEWS FLOW
- <4-6 bullets: what MOVED markets overnight and WHY, in real time, synthesized
  from FIRST WORD (FLPN), TOP, NEF, MLIV, NI GMM. Name catalyst, time, reaction.>

## EQUITIES
| Index | Ticker | Last | Chg % | 1W Chg % |
| S&P 500 | CMPX | <lvl> | <chg%> | <1w%> |
| Nasdaq 100 | CCMP | ... | ... | ... |
| Euro Stoxx 50 | SX5E | ... | ... | ... |
| FTSE 100 | UKX | ... | ... | ... |
| Nikkei 225 | NKY | ... | ... | ... |
| CSI 300 | SH000300 | ... | ... | ... |
| Hang Seng | HSI | ... | ... | ... |
| MSCI EM | XMEC | ... | ... | ... |

## RATES & CURVES
| Tenor | Ticker | Yield | 1W Chg (bps) |
| US 10Y | USGGB10 | <yield%> | <bps> |
| US 2Y | USGGB2 | ... | ... |
| US 30Y | USGGB30 | ... | ... |
| Bund 10Y | GUKG10 | ... | ... |
| Gilt 10Y | GUKG10 | ... | ... |
| JGB 10Y | GJGB10 | ... | ... |
- US 2s10s and 5s30s pivots + 1W change (bps).

## CREDIT & RATES MICROSTRUCTURE [BBG-EXCLUSIVE]
- Swap spreads: UST 10Y swap spread (bps) + 1W.
- Cross-CCY basis: EURUSD 5Y, USDJPY 5Y (FXFA) — flag widening.
- OIS-SOFR spread (bps).
- Sovereign CDS 5Y: US (CDSD US), Germany (CDSD GR), France (CDSD FR).
- Credit OAS: US IG (BARS), US HY, EM sovereign (EMBIG) — levels + 1W.
- Any dislocation vs 1Y range.

## COMMODITIES
| Asset | Ticker | Last | Chg % |
| Gold | XAU Curncy | <lvl> | <chg%> |
| WTI | CL1 | ... | ... |
| Brent | CO1 | ... | ... |
| Copper | HG1 | ... | ... |
| Natural Gas | NG1 | ... | ... |
| Silver | XAG | ... | ... |

## FX & FORWARDS
| Pair | Ticker | Rate | Chg % |
| EURUSD | EURUSD Curncy | <rate> | <chg%> |
| USDJPY | USDJPY Curncy | ... | ... |
| GBPUSD | GBPUSD Curncy | ... | ... |
| USDCNH | USDCNH Curncy | ... | ... |
| DXY | DXY | ... | ... |
- Dominant FX forward points / carry note.

## POSITIONING & FLOWS [BBG-EXCLUSIVE]
- CFTC/IMM net specs: EUR, JPY, Gold, US 10Y, Brent — net (k contracts) + 1W; flag CROWDED.
- BOOS/dealer positioning estimate (where available).
- TRACE: notable US IG/HY corporate-bond flow color.
- Fund flows (EPFR-style): equity vs bond, US vs EM, last week net.
- One explicit "where is the crowd wrong?" call.

## MACRO DEVELOPMENTS
- <3-5 bullets> key macro prints/data last 24h WITH figures. Lead with Bloomberg
  ECO surprise indices: US G-10 Surprise, China, EM (level & direction). Why it matters.

## CENTRAL BANK
- <bullets> using BECO / POE / BFW / WIR. Upcoming decisions, policy signals,
  market-implied hike/cut probabilities, key quotes Fed/ECB/BOJ/PBoC/BOE.

## INTERVIEW TALKING POINTS
- <5-7 data-driven points, EACH tied to a Bloomberg number/event>. At least TWO
  must draw on [BBG-EXCLUSIVE] positioning or microstructure.

## ASIA DAY AHEAD
- <bullets> Asia session watch: China (PBoC fixing, CFETS, Bond Connect, CIBM),
  Japan (BOJ, 日元), HK; key levels + catalysts.

## KEY LEVELS
| Asset | Support | Resistance | Note |
| S&P 500 | <lvl> | <lvl> | <note> |
| US 10Y | <lvl> | <lvl> | <note> |
| EURUSD | <lvl> | <lvl> | <note> |
| USDJPY | <lvl> | <lvl> | <note> |
| Gold | <lvl> | <lvl> | <note> |

STEP 2 — DEEPEN TALKING POINTS. For the INTERVIEW TALKING POINTS above, expand
each into one sentence connecting the data point to a trade-able market
implication (rates/FX/equity direction), explicitly referencing the positioning
or microstructure figure behind it. Keep the same numbered list.

STEP 3 — ASIA PRECISION. Expand ASIA DAY AHEAD with concrete levels for CSI 300,
Nikkei 225 and Hang Seng, referencing prior close, PBoC fixing bias, and key macro
catalysts. Add USDCNH 1Y forward points if notable.

STEP 4 — NEWS DEEP DIVE. Expand MARKETS LIVE — NEWS FLOW: for the top 2 catalysts
give exact Bloomberg headlines (NI/HP), the FIRST WORD timestamp, and the MLIV
strategist consensus view.

RULES: cite tickers + numbers; no vague claims. Tag Bloomberg-exclusive lines
[BBG-EXCLUSIVE]. If uncertain mark "≈" or "(unconfirmed)". Do NOT add commentary
outside the sections. After all steps, output the COMPLETE consolidated brief as
one delimited-markdown document.
```

## ▲ END COPY ▲

---

## One-line version (for the ASKB workflow title bar / saved prompt name)

> `Bloomberg-only morning macro brief: delimited-markdown with MARKETS LIVE news flow, EQUITIES/RATES/COMMODITIES/FX tables, [BBG-EXCLUSIVE] CREDIT & RATES MICROSTRUCTURE + POSITIONING & FLOWS, MACRO (lead w/ ECO surprise), CENTRAL BANK, INTERVIEW TALKING POINTS (≥2 from exclusive data), ASIA DAY AHEAD, KEY LEVELS; then deepen talking points, add Asia levels, and news deep-dive. Tag exclusive lines [BBG-EXCLUSIVE].`
