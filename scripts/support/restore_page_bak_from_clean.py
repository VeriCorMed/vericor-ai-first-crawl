# restore_page_bak_from_clean.py
from pathlib import Path
import shutil

CLEAN = Path("clean")                      # original cleaned pages (with VC shortcodes)
PAGES = Path("pages_clean/pages")          # your working pages
made = 0
missing = []

for md in PAGES.glob("*.md"):
    bak = md.with_suffix(md.suffix + ".bak")
    if bak.exists():
        continue
    src = CLEAN / md.name                  # matching by slug file name
    if src.exists():
        shutil.copy2(src, bak)
        made += 1
    else:
        missing.append(md.name)

print(f"✓ Created {made} .md.bak files next to pages in {PAGES}")
if missing:
    print("⚠ No matching source in clean/ for:")
    for name in missing[:20]:
        print("  -", name)
    if len(missing) > 20:
        print(f"  …and {len(missing)-20} more")
