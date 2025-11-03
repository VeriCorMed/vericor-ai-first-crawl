# backfill_selected_posts.py
# Crawl & CLEAN specific blog-post URLs, save into clean/, then run sitemap_split_pages_posts.py

import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

CLEAN_DIR = Path("clean")

POST_URLS = [
    "https://www.vericormed.com/2022-preparedness-summit-recap-cool-cube-transport-cart-triage-treatment/",
    "https://www.vericormed.com/cool-cube-care-and-maintenance-cool-cube-transport-cart-mobile-alternate-care-site-system/",
    "https://www.vericormed.com/cool-cube-transport-cart-96-hour-in-the-field-emergency-room-96-hour-alternate-care-site/",
    "https://www.vericormed.com/flexible-pack-mobile-hics-cart-ep-response-trailers/",
    "https://www.vericormed.com/mastering-mobile-response-engineered-for-extreme-durability-simplify-your-vaccine-clinics/",
    "https://www.vericormed.com/pink-for-breast-cancer-awareness-the-science-of-cool-know-the-temperature/",
    "https://www.vericormed.com/remember-recharge-reconnect-transport-cart-for-the-cool-cube-digital-data-loggers/",
    "https://www.vericormed.com/the-smartbook-forget-the-ice-burn-care-medkit/",
    "https://www.vericormed.com/voices-of-preparedness-the-choice-of-professionals-medical-kits/",
]

BASES = [
    "https://www.vericormed.com",
    "http://www.vericormed.com",
    "https://vericormed.com",
    "http://vericormed.com",
]

def safe_slug_from_url(url: str) -> str:
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
    # same cleaners we use elsewhere
    text = re.sub(r'^Call 608-526-6901.*?\n', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(
        r'\[Skip to navigation.*?\]\(/?#site-navigation\).*?\n(?:.*\n)*?Menu \[Skip Navigation.*?\n',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(r'^\s*Search for:.*?\n', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'###\s*SIGN ME UP!.*', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'By submitting this form,.*?Constant Contact\)\s*', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'!\[ico-phone-footer\]\(https?://[^\)]+/ico-phone-footer[^\)]*\)\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip() + "\n"

async def fetch_and_save(urls: list[str]) -> tuple[int, int]:
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
    saved = failed = 0
    async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
        for u in urls:
            try:
                res_list = await crawler.arun(u, config=crawl_cfg)
                res = res_list[0] if res_list else None
                if not res or not res.success:
                    print(f"FAIL  {u}")
                    failed += 1
                    continue
                cleaned = clean_markdown(res.markdown.raw_markdown)
                out_path = CLEAN_DIR / f"{safe_slug_from_url(u)}.md"
                out_path.write_text(cleaned, encoding="utf-8")
                print(f"OK    {u}  → {out_path.name}")
                saved += 1
            except Exception as e:
                print(f"ERR   {u} → {e}")
                failed += 1
    return saved, failed

def main():
    saved, failed = asyncio.run(fetch_and_save(POST_URLS))
    print(f"\n✓ Wrote {saved} files   ✗ Failed {failed}")

if __name__ == "__main__":
    main()
