# inject_page_videos.py
# Fetch each page's live HTML, find video embeds (YouTube/Vimeo/iframed mp4),
# and inject a "## Videos" section with Markdown links into the matching .md file.

from pathlib import Path
import re
import sys
import requests
from bs4 import BeautifulSoup

BASE = "https://www.vericormed.com"
PAGES_DIR = Path("pages_clean/pages")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": BASE + "/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Simple detectors
YOUTUBE_PAT = re.compile(r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+))", re.I)
VIMEO_PAT   = re.compile(r"(https?://(?:www\.)?vimeo\.com/\d+)", re.I)

def url_for_slug(slug: str) -> str:
    slug = slug.strip("/")
    return f"{BASE}/{slug}/" if slug else f"{BASE}/"

def find_video_urls_in_html(html: str) -> list[str]:
    out: list[str] = []
    soup = BeautifulSoup(html, "lxml")

    # 1) iframes with youtube/vimeo
    for ifr in soup.find_all("iframe"):
        src = (ifr.get("src") or "").strip()
        if not src:
            continue
        if "youtube.com" in src or "youtu.be" in src or "vimeo.com" in src:
            out.append(src)

    # 2) direct links in the HTML text (covers vc_video link="..."), youtube/vimeo
    for m in YOUTUBE_PAT.finditer(html):
        out.append(m.group(1))
    for m in VIMEO_PAT.finditer(html):
        out.append(m.group(1))

    # 3) simple <video><source src="..."></video> (self-hosted)
    for vid in soup.find_all("video"):
        src = (vid.get("src") or "").strip()
        if src:
            out.append(src)
        for src_tag in vid.find_all("source"):
            s = (src_tag.get("src") or "").strip()
            if s:
                out.append(s)

    # normalize and de-dup in order
    seen = set()
    uniq: list[str] = []
    for u in out:
        u = u.strip()
        if not u:
            continue
        # Convert youtube embed URLs to watch form if possible
        if "youtube.com/embed/" in u:
            vid = u.rsplit("/", 1)[-1].split("?")[0]
            u = f"https://www.youtube.com/watch?v={vid}"
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq

def inject_videos(md_text: str, video_urls: list[str]) -> tuple[str, bool]:
    """Insert or replace a '## Videos' section with a bulleted list of links."""
    if not video_urls:
        return md_text, False

    # If a Videos section exists, replace its content; else append at the end.
    videos_h2 = re.compile(r"(?im)^##\s+Videos\s*$")
    bullets   = "\n".join([f"- [▶ Watch]({u})" for u in video_urls])

    section = f"\n\n## Videos\n\n{bullets}\n"

    # Try to replace existing section (until next H2 or end of file)
    if videos_h2.search(md_text):
        # Find start
        start = videos_h2.search(md_text).start()
        # Find next H2 after start
        next_h2 = re.search(r"(?im)^##\s+\S.*$", md_text[videos_h2.search(md_text).end():])
        if next_h2:
            end = videos_h2.search(md_text).end() + next_h2.start()
            new_md = md_text[:start] + section + md_text[end:]
        else:
            new_md = md_text[:start] + section
        return new_md, True
    else:
        # Append at end
        return md_text.rstrip() + section, True

def process_one(md_path: Path) -> tuple[bool, str]:
    slug = md_path.stem  # file name without .md
    url = url_for_slug(slug)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        return False, f"Fetch failed {url} → {e}"

    vids = find_video_urls_in_html(resp.text)
    if not vids:
        return False, "No videos detected"

    original = md_path.read_text(encoding="utf-8", errors="replace")
    updated, changed = inject_videos(original, vids)
    if changed and updated != original:
        # one-time backup
        bak = md_path.with_suffix(".md.bak_videos")
        if not bak.exists():
            bak.write_text(original, encoding="utf-8")
        md_path.write_text(updated, encoding="utf-8")
        return True, f"Inserted {len(vids)} video link(s)"
    else:
        return False, "Already had a Videos section"

def main():
    # Optional: allow a single file via CLI arg
    targets = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            p = Path(arg)
            if p.is_file():
                targets.append(p)
    if not targets:
        targets = sorted(PAGES_DIR.glob("*.md"))

    changed = 0
    unchanged = 0
    skipped = 0
    for p in targets:
        ok, msg = process_one(p)
        if ok:
            changed += 1
            print(f"✓ {p.name}: {msg}")
        else:
            if msg.startswith("No videos detected"):
                skipped += 1
            else:
                unchanged += 1
            print(f"· {p.name}: {msg}")

    print(f"\nDone. {changed} updated, {unchanged} unchanged, {skipped} without videos.")

if __name__ == "__main__":
    main()
