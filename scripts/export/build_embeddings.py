#!/usr/bin/env python3
"""
build_embeddings.py
Create semantic embeddings from Markdown body text (excludes front-matter).

Default model: sentence-transformers 'all-MiniLM-L6-v2' (local, no API).
Output:
  exports/embeddings.jsonl   (one JSON object per line)

Each line:
  { "id", "type", "title", "url", "chunk_id", "text", "embedding": [floats...] }

Usage:
  python scripts/export/build_embeddings.py
  python scripts/export/build_embeddings.py --model all-MiniLM-L12-v2 --max-chars 1200
"""

from pathlib import Path
import argparse
import json
import re
from typing import Dict, Any, Iterator, Tuple, List

# Deps: sentence-transformers, pyyaml, tqdm
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise SystemExit("Missing dependency: sentence-transformers. Install with: pip install sentence-transformers")

try:
    import yaml
except ImportError:
    raise SystemExit("Missing dependency: pyyaml. Install with: pip install pyyaml")

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **kwargs): return x  # minimal fallback

ROOT = Path(__file__).resolve().parents[2]  # .../vericor-crawl
DATA_DIR = ROOT / "data" / "pages_clean"
EXPORTS_DIR = ROOT / "exports"

FRONTMATTER_RE = re.compile(r"^\ufeff?\s*---\s*\r?\n(.*?)\r?\n---\s*\r?\n?", re.DOTALL | re.MULTILINE)

def split_frontmatter_and_body(text: str) -> Tuple[Dict[str, Any], str]:
    m = FRONTMATTER_RE.search(text)
    fm = {}
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
            text = text[m.end():]
        except yaml.YAMLError:
            pass
    return (fm if isinstance(fm, dict) else {}), text

def simple_chunker(text: str, max_chars: int = 1000) -> Iterator[str]:
    """Chunk text by headings & paragraphs, then pack to ~max_chars."""
    if not text:
        return
    blocks = re.split(r"(?=^#{1,6}\s)|\n\s*\n", text, flags=re.MULTILINE)
    buf, size = [], 0
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if size + len(b) + 2 > max_chars and buf:
            yield "\n\n".join(buf).strip()
            buf, size = [], 0
        buf.append(b)
        size += len(b) + 2
    if buf:
        yield "\n\n".join(buf).strip()

def iter_markdown_files() -> Iterator[Path]:
    for folder in ("pages", "posts", "products"):
        base = DATA_DIR / folder
        if base.exists():
            yield from base.rglob("*.md")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="all-MiniLM-L6-v2", help="sentence-transformers model name")
    ap.add_argument("--max-chars", type=int, default=1000, help="max characters per chunk")
    ap.add_argument("--out", default=str(EXPORTS_DIR / "embeddings.jsonl"), help="output JSONL path")
    args = ap.parse_args()

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[info] Loading model: {args.model} (first run may download)")
    model = SentenceTransformer(args.model)

    out_path = Path(args.out)
    n_docs, n_chunks = 0, 0
    with out_path.open("w", encoding="utf-8") as out_f:
        for md_path in tqdm(sorted(iter_markdown_files()), desc="Embedding"):
            text = md_path.read_text(encoding="utf-8", errors="ignore")
            fm, body = split_frontmatter_and_body(text)
            if not body.strip():
                continue

            doc_id = fm.get("id") or fm.get("sku") or md_path.stem
            rec_type = (fm.get("type") or md_path.parent.name.rstrip("s")).lower()
            title = fm.get("title")
            url = fm.get("url")

            chunks = list(simple_chunker(body, max_chars=args.max_chars))
            if not chunks:
                continue

            embeddings = model.encode(chunks, convert_to_numpy=True, show_progress_bar=False)

            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                obj = {
                    "id": doc_id,
                    "type": rec_type,
                    "title": title,
                    "url": url,
                    "chunk_id": f"{doc_id}::chunk-{i+1}",
                    "text": chunk,
                    "embedding": emb.tolist(),
                }
                out_f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                n_chunks += 1
            n_docs += 1

    print(f"[ok] Wrote {out_path}  (docs: {n_docs}, chunks: {n_chunks})")

if __name__ == "__main__":
    main()
