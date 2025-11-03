# sitemap_split_pages_posts.py
# Split cleaned Markdown into pages vs posts using the site's sitemap index.
# Input:  clean/*.md  (files named by the crawl slug algorithm)
# Output: pages_clean/pages/*.md  and  pages_clean/posts/*.md

from pathlib import Path
import re
import sys
import shutil
from urllib.parse import urlparse

import requests
from lxml import etree

# Slugs we expect *not* to have Markdown (exclude from warnings)
IGNORE_SLUGS = {
    "shop",
    "rfq-checkout",
    "thank-you-for-your-online-quote-request",
    "vericor-profile-page",
}

BASES = [
    "https://www.vericormed.com",
    "http://www.vericormed.com",
    "https://vericormed.com",
    "http://vericormed.com",
]

SITEMAP_INDEX_URL = "https://www.vericormed.com/sitemap_index.xml"
CLEAN_DIR = Path("clean")
OUT_ROOT = Path("pages_clean")
PAGES_DIR = OUT_ROOT / "pages"
POSTS_DIR = OUT_ROOT / "posts"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.vericormed.com/",
}

def safe_slug_from_url(url: str) -> str:
    """Reproduce the slug used when saving .md files during crawl."""
    for b in BASES:
        if url.startswith(b):
            slug = url[len(b):]
            break
    else:
        slug = urlparse(url).path

    slug = slug.strip("/") or "home"
    # Replace characters Windows won't accept in filenames (and slash)
    slug = re.sub(r'[<>:"/\\|?*]', "_", slug)
    # Collapse repeats and trim length
    slug = re.sub(r"_+", "_", slug)
    return slug[:150]

def fetch_xml(url: str) -> etree._Element:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return etree.fromstring(r.content)

def collect_urls_from_urlset(urlset_url: str) -> list[str]:
    root = fetch_xml(urlset_url)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [
        loc.text.strip()
        for loc in root.findall(".//sm:url/sm:loc", ns)
        if loc is not None and loc.text
    ]

def get_pages_and_posts() -> tuple[set[str], set[str]]:
    """Return (pages_urls, posts_urls) using the sitemap index."""
    root = fetch_xml(SITEMAP_INDEX_URL)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_locs = [
        loc.text.strip()
        for loc in root.findall(".//sm:sitemap/sm:loc", ns)
        if loc is not None and loc.text
    ]

    # Filter sitemaps by type
    page_maps = [u for u in sitemap_locs if "/page-sitemap" in u]
    post_maps = [u for u in sitemap_locs if "/post-sitemap" in u]

    # Fallback: if index wasn’t returned, treat it as a single urlset
    if not page_maps and not post_maps and root.tag.endswith("urlset"):
        urls = [
            loc.text.strip()
            for loc in root.findall(".//sm:url/sm:loc", ns)
            if loc is not None and loc.text
        ]
        pages, posts = set(), set()
        for u in urls:
            if re.search(r"/(blog/|category/|tag/|20\d{2}/)", u):
                posts.add(u)
            else:
                pages.add(u)
        return pages, posts

    pages, posts = set(), set()
    for u in page_maps:
        pages.update(collect_urls_from_urlset(u))
    for u in post_maps:
        posts.update(collect_urls_from_urlset(u))
    return pages, posts

def clear_dir(dir_path: Path) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    for p in dir_path.glob("*.md"):
        try:
            p.unlink()
        except Exception:
            pass

def copy_selected(urls: set[str], dest_dir: Path) -> tuple[int, list[tuple[str, str]]]:
    copied = 0
    missing: list[tuple[str, str]] = []
    for u in sorted(urls):
        name = safe_slug_from_url(u) + ".md"
        src = CLEAN_DIR / name
        if src.exists():
            shutil.copy2(src, dest_dir / name)
            copied += 1
        else:
            missing.append((u, name))
    return copied, missing

def main() -> None:
    if not CLEAN_DIR.exists():
        print(f"🛑 Missing input folder: {CLEAN_DIR.resolve()}")
        sys.exit(1)

    try:
        pages_urls, posts_urls = get_pages_and_posts()
    except Exception as e:
        print("🛑 Failed to fetch/parse the sitemap index:", e)
        sys.exit(1)

    clear_dir(PAGES_DIR)
    clear_dir(POSTS_DIR)

    copied_pages, missing_pages = copy_selected(pages_urls, PAGES_DIR)
    copied_posts, missing_posts = copy_selected(posts_urls, POSTS_DIR)

    # Drop sitemap entries we intentionally ignore from the “missing” report
    missing_pages = [(u, name) for (u, name) in missing_pages if name[:-3] not in IGNORE_SLUGS]
    missing_posts = [(u, name) for (u, name) in missing_posts if name[:-3] not in IGNORE_SLUGS]

    print(f"✓ Copied {copied_pages} pages  → {PAGES_DIR}")
    print(f"✓ Copied {copied_posts} posts  → {POSTS_DIR}")

    total_missing = len(missing_pages) + len(missing_posts)
    if total_missing:
        print(f"⚠ {total_missing} sitemap URLs had no matching file in {CLEAN_DIR}. Showing up to 10:")
        for i, (u, name) in enumerate((missing_pages + missing_posts)[:10], 1):
            print(f"  {i}. {name}  ← {u}")

    # Always confirm ignored slugs
    if IGNORE_SLUGS:
        print("\nℹ Intentionally ignored slugs:")
        for slug in sorted(IGNORE_SLUGS):
            print(f"   - {slug}.md")

if __name__ == "__main__":
    main()
