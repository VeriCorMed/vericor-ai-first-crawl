# test_crawl_vcm.py
"""
Quick sanity‑check crawl for VeriCorMed.com
• Crawls up to 5 pages (depth 2) to verify setup
• Prints URL + HTTP status for each page
"""

import asyncio, json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

async def main() -> None:
    cfg = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2,            # two clicks from the homepage
            max_pages=5,            # tiny cap for test
            include_external=False,
            filter_chain=FilterChain([
                DomainFilter(allowed_domains=["vericormed.com"]),
            ]),
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        cache_mode=CacheMode.BYPASS,
        verbose=True,
        stream=False,              # avoids Py 3.13 streaming bug
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://www.vericormed.com", config=cfg)

    # Print a one‑line JSON record per page
    for r in results:
        print(json.dumps({"url": r.url, "status": r.status_code}))

if __name__ == "__main__":
    asyncio.run(main())
