# export_products_to_audit.py
"""
Build a Products sheet that matches the column order/names of your reference workbook.

Inputs
- pages_clean/products/*.md (your exported/cleaned product Markdown with YAML front-matter)
- (optional) --schema "Products for audit.xlsx"  -> read header row from its 'Products' sheet

Output
- vericor_products_audit.xlsx (default) with a 'Products' worksheet matching the schema
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Any

import frontmatter
import pandas as pd

# ---------- helpers ----------

def load_schema_columns(schema_path: Path | None) -> List[str]:
    """
    If schema_path provided, read the 'Products' sheet columns from the given workbook.
    Otherwise return a sensible default list (kept short—adjust as needed).
    """
    if schema_path and schema_path.exists():
        try:
            xls = pd.ExcelFile(schema_path)
            sheet_name = "Products"
            if sheet_name not in xls.sheet_names:
                raise ValueError(f"Sheet '{sheet_name}' not found in {schema_path.name}")
            df = pd.read_excel(schema_path, sheet_name=sheet_name, nrows=0)
            cols = df.columns.tolist()
            if not cols:
                raise ValueError("No columns found in reference sheet.")
            return cols
        except Exception as e:
            print(f"⚠ Failed to read schema from {schema_path}: {e}")
            print("  → Falling back to a small default schema.")
    # Minimal fallback (edit if you want more defaults)
    return [
        "Order", "Model#", "Webpage",
        "Section", "Section Detail",
        "Description", "Price", "Freight/Ground",
        "Weight (lbs.)", "L", "W", "H", "Class",
        "Accessory 1", "Accessory 2", "Accessory 3",
        "Tech", "Tech Prose", "SEO Prose",
    ]


def md_to_plain_text(md: str, max_chars: int | None = None) -> str:
    """Very simple Markdown → plain text (keeps content readable for spreadsheet)."""
    text = md
    # strip code fences
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # strip images/links but keep link text
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    # strip headings/bold/italic markers
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("__", "").replace("*", "")
    # collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    if max_chars and len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def first_paragraph(md: str, max_chars: int = 900) -> str:
    """Grab the first non-empty paragraph from Markdown and truncate."""
    parts = [p.strip() for p in md.split("\n\n")]
    for p in parts:
        if p:
            return md_to_plain_text(p, max_chars=max_chars)
    return ""


def pick_primary_category(categories: List[str]) -> tuple[str, str]:
    """Return (primary, rest_joined) from list of category names."""
    if not categories:
        return "", ""
    primary = categories[0]
    rest = " / ".join(categories[1:]) if len(categories) > 1 else ""
    return primary, rest


def three_accessories(meta: Dict[str, Any]) -> List[str]:
    """Pick up to three accessory-ish relations (related/cross-sells/upsells names)."""
    names: List[str] = []
    for key in ("related", "cross_sells", "upsells"):
        arr = meta.get(key) or []
        for item in arr:
            name = (item or {}).get("name") or ""
            if name and name not in names:
                names.append(name)
            if len(names) >= 3:
                break
        if len(names) >= 3:
            break
    while len(names) < 3:
        names.append("")
    return names[:3]


def safe_get(d: Dict[str, Any], *keys, default: Any = "") -> Any:
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


# ---------- mapping ----------

def product_to_row(columns: List[str], fm: Dict[str, Any], body_md: str) -> Dict[str, Any]:
    """
    Map one product file (fm + body) to a dict keyed by target columns.
    We fill only what we know; unknown columns left blank.
    """
    row = {c: "" for c in columns}

    title = fm.get("title") or ""
    sku = fm.get("sku") or ""
    price = fm.get("price") or ""
    url = fm.get("product_url") or ""
    weight = fm.get("weight") or ""
    dims = fm.get("dimensions") or {}
    L = safe_get(dims, "length", default="")
    W = safe_get(dims, "width", default="")
    H = safe_get(dims, "height", default="")
    ship_cl = fm.get("shipping_class") or {}
    ship_class_name = safe_get(ship_cl, "name", default="") or safe_get(ship_cl, "slug", default="")
    # categories list may be strings already; normalize
    cats = fm.get("categories") or []
    cats = [str(c) for c in cats if c]
    section, section_detail = pick_primary_category(cats)

    # description: title + first paragraph
    desc = first_paragraph(body_md, max_chars=2000)
    if title and (not desc or title not in desc[:200]):
        desc = f"{title}\n\n{desc}".strip()

    # accessories
    a1, a2, a3 = three_accessories(fm)

    # try to put an image URL into "Highlights Images" (first image)
    images = fm.get("images") or []
    first_img = ""
    if images and isinstance(images, list):
        first_img = (images[0] or {}).get("src") or ""

    # now fill row only for columns that exist in the schema
    def set_if(col: str, val: Any):
        if col in row:
            row[col] = val

    set_if("Model#", sku)
    set_if("Webpage", url)
    set_if("Description", desc)
    set_if("Price", price)
    set_if("Weight (lbs.)", weight)
    set_if("L", L)
    set_if("W", W)
    set_if("H", H)
    set_if("Class", ship_class_name)
    set_if("Section", section)
    set_if("Section Detail", section_detail)
    set_if("Accessory 1", a1)
    set_if("Accessory 2", a2)
    set_if("Accessory 3", a3)
    set_if("Tech", ", ".join(fm.get("tags") or []))
    # A couple of “nice to haves” if columns exist:
    set_if("Highlights Images", first_img)
    set_if("SEO Prose", "")              # leave blank for humans, unless you want a summary
    set_if("Tech Prose", "")             # leave blank or generate from specs if desired
    set_if("Freight/Ground", "")         # leave blank unless you have a rule to derive this
    set_if("Comments", "")
    set_if("Suggestions", "")
    # Some sheets include '#', '#.1', etc.—we leave them blank.

    return row


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--products-dir", default="pages_clean/products", help="Folder with product .md files")
    ap.add_argument("--schema", default="", help="Path to reference workbook (reads 'Products' header)")
    ap.add_argument("--out", default="vericor_products_audit.xlsx", help="Output workbook")
    args = ap.parse_args()

    products_dir = Path(args.products_dir)
    if not products_dir.exists():
        print(f"🛑 Missing folder: {products_dir.resolve()}")
        sys.exit(1)

    schema_path = Path(args.schema) if args.schema else None
    columns = load_schema_columns(schema_path)

    rows: List[Dict[str, Any]] = []

    files = sorted(products_dir.glob("*.md"))
    if not files:
        print(f"🛑 No .md files found in {products_dir}")
        sys.exit(1)

    for md_path in files:
        try:
            post = frontmatter.load(md_path)
            fm = post.metadata or {}
            body = post.content or ""
            row = product_to_row(columns, fm, body)
            rows.append(row)
        except Exception as e:
            print(f"⚠ Failed to read {md_path.name}: {e}")

    df = pd.DataFrame(rows, columns=columns)

    out_path = Path(args.out)
    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="Products")

    print(f"✓ Wrote {len(df)} products → {out_path.resolve()}")
    print("  Columns:", ", ".join(columns))


if __name__ == "__main__":
    main()
