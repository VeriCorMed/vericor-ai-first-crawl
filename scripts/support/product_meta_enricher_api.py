# product_meta_enricher_api.py
# Fetch WooCommerce products and write AI-ready Markdown with rich metadata.
# Output: pages_clean/products/*.md

from __future__ import annotations
import os
import sys
import time
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple

try:
    # Official helper lib (pip install woocommerce)
    from woocommerce import API as WCAPI
except ImportError:
    print("🛑 Missing dependency: pip install woocommerce")
    sys.exit(1)

# Optional HTML → Markdown if available
try:
    from markdownify import markdownify as html2md  # pip install markdownify
except Exception:
    html2md = None

# ---------- Config via environment variables ----------
WC_SITE = os.getenv("WC_SITE", "https://www.vericormed.com").rstrip("/")
WC_CK = os.getenv("WC_CK")
WC_CS = os.getenv("WC_CS")

OUT_DIR = Path("pages_clean") / "products"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PER_PAGE = 100  # WC REST API max per page
REQUEST_DELAY = 0.2  # be gentle

def die(msg: str) -> None:
    print(f"🛑 {msg}")
    sys.exit(1)

if not WC_CK or not WC_CS:
    die("Environment variables WC_CK and WC_CS are required. Example:\n"
        "  set WC_SITE=https://www.vericormed.com\n"
        "  set WC_CK=ck_xxx\n"
        "  set WC_CS=cs_xxx")

# ---------- Helpers ----------
def safe_slug(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^\w\-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:150] or "product"

def to_markdown(html: str | None) -> str:
    if not html:
        return ""
    if html2md:
        return html2md(html, heading_style="ATX").strip()
    # Fallback: crude tag strip
    text = re.sub(r"<\s*br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def kv_meta_list(meta_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Flatten Woo meta_data (list of {key, value}) into a dict, JSON-serializing objects."""
    out = {}
    for m in meta_data or []:
        key = str(m.get("key") or "").strip()
        val = m.get("value")
        if not key:
            continue
        if isinstance(val, (dict, list)):
            try:
                out[key] = json.dumps(val, ensure_ascii=False)
            except Exception:
                out[key] = str(val)
        else:
            out[key] = val
    return out

def yaml_escape(s: str) -> str:
    # Minimal YAML-safe string
    if s is None:
        return ""
    s = str(s)
    if any(c in s for c in [":", "-", "{", "}", "[", "]", "#", ",", "&", "*", "!", "|", ">", "@", "%", "\n", "\r", '"', "'"]):
        return '"' + s.replace('"', '\\"') + '"'
    return s

def write_product_md(prod: Dict[str, Any], idmap: Dict[int, Dict[str, str]]) -> None:
    slug = prod.get("slug") or safe_slug(prod.get("name", "product"))
    filename = f"{slug}.md"
    path = OUT_DIR / filename

    # Core fields
    permalink = prod.get("permalink")
    name = prod.get("name")
    sku = prod.get("sku") or ""
    ptype = prod.get("type")
    status = prod.get("status")
    stock_status = prod.get("stock_status")
    manage_stock = prod.get("manage_stock")
    stock_qty = prod.get("stock_quantity")
    regular_price = prod.get("regular_price")
    sale_price = prod.get("sale_price")
    price = prod.get("price")
    total_sales = prod.get("total_sales")

    weight = prod.get("weight")
    dims = (prod.get("dimensions") or {})
    dim_l = dims.get("length")
    dim_w = dims.get("width")
    dim_h = dims.get("height")

    shipping_class = prod.get("shipping_class") or ""
    shipping_class_id = prod.get("shipping_class_id")

    cats = [c.get("name") for c in (prod.get("categories") or []) if c.get("name")]
    tags = [t.get("name") for t in (prod.get("tags") or []) if t.get("name")]
    images = [i.get("src") for i in (prod.get("images") or []) if i.get("src")]

    # Attributes (name + options)
    attributes = []
    for a in prod.get("attributes") or []:
        attributes.append({
            "name": a.get("name"),
            "visible": a.get("visible"),
            "variation": a.get("variation"),
            "options": a.get("options") or [],
        })

    # Linked products
    def resolve_ids(id_list: List[int]) -> List[Dict[str, str]]:
        out = []
        for pid in id_list or []:
            meta = idmap.get(pid)
            if meta:
                out.append({"id": pid, **meta})
        return out

    related = resolve_ids(prod.get("related_ids") or [])
    upsells = resolve_ids(prod.get("upsell_ids") or [])
    cross_sells = resolve_ids(prod.get("cross_sell_ids") or [])

    meta_flat = kv_meta_list(prod.get("meta_data") or [])

    short_md = to_markdown(prod.get("short_description"))
    long_md = to_markdown(prod.get("description"))

    # ---------- YAML front matter ----------
    fm_lines = [
        "---",
        f'title: {yaml_escape(name)}',
        f'url: {yaml_escape(permalink)}',
        f'type: product',
        f'slug: {yaml_escape(slug)}',
        f'status: {yaml_escape(status)}',
        f'product_type: {yaml_escape(ptype)}',
        f'sku: {yaml_escape(sku)}',
        f'price: {yaml_escape(price)}',
        f'regular_price: {yaml_escape(regular_price)}',
        f'sale_price: {yaml_escape(sale_price)}',
        f'stock_status: {yaml_escape(stock_status)}',
        f'manage_stock: {yaml_escape(manage_stock)}',
        f'stock_quantity: {yaml_escape(stock_qty)}',
        f'total_sales: {yaml_escape(total_sales)}',
        f'weight: {yaml_escape(weight)}',
        "dimensions:",
        f'  length: {yaml_escape(dim_l)}',
        f'  width: {yaml_escape(dim_w)}',
        f'  height: {yaml_escape(dim_h)}',
        f'shipping_class: {yaml_escape(shipping_class)}',
        f'shipping_class_id: {yaml_escape(shipping_class_id)}',
        "categories: [" + ", ".join(yaml_escape(c) for c in cats) + "]",
        "tags: [" + ", ".join(yaml_escape(t) for t in tags) + "]",
        "images: [" + ", ".join(yaml_escape(u) for u in images) + "]",
        "attributes:",
    ]
    for a in attributes:
        fm_lines.append("  - name: " + yaml_escape(a["name"]))
        fm_lines.append("    visible: " + yaml_escape(a["visible"]))
        fm_lines.append("    variation: " + yaml_escape(a["variation"]))
        fm_lines.append("    options: [" + ", ".join(yaml_escape(o) for o in (a["options"] or [])) + "]")

    def list_of_links(label: str, items: List[Dict[str, str]]) -> None:
        fm_lines.append(f"{label}:")
        for it in items:
            fm_lines.append(f"  - id: {it['id']}")
            fm_lines.append(f"    name: {yaml_escape(it['name'])}")
            fm_lines.append(f"    slug: {yaml_escape(it['slug'])}")
            fm_lines.append(f"    url: {yaml_escape(it['url'])}")

    list_of_links("related_products", related)
    list_of_links("upsell_products", upsells)
    list_of_links("cross_sell_products", cross_sells)

    # Custom meta (flattened)
    fm_lines.append("meta_data:")
    for k, v in meta_flat.items():
        fm_lines.append(f"  {yaml_escape(k)}: {yaml_escape(v)}")

    fm_lines.append("---")
    fm = "\n".join(fm_lines)

    body_parts = []
    if short_md:
        body_parts.append("## Overview\n\n" + short_md)
    if long_md:
        body_parts.append("## Description\n\n" + long_md)

    content = fm + "\n\n" + ("\n\n".join(body_parts) if body_parts else "")

    path.write_text(content, encoding="utf-8")

def fetch_all_products(wc: WCAPI) -> List[Dict[str, Any]]:
    all_items: List[Dict[str, Any]] = []
    page = 1
    while True:
        resp = wc.get("products", params={
            "page": page,
            "per_page": PER_PAGE,
            "status": "publish"  # only public catalog
        })
        if resp.status_code != 200:
            die(f"Woo API error on page {page}: {resp.status_code} {resp.text[:200]}")
        batch = resp.json()
        if not batch:
            break
        all_items.extend(batch)
        page += 1
        time.sleep(REQUEST_DELAY)
    return all_items

def build_id_map(products: List[Dict[str, Any]]) -> Dict[int, Dict[str, str]]:
    idmap: Dict[int, Dict[str, str]] = {}
    for p in products:
        pid = int(p.get("id"))
        idmap[pid] = {
            "name": p.get("name") or "",
            "slug": p.get("slug") or safe_slug(p.get("name") or ""),
            "url": p.get("permalink") or "",
        }
    return idmap

def main() -> None:
    wc = WCAPI(
        url=WC_SITE,
        consumer_key=WC_CK,
        consumer_secret=WC_CS,
        version="wc/v3",
        timeout=30
    )

    print(f"Connecting to {WC_SITE} …")
    products = fetch_all_products(wc)
    if not products:
        print("✓ Enriched 0 product files via WooCommerce REST API  (no products found)")
        return

    idmap = build_id_map(products)

    written = 0
    for prod in products:
        try:
            write_product_md(prod, idmap)
            written += 1
        except Exception as e:
            # Keep going; report at end
            print(f"⚠ Failed to write product {prod.get('id')} {prod.get('name')}: {e}")

    print(f"✓ Wrote {written} product files → {OUT_DIR}")

if __name__ == "__main__":
    main()
