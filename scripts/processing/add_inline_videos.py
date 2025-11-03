# add_inline_videos.py
# Insert YouTube videos inline under headings, based on the order of [vc_video] blocks
# found in the original .md.bak capture.
#
# Strategy:
# 1) From <file>.md.bak, extract video URLs in page order.
# 2) In cleaned <file>.md, find H2 headings (lines starting with "## ").
#    - If len(videos) == len(H2s): insert one video right after each H2, in order.
#    - Else if a "## Videos" section exists: replace that section with our video list.
#    - Else: append at the end.
#
# Safety:
# - Create <file>.md.prevideo once (if it doesn't exist yet) before modifying .md.

from pathlib import Path
import re
import sys
from typing import List, Tuple

PAGES_DIR = Path("pages_clean/pages")  # change/add folders if needed

VIDEO_RE = re.compile(r'\[vc_video\b[^]]*?link="([^"]+)"[^]]*\]', re.IGNORECASE)
H2_RE = re.compile(r'^(## .+)$', re.MULTILINE)

def extract_videos_from_bak(bak_text: str) -> List[str]:
    return VIDEO_RE.findall(bak_text)

def find_h2_positions(md_text: str) -> List[Tuple[int, str]]:
    """Return list of (line_index, heading_line_text) for H2 headings."""
    lines = md_text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if line.startswith("## "):
            out.append((i, line))
    return out

def replace_videos_section(md_text: str, video_urls: List[str]) -> str:
    """If there's a '## Videos' section, replace its list with our links."""
    lines = md_text.splitlines()
    # Find '## Videos' heading
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower() == "## videos":
            start_idx = i
            break
    if start_idx is None:
        return md_text  # no videos section to replace

    # Find where that section ends (next H2 or EOF)
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if lines[j].startswith("## "):
            end_idx = j
            break

    # Build new section
    new_block = []
    new_block.append("## Videos")
    new_block.append("")
    for url in video_urls:
        new_block.append(f"- [▶ Watch]({url})")
    new_block.append("")

    new_lines = lines[:start_idx] + new_block + lines[end_idx:]
    return "\n".join(new_lines)

def insert_videos_after_h2(md_text: str, video_urls: List[str]) -> str:
    """Insert one video link right after each H2 (in order)."""
    lines = md_text.splitlines()
    h2_positions = [i for i, _ in find_h2_positions(md_text)]
    if not h2_positions:
        # no H2s — just append at end
        out = lines + ["", "## Videos", ""]
        out += [f"- [▶ Watch]({u})" for u in video_urls]
        out.append("")
        return "\n".join(out)

    # if more videos than headings, we’ll place extra under a trailing "## Videos"
    per_heading = min(len(video_urls), len(h2_positions))
    inserted_count = 0

    # We’ll insert from bottom to top so indices stay valid.
    for idx in reversed(range(per_heading)):
        h2_line = h2_positions[idx]
        insert_at = h2_line + 1
        block = ["", f"- [▶ Watch]({video_urls[idx]})"]
        lines[insert_at:insert_at] = block
        inserted_count += 1

    remaining = video_urls[inserted_count:]
    if remaining:
        # put remaining links into (or under) a Videos section
        tmp = "\n".join(lines)
        tmp2 = replace_videos_section(tmp, remaining)
        if tmp2 == tmp:
            # no existing '## Videos' — append one
            lines = lines + ["", "## Videos", ""]
            lines += [f"- [▶ Watch]({u})" for u in remaining]
            lines.append("")
            return "\n".join(lines)
        else:
            return tmp2
    else:
        return "\n".join(lines)

def process_file(md_path: Path) -> Tuple[bool, str]:
    """
    Returns (changed, message)
    """
    bak_path = md_path.with_suffix(md_path.suffix + ".bak")
    if not bak_path.exists():
        return (False, "no .bak present")

    bak = bak_path.read_text(encoding="utf-8", errors="replace")
    video_urls = extract_videos_from_bak(bak)
    if not video_urls:
        return (False, "no videos found in .bak")

    md = md_path.read_text(encoding="utf-8", errors="replace")

    # One-time safety backup of the current cleaned file
    prevideo = md_path.with_suffix(".md.prevideo")
    if not prevideo.exists():
        prevideo.write_text(md, encoding="utf-8")

    h2s = find_h2_positions(md)
    if len(video_urls) == len(h2s) and h2s:
        new_md = insert_videos_after_h2(md, video_urls)
        if new_md != md:
            md_path.write_text(new_md, encoding="utf-8")
            return (True, f"inline under {len(h2s)} H2s")
        return (False, "no change after inline attempt")
    else:
        # Try to replace an existing Videos section; if none, append
        replaced = replace_videos_section(md, video_urls)
        if replaced != md:
            md_path.write_text(replaced, encoding="utf-8")
            return (True, "replaced '## Videos' section")
        else:
            appended = md.rstrip() + "\n\n## Videos\n\n" + "\n".join(
                f"- [▶ Watch]({u})" for u in video_urls
            ) + "\n"
            if appended != md:
                md_path.write_text(appended, encoding="utf-8")
                return (True, "appended '## Videos' section at end")
            return (False, "no change")

def main() -> None:
    if not PAGES_DIR.exists():
        print(f"🛑 Missing folder: {PAGES_DIR.resolve()}")
        sys.exit(1)

    changed = 0
    unchanged = 0
    skipped = 0
    for md_path in sorted(PAGES_DIR.glob("*.md")):
        c, msg = process_file(md_path)
        if c:
            changed += 1
            print(f"✓ {md_path.name}: {msg}")
        else:
            if msg == "no .bak present":
                skipped += 1
            else:
                unchanged += 1
            print(f"• {md_path.name}: {msg}")

    print(f"\nDone — {changed} changed, {unchanged} unchanged, {skipped} skipped")

if __name__ == "__main__":
    main()
