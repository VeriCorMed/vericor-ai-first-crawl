# deep_crawl_vcm.py
"""
Deep‑crawl https://www.vericormed.com
• Max 400 pages, depth ≤ 5
• Writes Markdown for each page + links.jsonl
Works with Crawl4AI 0.7.1 + Python 3.13 (stream=False workaround)
"""

import asyncio, json, datetime as dt
import re
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter, URLPatternFilter
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

async def main() -> None:
    # 1 ─ Browser settings
    browser_cfg = BrowserConfig(headless=True, java_script_enabled=True, verbose=True)

    # 2 ─ Filters
    filters = FilterChain([
        DomainFilter(allowed_domains=["vericormed.com"]),
        URLPatternFilter(
            patterns=[
                "*wp-admin*", "*wp-login*", "*feed*", "*cart*", "*checkout*",
                "*?wpfb_dl=*",
                "*.pdf",
            ],
            reverse=True,   # treat as block list
        ),
    ])

    # 3 ─ Crawl config (no‑page cap)
    crawl_cfg = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=10,
            max_pages=10_000,
            include_external=False,
            filter_chain=filters,
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        cache_mode=CacheMode.BYPASS,
        verbose=True,
        stream=False,                 # Py 3.13 streaming bug workaround
        delay_before_return_html=0.5,
    )

    # 4 ─ Output directory
    out_dir = Path("output"); out_dir.mkdir(exist_ok=True)
    links_path = out_dir / "links.jsonl"

    # 5 ─ Create crawler strategy with browser config
    strategy = AsyncPlaywrightCrawlerStrategy(browser_config=browser_cfg)

    # 6 ─ Run crawl
    async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
        results = await crawler.arun("https://www.vericormed.com", config=crawl_cfg)

    # 7 ─ Save results
    with links_path.open("w", encoding="utf-8") as link_file:
        for res in results:
            if not res.success:
                print(f"FAIL  {res.url}  → {res.error_message}")
                continue

            depth = res.metadata.get("depth", 0)
            print(f"OK    {res.url}  (depth {depth})")

            # Markdown file — make the slug Windows‑safe
            slug = res.url.replace("https://www.vericormed.com", "").strip("/") or "home"
            safe_slug = re.sub(r'[<>:"/\\\\|?*]', "_", slug)[:150]  # replace illegal chars, truncate to 150

            (out_dir / f"{safe_slug}.md").write_text(
                res.markdown.raw_markdown,
                encoding="utf-8"
            )

            # Link record
            link_file.write(json.dumps({
                "url": res.url,
                "timestamp": dt.datetime.utcnow().isoformat(),
                "depth": depth,
                "links": res.links,
            }) + "\n")
            link_file.flush()  # ensure data reaches disk even if interrupted



    print(f"\n✓ Finished — saved {len(results)} pages "
          f"and link data to {links_path}")

if __name__ == "__main__":
    asyncio.run(main())
