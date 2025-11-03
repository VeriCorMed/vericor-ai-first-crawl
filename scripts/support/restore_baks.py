from pathlib import Path
import sys

root = Path("pages_clean/products")
if not root.exists():
    print(f"Missing folder: {root.resolve()}")
    sys.exit(1)

restored = 0
for bak in root.glob("*.md.bak"):
    target = bak.with_suffix("")
    data = bak.read_text(encoding="utf-8", errors="replace")
    target.write_text(data, encoding="utf-8")
    restored += 1

print(f"Restored {restored} files from .bak")
