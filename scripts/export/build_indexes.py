#!/usr/bin/env python3
"""
build_indexes.py
Create compact JSON indexes from YAML front-matter in data/pages_clean/*.
Outputs:
  exports/index_pages.json
  exports/index_posts.json
  exports/index_products.json
"""

from pathlib import Path
import json
import re
from typing import Dict, Any, Optional, Tuple

try:
    import yaml  # PyYAML
except ImportError:
    raise SystemExit("Missing dependency: pyyaml. Install with: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[2]  # .../vericor-crawl
DATA_DIR = ROOT / "data" / "pages_clean"
EXPORTS_DIR = ROOT / "exports"

# Folders we expect under data/pages_clean/
BUCKETS = {
    "pages": "index_pages.json",
    "posts": "index_posts.json",
    "products": "index_products.json",
}

# Tolerant front-matter regex: allows BOM, blank lines, CRLF, etc.
FRONTMATTER_RE = re.compile(
    r"^\ufeff?\s*---\s*\r?\n(.*?)\r?\n---\s*\r?\n?",
    re.DOTALL | re.MULTILINE
)


def split_frontmatter_and_body(text: str) -> Tuple[Dict[str, Any], str]:
    """Split a Markdown file into front-matter dict and body text."""
    m = FRONTMATTER_RE.search(text)
    fm = {}
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
            text = text[m.end():]
        except yaml.YAMLError:
            pass
    return (fm if isinstance(fm, dict) else {}), text


def first_heading(text: str) -> Optional[str]:
    """Find the first Markdown heading (# Heading)."""
    m = re.search(r"(?m)^\s*#\s+(.+)$", text)
    return m.group(1).strip() if m else None


def minimize_record(fm: Dict[str, Any], *, fallback_type: str, slug: str, body_text: str) -> Dict[str, Any]:
    """Build a compact record and infer missing fields."""
    taxonomy = fm.get("taxonomy", {}) or {}

    rec_id = fm.get("id") or fm.get("sku") or slug
    rec_type = (fm.get("type") or fallback_type).lower()
    title = fm.get("title") or first_heading(body_text)

    return {
        "id": rec_id,
        "type": rec_type,
        "title": title,
        "url": fm.get("url"),
        "slug": fm.get("slug") or slug,
        "updated_at": fm.get("updated_at"),
        "categories": taxonomy.get("categories", []),
        "tags": taxonomy.get("tags", []),
        "h1": (fm.get("seo") or {}).get("h1"),
        "meta_title": (fm.get("seo") or {}).get("meta_title"),
        "meta_description": (fm.get("seo") or {}).get("meta_description"),
        "word_count": (fm.get("metrics") or {}).get("word_count"),
    }


def main():
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for bucket, out_name in BUCKETS.items():
        src_dir = DATA_DIR / bucket
        if not src_dir.exists():
            print(f"[warn] Missing folder: {src_dir} (skipping)")
            (EXPORTS_DIR / out_name).write_text("[]", encoding="utf-8")
            continue

        all_md = list(src_dir.rglob("*.md"))
        print(f"[info] Scanning {src_dir} ({len(all_md)} md files)")

        records = []
        for md in all_md:
            text = md.read_text(encoding="utf-8", errors="ignore")
            fm, body = split_frontmatter_and_body(text)
            slug = md.stem
            rec = minimize_record(fm, fallback_type=bucket[:-1] if bucket.endswith('s') else bucket, slug=slug, body_text=body or "")
            # Include if it has an ID and type at minimum
            if rec.get("id") and rec.get("type"):
                records.append(rec)

        out_path = EXPORTS_DIR / out_name
        out_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[ok] Wrote {out_path}  ({len(records)} records)")

    print("[done] Index build complete")


if __name__ == "__main__":
    main()
