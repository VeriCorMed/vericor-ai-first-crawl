#!/usr/bin/env python3
"""
sitemap_subset.py
-----------------
Create pages_clean/ that contains only the .md files whose URL appears
in https://www.vericormed.com/sitemap_index.xml **or any of its *.xml / *.xml.gz children**.

Requires:  pip install requests lxml
Run from project root:  python sitemap_subset.py
"""

from __future__ import annotations

import gzip, io, re, shutil, sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from lxml import etree  # lxml is fast & tolerant

SITE_ROOT = "https://www.vericormed.com"
RAW_DIR = Path("clean")  # existing cleaned pages
DEST_DIR = Path("pages_clean")  # new subset folder
DEST_DIR.mkdir(exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────────────
SLUG_RGX = re.compile(r"[^a-z0-9\-_/]+", re.I)


def slug_from_url(url: str) -> str:
    """Convert a full URL to the slug used in filenames."""
    if not url.startswith(SITE_ROOT):
        return ""
    path = urlparse(url).path
    slug = path.strip("/")
    return slug  # empty string means home.md


def slug_from_filename(fn: str) -> str:
    """Reverse the naming we used when writing *.md files."""
    name = fn.rsplit(".", 1)[0]  # drop .md
    # remove social‑share params that survived filename stage
    name = re.sub(r"_nb=?\d*&share=(facebook|twitter).*", "", name, flags=re.I)
    return name


def parse_xml(url: str) -> list[str]:
    """Return list of <loc> URLs from a sitemap or sitemap‑index (.xml or .xml.gz)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; rv:128.0) "
            "Gecko/20100101 Firefox/128.0"
        )
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    data = gzip.decompress(resp.content) if url.endswith(".gz") else resp.content
    doc = etree.parse(io.BytesIO(data))
    return [
        node.strip() for node in doc.xpath("//*[local-name()='loc']/text()")
    ]


# ── Build sitemap URL set ────────────────────────────────────────────
print("Downloading sitemap index …")
try:
    locs = parse_xml(f"{SITE_ROOT}/sitemap_index.xml")
except Exception as exc:
    sys.exit(f"🛑  Could not fetch sitemap: {exc}")

urls: set[str] = set()
for loc in locs:
    if loc.endswith((".xml", ".xml.gz")):
        try:
            urls.update(parse_xml(loc))
        except Exception as exc:
            print(f"⚠️  Skip broken child sitemap {loc}: {exc}")
    else:
        urls.add(loc)

slugs = {slug_from_url(u) for u in urls}

# ── Copy matching files ─────────────────────────────────────────────
kept = skipped = 0
for md_path in RAW_DIR.glob("*.md"):
    # Skip social‑share duplicates straight away
    if re.search(r"_nb=.*?share=(facebook|twitter)", md_path.name, re.I):
        skipped += 1
        continue

    slug = slug_from_filename(md_path.stem)
    if slug in slugs or (slug == "home" and "" in slugs):
        shutil.copy2(md_path, DEST_DIR / md_path.name)
        kept += 1
    else:
        skipped += 1

print(
    f"✓ Copied {kept:,} sitemap pages → {DEST_DIR}  "
    f"(skipped {skipped:,} non-sitemap files)"
)
