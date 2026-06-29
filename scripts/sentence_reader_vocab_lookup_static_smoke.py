#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "reader_api" / "app.py"
MIGRATION = ROOT / "migrations" / "reader" / "005_general_dictionary_seed.sql"
DOC = ROOT / "docs" / "product_acceptance.md"
IMPORT_SCRIPT = ROOT / "scripts" / "sentence_reader_import_ecdict.py"


REQUIRED = {
    APP: [
        "def vocab_lookup_candidates",
        "def find_dictionary_entry",
        "def ensure_dictionary_vocab_item",
        "dictionary_fallback",
        "selected_vocab_row(conn, book_id, vocab_id)",
        "book_vocab_items",
        "dictionary_entries",
    ],
    MIGRATION: [
        "strategy",
        "advantage",
        "market",
        "business",
        "dictionary_entries",
        "seed_general",
        "ON CONFLICT (language, term, source) DO UPDATE",
    ],
    DOC: [
        "single-click/single-tap on an English word",
        "lookup must fall back to the general dictionary",
    ],
    IMPORT_SCRIPT: [
        "sys.path.insert(0, str(ROOT))",
        "def import_ecdict",
        "ON CONFLICT (language, term, source) DO UPDATE",
    ],
}


def main() -> int:
    missing_files = [str(path) for path in REQUIRED if not path.exists()]
    missing_markers: dict[str, list[str]] = {}
    for path, markers in REQUIRED.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            missing_markers[str(path)] = missing
    if missing_files or missing_markers:
        print(f"vocab lookup static FAIL missing_files={missing_files} missing_markers={missing_markers}")
        return 1
    print("vocab lookup static PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
