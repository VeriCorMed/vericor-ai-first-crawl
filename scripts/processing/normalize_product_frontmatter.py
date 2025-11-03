# normalize_product_frontmatter.py
"""
Normalize WooCommerce product front-matter for AI First Format.

What it does (per product .md in pages_clean/products/):
- weight: '13'              -> weight: { value: 13, unit: "lbs" }
- dimensions: '12' strings  -> dimensions.length/width/height as numbers + units
- price fields to numbers   -> price/regular_price/sale_price become numbers (if present)
- stock_quantity to int     -> if present and numeric
- adds derived 'volume'     -> { value: L*W*H, unit: "in^3" } when all dims available

It leaves the Markdown body unchanged.

Units:
- Set via environment variables (optional):
  - WC_WEIGHT_UNIT  (default: "lbs")
  - WC_DIM_UNIT     (default: "in")

Safety:
- Writes a .bak next to each file (first time only; won’t overwrite an existing .bak)
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
from typing import Any, Dict, Optional, Tuple

import frontmatter  # pip install python-frontmatter
import yaml         # pip install pyyaml

ROOT = Path(__file__).resolve().parent
PRODUCTS_DIR = ROOT / "pages_clean" / "products"

WEIGHT_UNIT = os.environ.get("WC_WEIGHT_UNIT", "lbs").strip() or "lbs"
DIM_UNIT = os.environ.get("WC_DIM_UNIT", "in").strip() or "in"

def _coerce_number(v: Any) -> Optional[float]:
    """Coerce strings like '13', '13.0' -> number; return None for empty/invalid."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        # Allow things like '13 lbs' (take leading number)
        # and strip commas
        s = s.replace(",", " ")
        token = s.split()[0]
        try:
            return float(token)
        except ValueError:
            return None
    return None

def _num_or_int(n: float) -> int | float:
    """Return int if whole number, else float (for cleaner YAML)."""
    if n is None:
        return n
    i = int(n)
    return i if n == i else n

def normalize_weight(meta: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    changed = False
    weight_raw = meta.get("weight")
    num = _coerce_number(weight_raw)
    if num is not None:
        meta["weight"] = {"value": _num_or_int(num), "unit": WEIGHT_UNIT}
        changed = True
    return changed, meta

def normalize_dimensions(meta: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    changed = False
    dims = meta.get("dimensions")
    if isinstance(dims, dict):
        out: Dict[str, Dict[str, Any]] = {}
        have_all = True
        prod = 1.0
        for key in ("length", "width", "height"):
            num = _coerce_number(dims.get(key))
            if num is not None:
                out[key] = {"value": _num_or_int(num), "unit": DIM_UNIT}
                prod *= float(num)
            else:
                have_all = False
        if out:
            meta["dimensions"] = out
            changed = True
        if have_all:
            meta["volume"] = {"value": _num_or_int(prod), "unit": f"{DIM_UNIT}^3"}
            changed = True
    return changed, meta

def normalize_prices(meta: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    changed = False
    for key in ("price", "regular_price", "sale_price"):
        if key in meta:
            num = _coerce_number(meta.get(key))
            if num is None:
                # Keep empty sale_price as empty string if that’s how it is
                if key == "sale_price" and (meta.get(key) in ("", None)):
                    continue
                # otherwise drop unusable
                meta.pop(key, None)
                changed = True
            else:
                meta[key] = _num_or_int(num)
                changed = True
    return changed, meta

def normalize_stock(meta: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    changed = False
    if "stock_quantity" in meta:
        num = _coerce_number(meta.get("stock_quantity"))
        if num is None:
            meta.pop("stock_quantity", None)
            changed = True
        else:
            meta["stock_quantity"] = int(round(num))
            changed = True
    return changed, meta

def process_file(path: Path) -> bool:
    """Return True if file changed."""
    post = frontmatter.load(path, encoding="utf-8")
    meta = dict(post.metadata)  # copy

    changed = False
    c, meta = normalize_weight(meta)
    changed = changed or c
    c, meta = normalize_dimensions(meta)
    changed = changed or c
    c, meta = normalize_prices(meta)
    changed = changed or c
    c, meta = normalize_stock(meta)
    changed = changed or c

    if not changed:
        return False

    # Make a backup once
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        try:
            shutil.copy2(path, bak)
        except Exception:
            pass

    # Write back with YAML front-matter
    post.metadata = meta
    text = frontmatter.dumps(post)
    path.write_text(text, encoding="utf-8")
    return True

def main() -> None:
    if not PRODUCTS_DIR.exists():
        print(f"🛑 Missing folder: {PRODUCTS_DIR}")
        return

    files = sorted(PRODUCTS_DIR.glob("*.md"))
    if not files:
        print(f"ℹ No product files found in {PRODUCTS_DIR}")
        return

    changed = 0
    for p in files:
        if process_file(p):
            changed += 1

    print(f"✓ Normalized {changed} / {len(files)} product file(s)")
    print(f"Units used → weight: {WEIGHT_UNIT}  dimensions: {DIM_UNIT}")

if __name__ == "__main__":
    main()
