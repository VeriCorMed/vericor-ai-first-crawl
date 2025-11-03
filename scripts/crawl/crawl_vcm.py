# scripts/crawl/crawl_vcm.py
"""
Crawl https://www.vericormed.com (bounded BFS) and write raw Markdown + link records.

- Compatible with crawl4ai >= 0.7.x and Python 3.13
- NO 'browser_config=' passed into CrawlerRunConfig (some versions don't accept it)
- Outputs to project-root/data/clean/crawl_raw + project-root/data/logs

This is the RAW crawl step. Cleaning/normalization happens later in the pipeline.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import re
from pathlib import Path

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter, URLPatternFilter
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy


# ---------- Paths (standardized) ----------
ROOT = Path(__file__).resolve().parents[2]                     # .../vericor-crawl
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "clean" / "crawl_raw"                      # raw markdown output
LOGS_DIR = DATA_DIR / "logs"
RAW_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

TS = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
LINKS_PATH = LOGS_DIR / f"links_{TS}.jsonl"


# ---------- Helpers ----------
SAFE_CHARS_RE = re.compile(r"[^a-z0-9\-_]+")

def slugify_url(url: str) -> str:
    """
    Convert a URL to a safe filesystem name.
    e.g., https://www.vericormed.com/products/cool-cube-08/ ->
          products_cool-cube-08
    """
    base = url.replace("https://www.vericormed.com", "").strip("/")
    if not base:
        base = "home"
    base = base.replace("/", "_")
    base = base.lower()
    base = SAFE_CHARS_RE.sub("-", base)
    return base.strip("-") or "page"


# ---------- Core crawl ----------
async def run_crawl() -> int:
    # Filters: domain + ignore common non-content paths
    filters = FilterChain([
        DomainFilter(allowed_domains=["vericormed.com"]),
        URLPatternFilter(
            patterns=[
                "*wp-admin*", "*wp-login*", "*feed*",
                "*?add-to-cart*", "*cart*", "*checkout*",
                "*account*", "*my-account*",
            ],
            reverse=True,
        ),
    ])

    # Crawl configuration (bounded BFS)
    crawl_cfg = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=5,
            max_pages=400,
            include_external=False,
            filter_chain=filters,
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        cache_mode=CacheMode.BYPASS,
        verbose=True,
        stream=False,                 # Python 3.13 streaming workaround
        delay_before_return_html=0.5,
        # NOTE: DO NOT pass browser_config= here; some versions error on this arg.
    )

    saved = 0
    async with AsyncWebCrawler():     # no positional args; default browser config
        results = await AsyncWebCrawler().arun(
            "https://www.vericormed.com",
            config=crawl_cfg
        )

    # Persist outputs
    with LINKS_PATH.open("w", encoding="utf-8") as link_file:
        for res in results:
            if not getattr(res, "ok", False):
                print(f"FAIL  {res.url}  → {getattr(res, 'error_message', 'unknown error')}")
                continue

            depth = (res.metadata or {}).get("depth", 0)
            print(f"OK    {res.url}  (depth {depth})")

            # Write Markdown
            name = slugify_url(res.url) + ".md"
            (RAW_DIR / name).write_text(res.markdown.raw_markdown, encoding="utf-8")
            saved += 1

            # Write link record
            link_file.write(json.dumps({
                "url": res.url,
                "timestamp": dt.datetime.utcnow().isoformat() + "Z",
                "depth": depth,
                "links_internal": getattr(res, "links_internal", []),
                "links_external": getattr(res, "links_external", []),
            }) + "\n")

    print(f"\n✓ Finished — saved {saved} pages and link data to {LINKS_PATH}")
    return saved


def main() -> None:
    try:
        asyncio.run(run_crawl())
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
