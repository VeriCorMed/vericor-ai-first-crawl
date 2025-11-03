# clean_vc_shortcodes.py
"""
WPBakery/Visual Composer cleaner for Vericor Markdown.

Features
- Backs up originals to .md.bak (unless --source=bak).
- Replaces [vc_single_image ...] with inline Markdown images from front-matter `images:`.
- Unwraps/drops common VC layout wrappers (rows, columns, separators, empty space, custom headings).
- FINAL VACUUM: strips any remaining [vc_*] / [/vc_*] tags so orphans don’t linger.
- Strict mode (--strict): logs all unmatched VC tags to logs/vc_leftovers.txt (file : line : tag).
- NEW: --bulletify-icons converts lines starting with “icon-like” images into real list items.

Usage (examples)
  python clean_vc_shortcodes.py --dir=pages_clean/products --force --inline-images --strict --bulletify-icons
  python clean_vc_shortcodes.py --dir=pages_clean/pages   --force --strict
  python clean_vc_shortcodes.py --dir=pages_clean/posts   --force --strict

Notes
- Requires PyYAML (installed earlier in this project).
- .md.bak are originals; delete them when satisfied.
"""

from __future__ import annotations
import re
import sys
import argparse
from pathlib import Path
from typing import Tuple, List, Dict, Any

import yaml

# ---------- Regexes ----------
VC_TAG_ANY = re.compile(r"\[(?:/?vc_[^\]]*)\]")
VC_SINGLE_IMAGE = re.compile(r"\[vc_single_image\b[^\]]*\]", re.IGNORECASE)

VC_OPEN_WRAPPERS = [
    r"\[vc_row[^\]]*\]",
    r"\[vc_row_inner[^\]]*\]",
    r"\[vc_column(?:_inner)?[^\]]*\]",
    r"\[vc_column_text[^\]]*\]",
    r"\[vc_section[^\]]*\]",
]
VC_CLOSE_WRAPPERS = [
    r"\[/vc_row\]",
    r"\[/vc_row_inner\]",
    r"\[/vc_column(?:_inner)?\]",
    r"\[/vc_column_text\]",
    r"\[/vc_section\]",
]
VC_NOISE = [
    r"\[vc_empty_space[^\]]*\]",
    r"\[vc_separator[^\]]*\]",
    r"\[vc_custom_heading[^\]]*\]",
    r"\[vc_message[^\]]*\]",
    r"\[vc_tta_accordion[^\]]*\]",
    r"\[vc_tta_section[^\]]*\]",
    r"\[/vc_tta_section\]",
    r"\[/vc_tta_accordion\]",
]

RE_OPEN_WRAPPERS = [re.compile(pat, re.IGNORECASE) for pat in VC_OPEN_WRAPPERS]
RE_CLOSE_WRAPPERS = [re.compile(pat, re.IGNORECASE) for pat in VC_CLOSE_WRAPPERS]
RE_NOISE = [re.compile(pat, re.IGNORECASE) for pat in VC_NOISE]

# Icon “hint” for bulletify step (filenames/alt that look like icons)
ICON_HINT = re.compile(r"(?i)(icon|ico|check|tick|bullet|arrow|circle|dot)")

FM_BOUNDARY = re.compile(r"^---\s*$", re.MULTILINE)


# ---------- Front matter helpers ----------
def split_front_matter(text: str) -> Tuple[str, str]:
    """Return (front_matter_text_or_empty, body)."""
    m = list(FM_BOUNDARY.finditer(text))
    if len(m) >= 2 and m[0].start() == 0:
        return text[m[0].end():m[1].start()], text[m[1].end():]
    return "", text


def join_front_matter(front: str, body: str) -> str:
    front = front.strip()
    if front:
        return f"---\n{front}\n---\n\n{body.lstrip()}"
    return body.lstrip()


def load_frontmatter_yaml(front: str) -> Dict[str, Any]:
    if not front.strip():
        return {}
    try:
        data = yaml.safe_load(front) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def dump_frontmatter_yaml(data: Dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()


# ---------- VC transforms ----------
def map_single_images_with_frontmatter(body: str, fm: Dict[str, Any]) -> str:
    """
    Replace each [vc_single_image] with the next item from fm['images'].
    If we run out, insert a placeholder: ![image]()
    """
    images = fm.get("images") or []
    idx = 0

    def repl(_m: re.Match) -> str:
        nonlocal idx
        if idx < len(images) and isinstance(images[idx], dict):
            src = images[idx].get("src") or ""
            alt = images[idx].get("alt") or images[idx].get("name") or ""
            idx += 1
            if src:
                return f"![{alt}]({src})"
        idx += 1
        return "![image]()"

    return VC_SINGLE_IMAGE.sub(repl, body)


def unwrap_wrappers_and_noise(body: str) -> str:
    # Drop/unwrap opening wrappers
    for rx in RE_OPEN_WRAPPERS:
        body = rx.sub("", body)
    # Drop closing wrappers
    for rx in RE_CLOSE_WRAPPERS:
        body = rx.sub("", body)
    # Remove layout noise → spacing
    for rx in RE_NOISE:
        body = rx.sub("\n\n", body)
    return body


def final_vacuum(body: str) -> str:
    """Remove any remaining [vc_*] or [/vc_*] tags (orphans)."""
    return VC_TAG_ANY.sub("", body)


def normalize_whitespace(body: str) -> str:
    body = re.sub(r"[ \t]+\n", "\n", body)   # trim trailing spaces
    body = re.sub(r"\n{3,}", "\n\n", body)   # collapse >2 blank lines
    return body.strip() + "\n"


def collect_vc_leftovers(body: str) -> List[Tuple[int, str]]:
    leftovers: List[Tuple[int, str]] = []
    if "[vc_" not in body and "[/vc_" not in body:
        return leftovers
    for i, line in enumerate(body.splitlines(), start=1):
        for m in VC_TAG_ANY.finditer(line):
            leftovers.append((i, m.group(0)))
    return leftovers


def ensure_logs_dir() -> Path:
    logs = Path("logs")
    logs.mkdir(exist_ok=True)
    return logs


def log_leftovers(md_path: Path, leftovers: List[Tuple[int, str]]) -> None:
    if not leftovers:
        return
    logs = ensure_logs_dir()
    out = logs / "vc_leftovers.txt"
    with out.open("a", encoding="utf-8") as f:
        f.write(f"# {md_path}\n")
        for ln, tag in leftovers:
            f.write(f"{md_path.name} : {ln} : {tag}\n")


# ---------- Icon bulletify ----------
def bulletify_icon_lines(body: str) -> str:
    """
    Turn lines that begin with a likely “icon image” into list bullets.

    Example:
      ![check](.../green-clipart-circle-1.png) Phase Change Technology
      →  - Phase Change Technology
    """
    out_lines: List[str] = []
    for line in body.splitlines():
        m = re.match(r'^[ \t]*!\[([^\]]*)\]\(([^)]+)\)[ \t]*(.*)$', line)
        if m:
            alt, url, rest = m.groups()
            if ICON_HINT.search(alt or "") or ICON_HINT.search(url or ""):
                out_lines.append(f"- {rest.strip()}" if rest.strip() else "-")
                continue
        out_lines.append(line)
    return "\n".join(out_lines) + "\n"


# ---------- Core processing ----------
def process_text_for_write(
    raw_text: str,
    inline_images: bool,
    strict: bool,
    bulletify_icons: bool
) -> str:
    front, body = split_front_matter(raw_text)
    fm = load_frontmatter_yaml(front)
    original_body = body

    # 1) unwrap wrappers/noise
    body = unwrap_wrappers_and_noise(body)

    # 2) map [vc_single_image] → markdown images
    if inline_images:
        body = map_single_images_with_frontmatter(body, fm)

    # 3) strict log BEFORE vacuum, so we see what was unmatched
    leftovers = collect_vc_leftovers(body)
    # (logging of leftovers is handled by caller with file path)

    # 4) vacuum remaining vc_* tags
    body = final_vacuum(body)

    # 5) optional bulletify (after images are inlined)
    if bulletify_icons:
        body = bulletify_icon_lines(body)

    # 6) whitespace tidy
    body = normalize_whitespace(body)

    if body == original_body:
        # No change; return original
        return raw_text

    new_front = dump_frontmatter_yaml(fm) if fm else ""
    return join_front_matter(new_front, body), leftovers


def process_file(
    md_path: Path,
    source: str = "md",
    inline_images: bool = False,
    strict: bool = False,
    bulletify_icons: bool = False,
    force: bool = False
) -> Tuple[bool, bool]:
    """
    Returns (changed, skipped_for_safety)

    - If source == 'md': read .md; create .md.bak on first write (unless it already exists).
    - If source == 'bak': read from .md.bak and overwrite .md (no new backup).
    """
    # Choose text source
    if source == "bak":
        bak_path = md_path.with_suffix(md_path.suffix + ".bak")
        if not bak_path.exists():
            return False, False
        text = bak_path.read_text(encoding="utf-8", errors="replace")
    else:
        text = md_path.read_text(encoding="utf-8", errors="replace")

    # Transform
    result = process_text_for_write(text, inline_images, strict, bulletify_icons)
    if isinstance(result, tuple):
        new_text, leftovers = result
    else:
        # Back-compat guard
        new_text, leftovers = result, []

    # Strict logging (if requested and there were leftovers)
    if strict and leftovers:
        log_leftovers(md_path, leftovers)

    # No changes → done
    if new_text == text and source != "bak":
        return False, False

    # Back up if writing from md source and no .bak exists yet
    if source == "md":
        bak_path = md_path.with_suffix(md_path.suffix + ".bak")
        if not bak_path.exists():
            try:
                bak_path.write_text(text, encoding="utf-8")
            except Exception:
                pass

    # Write updated .md
    md_path.write_text(new_text, encoding="utf-8")
    return True, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="pages_clean/products",
                    help="Folder to clean (default: pages_clean/products)")
    ap.add_argument("--source", choices=["md", "bak"], default="md",
                    help="Read from .md (default) or from .md.bak")
    ap.add_argument("--inline-images", action="store_true",
                    help="Replace [vc_single_image] using front-matter images")
    ap.add_argument("--bulletify-icons", action="store_true",
                    help="Convert lines starting with likely icon images into '- ' bullets")
    ap.add_argument("--strict", action="store_true",
                    help="Log unmatched VC tags to logs\\vc_leftovers.txt")
    ap.add_argument("--force", action="store_true",
                    help="(Reserved for future safety toggles)")
    args = ap.parse_args()

    base = Path(args.dir)
    if not base.exists():
        print(f"🛑 Folder not found: {base.resolve()}")
        sys.exit(1)

    files: List[Path] = sorted(base.glob("*.md"))
    if not files:
        print(f"ℹ No .md files in {base}")
        return

    changed = 0
    unchanged = 0
    skipped = 0

    for md in files:
        ch, sk = process_file(
            md_path=md,
            source=args.source,
            inline_images=args.inline_images,
            strict=args.strict,
            bulletify_icons=args.bulletify_icons,
            force=args.force,
        )
        if sk:
            skipped += 1
        elif ch:
            changed += 1
        else:
            unchanged += 1

    label = []
    if args.inline_images:
        label.append("inline images")
    if args.bulletify_icons:
        label.append("bulletify icons")
    label_text = f" ({', '.join(label)})" if label else ""

    print(f"✓ VC cleaned{label_text}: {changed} changed, {unchanged} unchanged, {skipped} skipped  / {len(files)}")
    if args.strict:
        print("ℹ Strict mode: see logs\\vc_leftovers.txt for any unrecognized VC shortcodes.")
    print("ℹ .md.bak files are originals; delete them when satisfied.")


if __name__ == "__main__":
    main()
