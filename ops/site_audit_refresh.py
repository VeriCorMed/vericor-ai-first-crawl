# site_audit_refresh.py
"""
Full-site refresh pipeline for Vericor crawl → clean → split → video → normalize → export products.

USAGE (Windows, from project folder):
  venv\Scripts\activate
  python site_audit_refresh.py --mode=rebuild
or
  python site_audit_refresh.py --mode=incremental

Requirements:
- All the helper scripts you already have in this repo:
  deep_crawl_vcm.py
  preprocess_clean.py
  sitemap_split_pages_posts.py
  inject_page_videos.py
  add_inline_videos.py
  normalize_pages_format.py       (optional; formatting polish for pages/posts)
  export_products.py
  normalize_product_frontmatter.py
  clean_vc_shortcodes.py          (for products only; pages handled by video step first)

Environment (already set for products):
  set WC_CK=ck_...
  set WC_CS=cs_...
  set WC_SITE=https://www.vericormed.com
"""

import argparse
import subprocess
import sys
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).parent.resolve()
CLEAN_DIR = PROJECT_ROOT / "clean"
PAGES_CLEAN = PROJECT_ROOT / "pages_clean"
PAGES_DIR = PAGES_CLEAN / "pages"
POSTS_DIR = PAGES_CLEAN / "posts"
PRODUCTS_DIR = PAGES_CLEAN / "products"

def run(cmd, cwd=PROJECT_ROOT):
    print(f"\n$ {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd)
    if res.returncode != 0:
        print(f"🛑 Step failed: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(res.returncode)

def ensure_dirs():
    PAGES_CLEAN.mkdir(exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)

def full_rebuild():
    ensure_dirs()

    # 1) Deep crawl (no cache) → output/
    run([sys.executable, "deep_crawl_vcm.py"])

    # 2) Clean → clean/
    run([sys.executable, "preprocess_clean.py"])

    # 3) Split into pages/posts → pages_clean/pages & pages_clean/posts
    run([sys.executable, "sitemap_split_pages_posts.py"])

    # 4) Videos (PAGES FIRST!) — use fresh .bak from cleaned pages to locate shortcodes
    #    4a) Inject (collect video URLs into the files)
    run([sys.executable, "inject_page_videos.py", str(PAGES_DIR)])
    run([sys.executable, "inject_page_videos.py", str(POSTS_DIR)])
    #    4b) Inline videos using ORIGINAL positions from .md.bak
    #        (this script reads .bak to find [vc_video] markers)
    run([sys.executable, "add_inline_videos.py", str(PAGES_DIR)])
    run([sys.executable, "add_inline_videos.py", str(POSTS_DIR)])

    # 5) Optional: page/post formatting polish (headings, lists, spacing)
    if (PROJECT_ROOT / "normalize_pages_format.py").exists():
        run([sys.executable, "normalize_pages_format.py"])

    # 6) Products export (front-matter enriched, images listed, etc.)
    run([sys.executable, "export_products.py"])

    # 7) Normalize product front-matter (units, consistency)
    run([sys.executable, "normalize_product_frontmatter.py"])

    # 8) Clean product VC shortcodes and keep inline images (we already built this behavior)
    #    For products, it’s safe to clean now; we don’t need video shortcode positions.
    run([sys.executable, "clean_vc_shortcodes.py", "--inline-images"])

    print("\n✓ Full rebuild complete.")

def incremental():
    """
    Lightweight update when only some site pages/products changed.
    - Skips re-crawl if you just want to reformat → but typically you’ll re-crawl.
    - Keeps the same ordering rules.
    Strategy here: run the pipeline steps but let each script decide what’s changed.
    """
    ensure_dirs()

    # You can uncomment this to re-crawl on each incremental run:
    # run([sys.executable, "deep_crawl_vcm.py"])

    run([sys.executable, "preprocess_clean.py"])
    run([sys.executable, "sitemap_split_pages_posts.py"])

    # Videos
    run([sys.executable, "inject_page_videos.py", str(PAGES_DIR)])
    run([sys.executable, "inject_page_videos.py", str(POSTS_DIR)])
    run([sys.executable, "add_inline_videos.py", str(PAGES_DIR)])
    run([sys.executable, "add_inline_videos.py", str(POSTS_DIR)])

    # Optional page/post polish
    if (PROJECT_ROOT / "normalize_pages_format.py").exists():
        run([sys.executable, "normalize_pages_format.py"])

    # Products
    run([sys.executable, "export_products.py"])
    run([sys.executable, "normalize_product_frontmatter.py"])
    run([sys.executable, "clean_vc_shortcodes.py", "--inline-images"])

    print("\n✓ Incremental refresh complete.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["rebuild", "incremental"], default="rebuild")
    args = ap.parse_args()

    t0 = time.time()
    if args.mode == "rebuild":
        full_rebuild()
    else:
        incremental()
    print(f"⏱ Done in {int(time.time()-t0)}s")

if __name__ == "__main__":
    main()
