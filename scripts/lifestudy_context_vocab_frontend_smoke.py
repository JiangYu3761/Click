#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "reader_api" / "app.py"
SWIFT = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"


def main() -> int:
    missing_files = [str(path) for path in (APP, SWIFT) if not path.exists()]
    missing_markers: dict[str, list[str]] = {}
    required = {
        APP: [
            "def normalize_vocab_lookup_text",
            "def vocab_lookup_terms",
            "normalized_lookup",
            "lower(bvi.surface) = ANY(%s::text[])",
            "regexp_replace(lower(bvi.surface), '[^a-z]', '', 'g')",
            "len(normalized_lookup.split()) <= 1",
        ],
        SWIFT: [
            "selectedEnglishWord()",
            "replace(/\\\\s+/g, ' ')",
            "/^[A-Za-z][A-Za-z' -]{0,96}[A-Za-z]$/",
            "post({ type: 'lookup'",
        ],
    }
    for path, markers in required.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            missing_markers[str(path)] = missing
    if missing_files or missing_markers:
        print(f"lifestudy context vocab frontend smoke FAIL missing_files={missing_files} missing_markers={missing_markers}")
        return 1
    print("lifestudy context vocab frontend smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
