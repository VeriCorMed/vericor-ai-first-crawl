# preprocess_clean.py
"""
Clean the raw Markdown pages produced by deep_crawl_vcm.py.

HOW IT WORKS
============
• Reads every *.md file in  ./output/
• Keeps everything **between** the first Markdown heading (`# …`) and the last line *before* any footer‑type blocks.
• Removes site‑wide boiler‑plate:
    – phone/banner line (`Call 608‑526‑6901 …`)
    – giant nav menu that precedes the first heading
    – newsletter / Constant‑Contact block (starts with `### SIGN ME UP!`)
    – footer blocks such as `### CUSTOMER CARE`, © lines, etc.
    – stray `Search for:` prompts
• Normalises blank lines
• Writes cleaned files to ./clean/  (overwriting previous run)

Run with:  `python preprocess_clean.py`  from the project root.
"""

from __future__ import annotations

import hashlib
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

RAW_DIR = Path("output")
CLEAN_DIR = Path("clean")
CLEAN_DIR.mkdir(exist_ok=True)

# ── Regex helpers ────────────────────────────────────────────────────────────
PHONE_BANNER = re.compile(r"^Call +\d{3}-\d{3}-\d{4}.*?$", re.I | re.M)
NAV_BLOCK = re.compile(
    r"\[Skip to navigation.*?\]\(/?#site-navigation\).*?\n"  # a11y skip‑link
    r"(?:.*?\n)*?"                                             # anything until …
    r"Menu[^\n]*?\[Skip Navigation[^\n]*?\n",                 # menu end marker
    re.I | re.S,
)
FOOTER_BLOCK = re.compile(
    r"^#{2,3}\s*CUSTOMER\s+CARE.*$|^©.*$",  # footer heading or copyright
    re.I | re.M | re.S,
)
SEARCH_LINE = re.compile(r"^Search for:.*?$", re.I | re.M)
BLANKS = re.compile(r"\n{3,}")

# We will trim the Constant‑Contact stub by cutting at the first line that
# contains "sign me up" (case‑insensitive) and discarding everything after.

def cut_newsletter(lines: list[str]) -> list[str]:
    for i, line in enumerate(lines):
        if "sign me up" in line.lower():
            return lines[:i]
    return lines


# ── Cleaning routine ─────────────────────────────────────────────────────────

def clean_markdown(md: str) -> str:
    """Return markdown stripped of global nav, footer, newsletter, etc."""
    md = PHONE_BANNER.sub("", md)
    md = NAV_BLOCK.sub("", md)
    md = SEARCH_LINE.sub("", md)

    lines = md.splitlines()

    # keep only from first heading onward
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            lines = lines[idx:]
            break

    # cut everything from newsletter / footer onward
    lines = cut_newsletter(lines)
    for idx, line in enumerate(lines):
        if line.lower().startswith("### customer care") or line.lstrip().startswith("©"):
            lines = lines[:idx]
            break

    cleaned = "\n".join(lines)
    cleaned = FOOTER_BLOCK.sub("", cleaned)  # secondary catch‑all
    cleaned = BLANKS.sub("\n\n", cleaned).strip() + "\n"
    return cleaned


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not RAW_DIR.is_dir():
        sys.exit(f"❌  {RAW_DIR} not found – run the crawl first.")

    # Remove previous run so we always start fresh
    for f in CLEAN_DIR.glob("*.md"):
        f.unlink(missing_ok=True)

    processed = 0
    for md_file in RAW_DIR.glob("*.md"):
        raw = md_file.read_text(encoding="utf-8", errors="ignore")
        cleaned = clean_markdown(raw)
        (CLEAN_DIR / md_file.name).write_text(cleaned, encoding="utf-8")
        processed += 1

    ts = datetime.now(UTC).isoformat(timespec="seconds")
    print(f"✓ Cleaned {processed} files  → {CLEAN_DIR}  {ts}")


if __name__ == "__main__":
    main()
