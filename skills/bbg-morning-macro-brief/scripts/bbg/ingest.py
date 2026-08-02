"""Load a pasted Bloomberg ASKB file and parse it into a structured dict."""
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .parse import parse_bbg


def _skill_root() -> Path:
    # scripts/bbg/ingest.py -> resolve -> .../scripts/bbg -> parent x3 = skill_root
    return Path(__file__).resolve().parent.parent.parent


def _today_str() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")


def _extract_asof_date(text: str) -> str | None:
    """Try to read the date from an 'AS OF: <time>, <DATE>' line in a BBG paste."""
    m = re.search(
        r"AS\s*OF[:\s]+(?:[0-9]{2}:[0-9]{2}\s+[A-Za-z]+\s*,?\s*)?(\d{4}-\d{2}-\d{2})",
        text, re.IGNORECASE,
    )
    if m:
        return m.group(1)
    m2 = re.search(r"AS\s*OF[:\s]+.*?(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE | re.DOTALL)
    if m2:
        return m2.group(1)
    return None


def default_bbg_path() -> Path:
    """Default location of the ASKB paste.

    Prefers today's DATE-STAMPED paste (input/bbg_paste_YYYY-MM-DD.txt) so the
    daily history is preserved; falls back to the legacy input/bbg_paste.txt for
    the manual flow or when no dated file exists yet.
    """
    root = _skill_root()
    dated = root / "input" / f"bbg_paste_{_today_str()}.txt"
    if dated.exists():
        return dated
    return root / "input" / "bbg_paste.txt"


def save_paste(text: str) -> Path:
    """Persist a pasted BBG reply to a DATE-STAMPED file (never overwrites past days).

    The filename uses the AS OF date parsed from the paste when available, else
    today's date. Returns the saved path so the caller can feed it straight into
    `python scripts/main.py --bbg <path>` (the chained downstream skill).
    """
    root = _skill_root()
    date_str = _extract_asof_date(text) or _today_str()
    dated = root / "input" / f"bbg_paste_{date_str}.txt"
    dated.parent.mkdir(parents=True, exist_ok=True)
    dated.write_text(text, encoding="utf-8")
    return dated


def load_bbg(path=None) -> dict | None:
    """Load and parse a Bloomberg ASKB paste.

    Args:
        path: path to the pasted text file. If None, uses default_bbg_path().

    Returns:
        Parsed dict (see parse.parse_bbg) or None if missing/empty.
    """
    if path is None:
        path = default_bbg_path()
    p = Path(path)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    if not text.strip():
        return None
    return parse_bbg(text)
