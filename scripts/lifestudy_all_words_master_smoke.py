#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_all_words_master.py"
REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_all_words_master_smoke.json"
CSV_REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_all_words_master_smoke.csv"


def fail(message: str) -> int:
    print(f"lifestudy all words master smoke FAIL: {message}")
    return 1


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--volumes", "01,02,03", "--output-stem", "lifestudy_all_words_master_smoke"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        return fail(proc.stderr.strip() or proc.stdout.strip())
    if not REPORT.exists():
        return fail(f"missing JSON report: {REPORT}")
    if not CSV_REPORT.exists():
        return fail(f"missing CSV report: {CSV_REPORT}")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_all_words_master.v1":
        return fail(f"unexpected schema: {payload.get('schema')}")
    if payload.get("database_write_performed") is not False:
        return fail("all words master must be no-write")
    quality = payload.get("quality") or {}
    if quality.get("source_volume_count") != 3:
        return fail(f"expected 3 smoke source volumes, got {quality.get('source_volume_count')}")
    if quality.get("unique_word_count", 0) < 5000:
        return fail(f"expected real all-word table, got only {quality.get('unique_word_count')} unique words")
    items = payload.get("items") or []
    row_by_word = {row.get("word"): row for row in items}
    for word in ("god", "life", "spirit", "the"):
        if word not in row_by_word:
            return fail(f"missing expected word: {word}")
        if not row_by_word[word].get("sources"):
            return fail(f"missing sources for word: {word}")
    if row_by_word["the"].get("is_content_word") is not False:
        return fail("stopword 'the' should be present but not marked as a content word")
    if not row_by_word["life"].get("sample_zh_contexts", None) and not row_by_word["life"].get("sources"):
        return fail("life should have source evidence")
    print(
        "lifestudy all words master smoke PASS "
        f"source_volumes={quality.get('source_volume_count')} "
        f"unique_words={quality.get('unique_word_count')} "
        f"raw_tokens={quality.get('raw_word_token_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
