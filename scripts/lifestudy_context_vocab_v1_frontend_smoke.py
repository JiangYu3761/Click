#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "reader_api" / "app.py"


def fail(message: str) -> int:
    print(f"lifestudy context vocab v1 frontend smoke FAIL: {message}")
    return 1


def main() -> int:
    text = APP.read_text(encoding="utf-8")
    required = [
        "lifestudy_enabled = book_lifestudy_domain_enabled(conn, book_id)",
        "domain_item = find_domain_glossary_entry(conn, book_id, lookup_terms, clean_word)",
        'current_source in {"none", "dictionary_fallback"}',
        "current_alignment == \"dictionary_fallback\"",
        "item_payload = domain_item",
    ]
    for marker in required:
        if marker not in text:
            return fail(f"missing marker: {marker}")
    domain_lookup_pos = text.find("domain_item = find_domain_glossary_entry")
    dictionary_pos = text.find("dictionary = find_dictionary_entry", domain_lookup_pos)
    if domain_lookup_pos < 0 or dictionary_pos < 0 or domain_lookup_pos > dictionary_pos:
        return fail("Life-study domain lookup must be checked before dictionary fallback creation")
    print("lifestudy context vocab v1 frontend smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
