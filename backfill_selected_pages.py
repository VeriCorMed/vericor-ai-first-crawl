# backfill_selected_pages.py
# Force-crawl a fixed list of URLs, CLEAN the markdown (same style as preprocess),
# and save into clean/. Run sitemap_split_pages_posts.py after this.

import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

# --------- Config ---------
CLEAN_DIR = Path("clean")

INCLUDE_URLS = [
    "https://www.vericormed.com/cool-cube-literature/",
    "https://www.vericormed.com/immunize-stratford/",
    "https://www.vericormed.com/nhsc/",
    "https://www.vericormed.com/po/",
    "https://www.vericormed.com/s-o-for-frequent-use/",
    "https://www.vericormed.com/s-o-for-organization/",
    "https://www.vericormed.com/s-o-for-warehouse/",
    "https://www.vericormed.com/terms-conditions/",
]

# Explicitly NOT including these:
EXCLUDE_SUBSTRINGS = ("rfq-checkout", "/shop/")

# Handle all base variants when making a filename
BASES = [
    "https://www.vericormed.com",
    "http://www.vericormed.com",
    "https://vericormed.com",
    "http://vericormed.com",
]
# --------------------------


def safe_slug_from_url(url: str) -> str:
    """Create a Windows-safe filename from a URL."""
    for b in BASES:
        if url.startswith(b):
            slug = url[len(b):]
            break
    else:
        slug = urlparse(url).path

    slug = slug.strip("/") or "home"
    slug = re.sub(r'[<>:"/\\|?*]', "_", slug)
    slug = re.sub(r"_+", "_", slug)
    return slug[:150]


def clean_markdown(text: str) -> str:
    """Apply the same cleaning you used in preprocess_clean.py (nav/footer/newsletter)."""

    # 1) Kill the top phone/banner line if present
    text = re.sub(r'^Call 608-526-6901.*?\n', '', text, flags=re.IGNORECASE | re.MULTILINE)

    # 2) Strip the site-wide nav block (pattern that worked for your site)
    text = re.sub(
        r'\[Skip to navigation.*?\]\(/?#site-navigation\).*?\n(?:.*\n)*?Menu \[Skip Navigation.*?\n',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    # 3) Optional: drop any remaining “Search for:” prompts
    text = re.sub(r'^\s*Search for:.*?\n', '', text, flags=re.MULTILINE | re.IGNORECASE)

    # 4) Remove the newsletter block and anything that follows
    text = re.sub(
        r'###\s*SIGN ME UP!.*',
        '',
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # 5) Remove the Constant Contact consent boilerplate if left behind
    text = re.sub(
        r'By submitting this form,.*?Constant Contact\)\s*',
        '',
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # 6) Remove footer phone icon image if present
    text = re.sub(
        r'!\[ico-phone-footer\]\(https?://[^\)]+/ico-phone-footer[^\)]*\)\s*',
        '',
        text,
        flags=re.IGNORECASE
    )

    # 7) Collapse extra blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip() + "\n"


async def fetch_and_save(urls: list[str]) -> tuple[int, int, int]:
    """Crawl each URL, clean markdown, and save into clean/."""
    browser_cfg = BrowserConfig(headless=True, java_script_enabled=True, verbose=True)
    strategy = AsyncPlaywrightCrawlerStrategy(browser_config=browser_cfg)
    crawl_cfg = CrawlerRunConfig(
        scraping_strategy=LXMLWebScrapingStrategy(),
        cache_mode=CacheMode.BYPASS,
        verbose=True,
        stream=False,
        delay_before_return_html=0.5,
    )

    CLEAN_DIR.mkdir(exist_ok=True)

    saved = failed = skipped = 0
    async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
        for u in urls:
            if any(s in u for s in EXCLUDE_SUBSTRINGS):
                print(f"SKIP  {u}")
                skipped += 1
                continue

            try:
                res_list = await crawler.arun(u, config=crawl_cfg)
                res = res_list[0] if res_list else None

                if not res or not res.success:
                    print(f"FAIL  {u}")
                    failed += 1
                    continue

                raw_md = res.markdown.raw_markdown
                cleaned = clean_markdown(raw_md)

                slug = safe_slug_from_url(u)
                out_path = CLEAN_DIR / f"{slug}.md"
                out_path.write_text(cleaned, encoding="utf-8")
                print(f"OK    {u}  → {out_path.name}")
                saved += 1
            except Exception as e:
                print(f"ERR   {u} → {e}")
                failed += 1

    return saved, failed, skipped


def main():
    # Modern asyncio run for Python 3.13+
    saved, failed, skipped = asyncio.run(fetch_and_save(INCLUDE_URLS))
    print(f"\n✓ Wrote {saved} files   ✗ Failed {failed}   ⏭ Skipped {skipped}")


if __name__ == "__main__":
    main()
