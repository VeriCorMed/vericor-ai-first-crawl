#!/usr/bin/env python3
"""
organize_project.py  —  standalone

Reorganize the vericor-crawl repo into a clean structure.

- Creates standardized folders if missing
- Moves scripts into /scripts/{crawl,processing,export,support,tests}
- Moves data artifacts into /data and /exports
- Moves env files into /env (keeps existing venv wherever it already lives)
- Keeps a CSV move log for undo in .organize_logs/
- Supports --dry-run and --undo

Usage (run from repo root):
  python organize_project.py --dry-run
  python organize_project.py
  python organize_project.py --undo
"""
import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys
from typing import List, Tuple, Optional

# ---- Desired folders ----
FOLDERS = {
    "scripts": [
        "scripts/crawl",
        "scripts/processing",
        "scripts/export",
        "scripts/support",
        "scripts/tests",
    ],
    "data": [
        "data/clean",
        "data/pages_clean",
        "data/logs",
    ],
    "exports": [],
    "env": [],
    "ops": [],
}

# ---- File routing rules (first match wins) ----
FILE_RULES = [
    # Crawlers
    (r"^(crawl_vcm|deep_crawl_vcm|sitemap_subset)\.py$", "scripts/crawl"),
    # Backfill fetchers (treat as crawl)
    (r"^(backfill_selected_pages|backfill_selected_posts)\.py$", "scripts/crawl"),

    # Processing / cleaning
    (r"^(preprocess_clean|clean_vc_shortcodes|normalize_pages_format|"
     r"normalize_product_frontmatter|inject_page_videos|add_inline_videos|"
     r"clean_products_markdown|sitemap_split_pages_posts)\.py$", "scripts/processing"),

    # Exports
    (r"^(export_products|export_to_workbook|export_products_to_audit)\.py$", "scripts/export"),

    # Support / utils
    (r"^(product_meta_enricher_api|restore_baks|restore_page_bak_from_clean)\.py$", "scripts/support"),

    # Tests / scratch
    (r"^test_.*\.py$", "scripts/tests"),
    (r"^from_pathlib_import_Path\.py$", "scripts/tests"),
    (r"^from pathlib import Path\.py$", "scripts/tests"),  # handle the odd filename

    # Ops
    (r"^(site_audit_refresh)\.py$", "ops"),
    (r"^(start_vericor_env|refresh_audit|run_all)\.bat$", "ops"),

    # Env and requirements
    (r"^install_requirements\.bat$", "env"),
    (r"^requirements\.txt$", "env"),
    (r"^\.env$", "env"),

    # Excel exports
    (r"^(audit_export_[0-9\-]+|vericor_products_audit)\.xlsx$", "exports"),

    # This organizer itself -> ops
    (r"^organize_project\.py$", "ops"),
]


# ---- Legacy folders to migrate ----
LEGACY_TO_DATA = [
    ("pages_clean", "data/pages_clean"),
    ("logs", "data/logs"),
    ("clean", "data/clean"),
    ("output", "exports"),  # old 'output' becomes 'exports'
]

MOVE_LOG_DIR = ".organize_logs"

@dataclass
class MoveRecord:
    src: str
    dst: str

def ensure_dirs(root: Path, dry_run: bool = False) -> None:
    for top, subs in FOLDERS.items():
        top_path = root / top
        if not top_path.exists():
            print(f"[create] {top_path}")
            if not dry_run:
                top_path.mkdir(parents=True, exist_ok=True)
        for sub in subs:
            p = root / sub
            if not p.exists():
                print(f"[create] {p}")
                if not dry_run:
                    p.mkdir(parents=True, exist_ok=True)
    # ensure destinations for legacy folders exist
    for legacy, target in LEGACY_TO_DATA:
        legacy_path = root / legacy
        target_path = root / target
        if legacy_path.exists() and not target_path.exists():
            print(f"[create] {target_path}")
            if not dry_run:
                target_path.mkdir(parents=True, exist_ok=True)

def match_destination(filename: str) -> Optional[str]:
    for pattern, dest in FILE_RULES:
        if re.match(pattern, filename, flags=re.IGNORECASE):
            return dest
    return None

def move_with_rules(root: Path, dry_run: bool = False) -> List[MoveRecord]:
    records: List[MoveRecord] = []
    for item in root.iterdir():
        if item.is_dir():
            continue
        dest = match_destination(item.name)
        if dest:
            dst_path = root / dest / item.name
            if dst_path.exists():
                print(f"[skip] Destination exists: {dst_path}")
                continue
            print(f"[move] {item.name} -> {dest}/")
            records.append(MoveRecord(str(item), str(dst_path)))
            if not dry_run:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(item), str(dst_path))
    return records

def move_legacy_folders(root: Path, dry_run: bool = False) -> List[MoveRecord]:
    records: List[MoveRecord] = []
    for legacy, target in LEGACY_TO_DATA:
        src = root / legacy
        dst = root / target
        if src.exists() and src.is_dir():
            for child in src.iterdir():
                target_path = dst / child.name
                if target_path.exists():
                    print(f"[skip] Destination exists: {target_path}")
                    continue
                print(f"[move-dir] {child} -> {target_path}")
                records.append(MoveRecord(str(child), str(target_path)))
                if not dry_run:
                    dst.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(child), str(target_path))
            # remove empty legacy folder if possible
            try:
                if not dry_run and not any(src.iterdir()):
                    src.rmdir()
            except Exception:
                pass
    return records

def write_move_log(root: Path, records: List[MoveRecord]) -> Path:
    log_dir = root / MOVE_LOG_DIR
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"moves_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with log_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["src", "dst"])
        for r in records:
            writer.writerow([r.src, r.dst])
    print(f"[log] Wrote move log: {log_path}")
    return log_path

def find_latest_move_log(root: Path) -> Optional[Path]:
    log_dir = root / MOVE_LOG_DIR
    if not log_dir.exists():
        return None
    logs = sorted(log_dir.glob("moves_*.csv"), reverse=True)
    return logs[0] if logs else None

def undo_moves(root: Path, log_path: Path, dry_run: bool = False) -> None:
    print(f"[undo] Using log: {log_path}")
    with log_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for row in reversed(rows):
        src = Path(row["src"])
        dst = Path(row["dst"])
        if dst.exists():
            print(f"[undo-move] {dst} -> {src}")
            if not dry_run:
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(src))
        else:
            print(f"[undo-skip] Missing destination to move back: {dst}")

def main():
    ap = argparse.ArgumentParser(description="Reorganize vericor-crawl repository structure.")
    ap.add_argument("--root", type=str, default=".", help="Project root (default: current directory)")
    ap.add_argument("--dry-run", action="store_true", help="Preview moves without changing files")
    ap.add_argument("--undo", action="store_true", help="Undo the last organize run via the latest move log")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root does not exist: {root}")
        sys.exit(1)

    if args.undo:
        log_path = find_latest_move_log(root)
        if not log_path:
            print("No move logs found.")
            sys.exit(1)
        undo_moves(root, log_path, dry_run=args.dry_run)
        print("[done] Undo complete (dry-run)" if args.dry_run else "[done] Undo complete")
        return

    print(f"[start] Organizing project at: {root}")
    ensure_dirs(root, dry_run=args.dry_run)

    records: List[MoveRecord] = []
    records += move_legacy_folders(root, dry_run=args.dry_run)
    records += move_with_rules(root, dry_run=args.dry_run)

    if records and not args.dry_run:
        write_move_log(root, records)

    print("[done] Dry-run complete" if args.dry_run else "[done] Organization complete")

if __name__ == "__main__":
    main()
