"""Parse a Bloomberg ASKB "morning brief" paste into a structured dict.

The expected paste format is a delimited markdown produced by the ASKB prompt
in references/bbg_askb_prompts.md, e.g.:

    ## EQUITIES
    | Index | Ticker | Last | Chg % | 1W Chg % |
    | S&P 500 | CMPX | 5,430.20 | +0.82% | -1.10% |
    ...

    ## MACRO DEVELOPMENTS
    - Bullet narrative ...
    ...

The parser is tolerant: section headers are matched by keyword, tables are
detected by leading '|', and narrative sections fall back to bullet or text.
"""
import re

# canonical key -> list of substring keywords used to classify a header.
# ORDER MATTERS: broader / Bloomberg-exclusive sections are checked first so
# their keywords win over the generic "rates"/"equities" buckets.
KEYWORDS = {
    "news_flow": ["markets live", "news flow", "first word", "mliv", "ni gmm", "market wire"],
    "credit_rates": ["credit", "swap spread", "microstructure", "cds", "oas", "basis"],
    "positioning": ["positioning", "flows", "cftc", "imm", "trace", "boos"],
    "equities": ["equit", "stock", "index"],
    "rates": ["rate", "fixed", "yield", "bond", "tenor"],
    "commodities": ["commod", "metal", "oil", "gold"],
    "fx": ["fx", "forex", "currency", "exchange"],
    "macro": ["macro", "develop"],
    "central_bank": ["central", "bank", "cb"],
    "talking_points": ["talk", "interview", "point"],
    "asia_day_ahead": ["asia", "day ahead", "dayahead", "session"],
    "key_levels": ["key level", "levels"],
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _classify_header(title: str):
    t = _norm(title)
    for key, kws in KEYWORDS.items():
        for kw in kws:
            if _norm(kw) in t:
                return key
    return None


# Normalized phrasings that ONLY appear in real ASKB section headers (not body
# text). Used to detect headers that arrive WITHOUT the "## " markdown prefix
# (e.g. Bloomberg terminal copy-paste: "EQUITIES", "RATES & CURVES").
HEADER_SIGNATURES = [
    "marketslivenewsflow", "newsflow", "equities", "ratescurves",
    "creditratesmicrostructure", "commodities", "fxforwards",
    "positioningflows", "macrodevelopments", "centralbank",
    "interviewtalkingpoints", "asiadayahead", "keylevels",
]


def _is_all_caps(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def _looks_like_header(line: str) -> bool:
    """Detect a section header that may lack the '## ' markdown prefix.

    A bare line qualifies only if it (a) matches a header signature AND
    (b) is ALL-CAPS / carries a [BBG-EXCLUSIVE] tag — this prevents false
    positives from body sentences that mention e.g. 'equities' or 'key levels'.
    """
    s = line.strip()
    if not s:
        return False
    m = re.match(r"^#{1,3}\s+(.*)", line)
    title = m.group(1) if m else s
    nt = _norm(title)
    if not any(sig in nt for sig in HEADER_SIGNATURES):
        return False
    if m:
        return True  # already has a markdown prefix
    if "[BBG" in line.upper():
        return True
    return _is_all_caps(title)


def _is_separator(line: str) -> bool:
    s = line.strip()
    return bool(s) and set(s) <= set("|-: ")


def _split_table(text: str):
    lines = [l.rstrip() for l in text.splitlines() if l.strip().startswith("|")]
    if not lines:
        return None
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for l in lines[1:]:
        if _is_separator(l):
            continue
        cells = [c.strip() for c in l.strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(cells)
    if not rows:
        return None
    return {"type": "table", "headers": headers, "rows": rows}


def _split_space_table(text: str):
    """Parse a Bloomberg terminal space-aligned table (no '|' pipes).

    Detects a header line (>=3 columns when split on 2+ spaces) followed by
    at least 2 data rows; slices rows by the header's column offsets so that
    single-space values inside a cell (e.g. "-0.6 bps") stay intact.
    Trailing narrative paragraphs are preserved under "notes".
    """
    lines = text.splitlines()
    header_line = None
    start = -1
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        cols = re.split(r"\s{2,}", line.strip())
        if len(cols) < 3:
            return None  # first content line is prose, not a table header
        header_line = line
        start = i
        break
    if header_line is None:
        return None

    # column start offsets derived from the header line
    offsets = []
    idx = 0
    for c in cols:
        pos = header_line.index(c, idx)
        offsets.append(pos)
        idx = pos + len(c)

    rows = []
    j = start + 1
    while j < len(lines):
        ln = lines[j]
        s = ln.strip()
        if not s or set(s) <= set("═━─—-| "):
            break
        cells = []
        for k, off in enumerate(offsets):
            end = offsets[k + 1] if k + 1 < len(offsets) else len(ln)
            cells.append(ln[off:end].strip())
        if not cells[0]:
            break
        rows.append(cells)
        j += 1
    if len(rows) < 2:
        return None

    notes = []
    for ln in lines[j:]:
        s = ln.strip()
        if s and not set(s) <= set("═━─—-| "):
            notes.append(s)
    return {"type": "table", "headers": cols, "rows": rows, "notes": notes}


def _split_bullets(text: str):
    items = []
    for l in text.splitlines():
        s = l.strip()
        m = re.match(r"^[-*•‣]\s+(.*)", s) or re.match(r"^\d+[.)]\s+(.*)", s)
        if m:
            items.append(m.group(1).strip())
    return items


def parse_bbg(text: str) -> dict:
    """Parse raw ASKB paste text into a structured dict.

    Returns:
        {
          "raw": <original text>,
          "equities": {"type":"table","headers":[...],"rows":[[...]]},  # optional
          "rates": {...}, "commodities": {...}, "fx": {...},            # optional tables
          "macro": {"type":"bullets"/"text", ...},                      # optional
          "central_bank": {...}, "talking_points": {...},
          "asia_day_ahead": {...}, "key_levels": {...},                 # optional
        }
    """
    result: dict = {"raw": text}
    sections: dict = {}
    current = None
    buf = []

    for line in text.splitlines():
        m = re.match(r"^#{1,3}\s+(.*)", line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = _classify_header(m.group(1))
            buf = []
        elif _looks_like_header(line):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = _classify_header(line)
            buf = []
        else:
            if current is not None:
                buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()

    for key, content in sections.items():
        tbl = _split_table(content) or _split_space_table(content)
        if tbl:
            result[key] = tbl
            continue
        bullets = _split_bullets(content)
        if bullets:
            result[key] = {"type": "bullets", "items": bullets}
        elif content:
            result[key] = {"type": "text", "text": content}

    return result
