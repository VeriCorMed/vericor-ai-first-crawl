# export_products.py
# Export WooCommerce products to Markdown (AI-first format) with product_url, images, and variations.
# Requires env vars: WC_SITE, WC_CK, WC_CS
#   set WC_SITE=https://www.vericormed.com
#   set WC_CK=ck_5b1d4b82af1c1a492101397cc680b77ee86cf892
#   set WC_CS=cs_06149e7da3d0dfec43fb9fb214c3b462c57496ce

from __future__ import annotations
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from urllib.parse import urljoin

import requests
from markdownify import markdownify as md


# ---------- Config / Env ----------
SITE = os.environ.get("WC_SITE", "").rstrip("/")
CK = os.environ.get("WC_CK", "")
CS = os.environ.get("WC_CS", "")
TIMEOUT = float(os.environ.get("WC_TIMEOUT", "30"))
OUT_DIR = Path("pages_clean") / "products"
OUT_DIR.mkdir(parents=True, exist_ok=True)

if not (SITE and CK and CS):
    print("🛑 Missing WC_SITE / WC_CK / WC_CS environment variables.")
    print("   Example:")
    print("     set WC_SITE=https://www.vericormed.com")
    print("     set WC_CK=ck_XXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    print("     set WC_CS=cs_XXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    sys.exit(1)

API_BASE = f"{SITE}/wp-json/wc/v3"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


# ---------- HTTP helpers ----------
def _req(method: str, url: str, params: Dict[str, Any] | None = None) -> requests.Response:
    # Woo allows ck/cs in query on HTTPS
    p = dict(params or {})
    p["consumer_key"] = CK
    p["consumer_secret"] = CS
    resp = requests.request(method, url, params=p, headers=HEADERS, timeout=TIMEOUT)
    return resp

def wc_get(path: str, params: Dict[str, Any] | None = None) -> Any:
    r = _req("GET", f"{API_BASE}{path}", params=params or {})
    if r.status_code == 404:
        # Some stores disable certain endpoints (e.g., /shipping_classes)
        raise FileNotFoundError(f"404 for {path} → {r.text[:300]}")
    if not r.ok:
        detail = {}
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        raise RuntimeError(f"HTTP {r.status_code} for {API_BASE}{path}\n{detail}")
    try:
        return r.json()
    except Exception:
        return r.text


# ---------- Utilities ----------
def chunked(seq: List[Any], n: int) -> List[List[Any]]:
    return [seq[i : i + n] for i in range(0, len(seq), n)]

def safe_slug(s: str) -> str:
    import re
    slug = s.strip().lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9\-._]", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:150]

def md_front_matter(data: Dict[str, Any]) -> str:
    import yaml
    return "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True) + "---\n\n"


# ---------- Lookups (optional/when available) ----------
def try_get_shipping_classes_map() -> Dict[int, Dict[str, str]]:
    """Return {id: {'name': ..., 'slug': ...}}. If endpoint is unavailable, return {} and warn."""
    try:
        classes = wc_get("/shipping_classes")
    except FileNotFoundError:
        print("ℹ shipping_classes endpoint not available; continuing without it.")
        return {}
    out: Dict[int, Dict[str, str]] = {}
    for c in classes:
        cid = c.get("id")
        if isinstance(cid, int):
            out[cid] = {"name": c.get("name") or "", "slug": c.get("slug") or ""}
    return out

def get_product_names_by_ids(ids: List[int]) -> Dict[int, Dict[str, str]]:
    """Resolve a list of product IDs to {id: {'name':..., 'slug':..., 'permalink': ...}} in batches."""
    result: Dict[int, Dict[str, str]] = {}
    ids = [i for i in ids if isinstance(i, int)]
    if not ids:
        return result
    for batch in chunked(ids, 100):
        params = {"include": ",".join(str(i) for i in batch), "per_page": len(batch)}
        items = wc_get("/products", params=params)
        for p in items:
            pid = p.get("id")
            if isinstance(pid, int):
                result[pid] = {
                    "name": p.get("name") or "",
                    "slug": p.get("slug") or "",
                    "permalink": p.get("permalink") or "",
                }
    return result


# ---------- Variations ----------
def get_variations_for_product(prod_id: int) -> List[Dict[str, Any]]:
    """Fetch all variations for a variable product."""
    variations: List[Dict[str, Any]] = []
    page = 1
    while True:
        params = {"per_page": 100, "page": page, "orderby": "id", "order": "asc"}
        try:
            items = wc_get(f"/products/{prod_id}/variations", params=params)
        except FileNotFoundError:
            # Variations endpoint missing/disabled
            break
        if not items:
            break
        for v in items:
            # normalize just what we need for front-matter
            variations.append({
                "id": v.get("id"),
                "sku": v.get("sku") or "",
                "price": v.get("price") or "",
                "regular_price": v.get("regular_price") or "",
                "sale_price": v.get("sale_price") or "",
                "stock_status": v.get("stock_status") or "",
                "stock_quantity": v.get("stock_quantity"),
                "weight": v.get("weight") or "",
                "dimensions": v.get("dimensions") or {},
                "attributes": [
                    {
                        "name": a.get("name") or "",
                        "option": a.get("option") or ""
                    } for a in (v.get("attributes") or [])
                ],
            })
        page += 1
    return variations


# ---------- Export ----------
def gather_all_products(status: str = "publish") -> Tuple[List[Dict[str, Any]], int]:
    """Return (all_products_list, total_pages)."""
    params = {"per_page": 100, "page": 1, "status": status, "orderby": "id", "order": "asc"}
    first = wc_get("/products", params=params)
    total_pages = int(first and isinstance(first, list) and hasattr(first, "__len__") and
                      _req("GET", f"{API_BASE}/products", params=params).headers.get("X-WP-TotalPages", "1") or 1)
    all_items = list(first or [])
    for page in range(2, total_pages + 1):
        params["page"] = page
        items = wc_get("/products", params=params)
        all_items.extend(items or [])
    return all_items, total_pages

def export_product(p: Dict[str, Any],
                   ship_map: Dict[int, Dict[str, str]],
                   names_cache: Dict[int, Dict[str, str]]) -> Optional[Path]:
    """Export a single product dict to Markdown with rich front-matter."""
    prod_id = p.get("id")
    slug = p.get("slug") or (p.get("sku") and safe_slug(p["sku"])) or f"product-{prod_id}"
    title = p.get("name") or slug
    permalink = p.get("permalink") or ""
    sku = p.get("sku") or ""
    ptype = p.get("type") or ""
    status = p.get("status") or ""
    price = p.get("price") or ""
    regular_price = p.get("regular_price") or ""
    sale_price = p.get("sale_price") or ""
    stock_status = p.get("stock_status") or ""
    stock_qty = p.get("stock_quantity")
    weight = p.get("weight") or ""
    dimensions = p.get("dimensions") or {}
    shipping_class_id = p.get("shipping_class_id")
    shipping_class = {}
    if isinstance(shipping_class_id, int) and shipping_class_id in ship_map:
        shipping_class = ship_map[shipping_class_id]

    # categories/tags
    categories = [c.get("name") for c in (p.get("categories") or []) if c.get("name")]
    tags = [t.get("name") for t in (p.get("tags") or []) if t.get("name")]

    # linked products
    related_ids = p.get("related_ids") or []
    upsell_ids = p.get("upsell_ids") or []
    cross_sell_ids = p.get("cross_sell_ids") or []
    all_linked = set(related_ids + upsell_ids + cross_sell_ids)
    if all_linked:
        names = get_product_names_by_ids(list(all_linked))
        names_cache.update(names)

    def _resolve_list(ids: List[int]) -> List[Dict[str, str]]:
        out = []
        for i in ids:
            meta = names_cache.get(i)
            if meta:
                out.append({"id": i, "name": meta.get("name", ""), "slug": meta.get("slug", ""), "url": meta.get("permalink", "")})
            else:
                out.append({"id": i})
        return out

    related = _resolve_list(related_ids)
    upsells = _resolve_list(upsell_ids)
    cross_sells = _resolve_list(cross_sell_ids)

    # IMAGES
    images_block: List[Dict[str, Any]] = []
    for im in (p.get("images") or []):
        images_block.append({
            "src": im.get("src") or "",
            "alt": im.get("alt") or "",
            "name": im.get("name") or "",
            "position": im.get("position"),
        })

    # VARIATIONS (for variable products)
    variations_block: List[Dict[str, Any]] = []
    if ptype == "variable":
        variations_block = get_variations_for_product(prod_id)

    # Descriptions → Markdown
    short_md = md(p.get("short_description") or "", strip=["script", "style"]).strip()
    long_md = md(p.get("description") or "", strip=["script", "style"]).strip()

    # Front-matter
    fm: Dict[str, Any] = {
        "id": prod_id,
        "slug": slug,
        "title": title,
        "status": status,
        "type": ptype,
        "sku": sku,
        "price": str(price) if price is not None else "",
        "regular_price": str(regular_price) if regular_price is not None else "",
        "sale_price": str(sale_price) if sale_price is not None else "",
        "stock_status": stock_status,
        "stock_quantity": stock_qty,
        "weight": weight,
        "dimensions": dimensions,  # {length,width,height}
        "shipping_class": shipping_class,  # {'name','slug'} if available
        "categories": categories,
        "tags": tags,
        "related": related,
        "upsells": upsells,
        "cross_sells": cross_sells,
        "product_url": permalink,          # <— trace back to live page
        "images": images_block,            # <— images list
    }

    if variations_block:
        fm["variations"] = variations_block  # <— variations for variable products

    # Build Markdown body
    body_parts = []
    body_parts.append(f"# {title}\n")
    if short_md:
        body_parts.append(f"**Summary:** {short_md}\n")
    if long_md:
        body_parts.append(long_md + "\n")

    content = md_front_matter(fm) + "\n".join(body_parts).strip() + "\n"

    # Write file
    out_path = OUT_DIR / f"{slug}.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def main() -> None:
    # Gather shipping classes (if exposed)
    ship_map = try_get_shipping_classes_map()

    # Gather products
    # First request just to show a friendly count/pages
    params = {"per_page": 100, "page": 1, "status": "publish", "orderby": "id", "order": "asc"}
    first_resp = _req("GET", f"{API_BASE}/products", params=params)
    total_pages = int(first_resp.headers.get("X-WP-TotalPages", "1"))
    total_items = int(first_resp.headers.get("X-WP-Total", "0"))
    try:
        first_items = first_resp.json()
    except Exception:
        first_items = []
    print(f"Found ~{total_items} published products across {total_pages} page(s).")
    if ship_map == {}:
        # already printed inside try_get_shipping_classes_map
        pass

    names_cache: Dict[int, Dict[str, str]] = {}
    written = 0

    # Page 1
    page_items = first_items
    if page_items:
        print(f"Page 1/{total_pages}: {len(page_items)} products")
        for p in page_items:
            if not isinstance(p, dict):
                continue
            if export_product(p, ship_map, names_cache):
                written += 1

    # Remaining pages
    for page in range(2, total_pages + 1):
        params["page"] = page
        r = _req("GET", f"{API_BASE}/products", params=params)
        items = []
        try:
            items = r.json()
        except Exception:
            items = []
        print(f"Page {page}/{total_pages}: {len(items)} products")
        for p in items:
            if not isinstance(p, dict):
                continue
            if export_product(p, ship_map, names_cache):
                written += 1
        # be nice to the API
        time.sleep(0.2)

    print(f"✓ Wrote {written} product Markdown file(s) → {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
