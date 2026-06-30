#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import urllib.parse
import urllib.request


BASE = "http://127.0.0.1:18180"
LIFESTUDY_BOOK_ID = "book_e0679064039e4e298e9faf3127b65876"
ORDINARY_BOOK_ID = "book_e741998932344f15a239df571593c11d"


def fail(message: str) -> int:
    print(f"lifestudy context vocab v1 live lookup smoke FAIL: {message}")
    return 1


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def lookup(book_id: str, word: str) -> dict:
    url = f"{BASE}/books/{book_id}/lookup?word={urllib.parse.quote(word)}"
    return fetch_json(url)


def main() -> int:
    try:
        health = fetch_json(f"{BASE}/health")
    except Exception as exc:
        return fail(f"Reader API is not reachable: {exc}")
    if not health.get("ok"):
        return fail(f"Reader API health is not ok: {health}")

    expected = {"economy": "经纶", "dispensing": "分赐", "mingled": "调和"}
    for word, meaning in expected.items():
        payload = lookup(LIFESTUDY_BOOK_ID, word)
        item = payload.get("item") or {}
        if item.get("meaning_source") != "lifestudy_domain_glossary":
            return fail(f"{word} did not use Life-study glossary: {item.get('meaning_source')}")
        if item.get("context_meaning_zh") != meaning:
            return fail(f"{word} meaning mismatch: {item.get('context_meaning_zh')} != {meaning}")
        metadata = item.get("metadata") or {}
        if metadata.get("source_page") is None or metadata.get("quality_grade") != "A":
            return fail(f"{word} missing source page or A-grade metadata: {metadata}")

    ordinary = lookup(ORDINARY_BOOK_ID, "economy")
    ordinary_item = ordinary.get("item") or {}
    if ordinary_item.get("meaning_source") == "lifestudy_domain_glossary":
        return fail("ordinary book was polluted by Life-study glossary")

    print("lifestudy context vocab v1 live lookup smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
