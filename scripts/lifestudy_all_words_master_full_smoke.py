#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_all_words_master.json"
CSV_REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_all_words_master.csv"


def fail(message: str) -> int:
    print(f"lifestudy all words master full smoke FAIL: {message}")
    return 1


def main() -> int:
    if not REPORT.exists():
        return fail(f"missing full JSON report: {REPORT}")
    if not CSV_REPORT.exists():
        return fail(f"missing full CSV report: {CSV_REPORT}")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_all_words_master.v1":
        return fail(f"unexpected schema: {payload.get('schema')}")
    if payload.get("database_write_performed") is not False:
        return fail("full all-word master must be no-write")
    quality = payload.get("quality") or {}
    if quality.get("source_volume_count") != 51:
        return fail(f"expected all 51 processable volumes, got {quality.get('source_volume_count')}")
    if quality.get("unique_word_count", 0) < 30000:
        return fail(f"expected full-corpus word table, got {quality.get('unique_word_count')} unique words")
    if quality.get("raw_word_token_count", 0) < 5000000:
        return fail(f"expected full-corpus token count, got {quality.get('raw_word_token_count')}")
    items = payload.get("items") or []
    words = {item.get("word") for item in items}
    for word in ("god", "life", "christ", "spirit", "the"):
        if word not in words:
            return fail(f"missing expected full-corpus word: {word}")
    print(
        "lifestudy all words master full smoke PASS "
        f"source_volumes={quality.get('source_volume_count')} "
        f"unique_words={quality.get('unique_word_count')} "
        f"raw_tokens={quality.get('raw_word_token_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
