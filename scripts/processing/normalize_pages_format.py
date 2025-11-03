# normalize_pages_format.py
# -------------------------
# Normalize Markdown formatting for pages (not products).
# Removes leftover VC shortcodes, collapses empty rows, adjusts headings.

from pathlib import Path
import re

ROOT = Path(".")
TARGET_DIRS = [
    Path("pages_clean/pages"),
    Path("pages_clean/posts"),
]

# --- helpers -----------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_or_empty, body). Keeps the --- blocks intact."""
    if text.startswith("---"):
        m = re.search(r"^---\s*$.*?^---\s*$", text, flags=re.DOTALL | re.MULTILINE)
        if m:
            fm = m.group(0)
            body = text[m.end():]
            return fm, body
    return "", text

def smart_titlecase(s: str) -> str:
    s = s.strip()
    # lower noise spacing
    s = re.sub(r"\s+", " ", s)
    # keep existing capitalization if it looks mixed-case already
    if re.search(r"[a-z].*[A-Z]", s) or re.search(r"[A-Z].*[a-z]", s):
        return s
    # otherwise title-case, but keep small words lower
    small = {"a","an","and","as","at","but","by","for","in","of","on","or","the","to","vs","via"}
    words = re.split(r"(\s+|-)", s)
    out = []
    for w in words:
        if re.fullmatch(r"\s+|-", w):
            out.append(w)
        else:
            low = w.lower()
            out.append(low if low in small else low.capitalize())
    # first and last word: capitalize
    joined = "".join(out)
    parts = re.split(r"(\s+|-)", joined)
    tokens = [t for t in parts if not re.fullmatch(r"\s+|-", t)]
    if tokens:
        first = tokens[0]
        last = tokens[-1]
        joined = re.sub(r"^"+re.escape(first), first.capitalize(), joined, count=1)
        joined = re.sub(re.escape(last)+r"$", last.capitalize(), joined, count=1)
    return joined

def fix_bold_headings(body: str) -> str:
    # Lines like **FUNCTION-BASED MODULES**  →  ### Function-based modules
    def repl(m):
        text = m.group(1)
        text = re.sub(r"[*_`]+", "", text).strip()
        if not text:
            return ""
        return "### " + smart_titlecase(text)
    return re.sub(r"^\s*\*\*\s*(.+?)\s*\*\*\s*$", repl, body, flags=re.MULTILINE)

def unwrap_thumb_linked_images(body: str) -> str:
    # [![ALT](thumb)](full)  →  ![ALT](full)
    def repl(m):
        alt = m.group(1).strip()
        full = m.group(3).strip()
        return f"![{alt}]({full})"
    return re.sub(r"\[\!\[(.*?)\]\((.*?)\)\]\((.*?)\)", repl, body)

def drop_decorative_images(body: str) -> str:
    # Remove lines that are only one image and match specific decorative names.
    pattern = re.compile(
        r"^\s*!\[[^\]]*\]\((?:[^)]+(?:have-questions|ico-news)[^)]+)\)\s*$",
        flags=re.IGNORECASE | re.MULTILINE
    )
    return pattern.sub("", body)

def strip_stray_backtick_lines(body: str) -> str:
    # Lines that are just ` or `` or ``` (and spaces)
    return re.sub(r"(?m)^[\s`]{1,5}$", "", body)

def collapse_blank_lines(body: str) -> str:
    body = re.sub(r"\n{3,}", "\n\n", body)
    # trim leading/trailing newlines
    return body.strip() + "\n"

def clean_one(markdown_text: str) -> str:
    fm, body = split_frontmatter(markdown_text)

    # 1) unwrap VC-style linked thumbnails
    body = unwrap_thumb_linked_images(body)

    # 2) remove decorative images
    body = drop_decorative_images(body)

    # 3) bold-to-heading where appropriate
    body = fix_bold_headings(body)

    # 4) drop stray backtick-only lines
    body = strip_stray_backtick_lines(body)

    # 5) squash blank-line noise
    body = collapse_blank_lines(body)

    return (fm + ("\n" if fm and not fm.endswith("\n") else "")) + body

# --- main --------------------------------------------------------------------

def process_dir(d: Path) -> tuple[int,int,int]:
    changed = unchanged = skipped = 0
    if not d.exists():
        return (0,0,0)
    for md in sorted(d.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        cleaned = clean_one(text)
        if cleaned == text:
            unchanged += 1
            continue
        # write .fmt.bak only once
        bak = md.with_suffix(md.suffix + ".fmt.bak")
        if not bak.exists():
            bak.write_text(text, encoding="utf-8")
        md.write_text(cleaned, encoding="utf-8")
        changed += 1
    return changed, unchanged, skipped

def main():
    total_c = total_u = total_s = 0
    for d in TARGET_DIRS:
        c,u,s = process_dir(d)
        total_c += c; total_u += u; total_s += s
    print(f"✓ Normalized pages/posts: {total_c} changed, {total_u} unchanged")
    print("ℹ .fmt.bak are backups created on first change; delete once satisfied.")

if __name__ == "__main__":
    main()
