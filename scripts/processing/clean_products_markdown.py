# clean_products_markdown.py
"""
Strip Visual Composer shortcodes from product Markdown files.
- Input:  pages_clean/products/*.md
- Output: in-place cleaned files (front-matter preserved)
"""

from pathlib import Path
import re

PRODUCTS_DIR = Path("pages_clean") / "products"

# --- regexes ---
# vc_video: keep the link as plain URL
RE_VC_VIDEO = re.compile(r'\[\s*vc\\?_video\b[^]]*?\blink="([^"]+)"[^]]*?\]', re.IGNORECASE)

# self-closing VC blocks (single_image, separator, etc.) → drop entirely
RE_VC_SELF = re.compile(r'\[\s*vc\\?_(?:single_image|separator|empty_space|icon|btn|custom_heading|gallery)[^]]*?\]', re.IGNORECASE)

# opening/closing wrappers like [vc_row], [/vc_row], [vc_column], [vc_section], etc. → remove just the tags
RE_VC_TAGS = re.compile(r'\[/?\s*vc\\?_[^]]*?\]', re.IGNORECASE)

# after VC removal, collapse 3+ blank lines → 2, then 2 → 1
RE_ML_BLANKS = re.compile(r'\n{3,}')

def split_front_matter(text: str):
    """Return (front_matter_block or '', body_text)."""
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            end += 4
            return text[:end].strip() + "\n", text[end+1:].lstrip()
    return "", text

def clean_body(body: str) -> str:
    # 1) vc_video → keep URL
    body = RE_VC_VIDEO.sub(lambda m: f"{m.group(1)}", body)

    # 2) self-closing VC tags → remove
    body = RE_VC_SELF.sub("", body)

    # 3) all remaining VC open/close tags → strip tags only
    body = RE_VC_TAGS.sub("", body)

    # 4) unescape some backslash artifacts that might remain (common after html→md)
    body = body.replace("\\_", "_")

    # 5) tidy excessive blank lines
    body = RE_ML_BLANKS.sub("\n\n", body)
    body = body.strip() + "\n"
    return body

def main():
    if not PRODUCTS_DIR.exists():
        print(f"🛑 Missing folder: {PRODUCTS_DIR.resolve()}")
        return

    files = sorted(PRODUCTS_DIR.glob("*.md"))
    if not files:
        print(f"🛈 No Markdown files in {PRODUCTS_DIR}")
        return

    changed = 0
    for md_path in files:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        fm, body = split_front_matter(text)
        new_body = clean_body(body)
        if new_body != body:
            md_path.write_text(fm + new_body, encoding="utf-8")
            changed += 1

    print(f"✓ Cleaned {changed} product file(s) in {PRODUCTS_DIR}")

if __name__ == "__main__":
    main()
