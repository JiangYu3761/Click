#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_all_words_chinese_context_candidates.csv"
SUMMARY = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_all_words_chinese_context_candidates_summary.json"
SCRIPT = ROOT / "scripts" / "lifestudy_all_words_chinese_context_candidates.py"


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if not REPORT.exists() or not SUMMARY.exists():
        proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            return fail(proc.stderr.strip() or proc.stdout.strip() or "candidate build failed")
    rows = list(csv.DictReader(REPORT.open(encoding="utf-8-sig")))
    if len(rows) < 30000:
        return fail(f"expected full all-word candidate table, got {len(rows)} rows")
    by_word = {row["word"]: row for row in rows}
    expected = {
        "love": "爱",
        "world": "世界",
        "wonderful": "奇妙",
        "economy": "经纶",
        "dispensing": "分赐",
        "mingled": "调和",
    }
    for word, expected_zh in expected.items():
        row = by_word.get(word)
        if not row:
            return fail(f"missing word: {word}")
        if expected_zh not in row.get("draft_meaning_zh_from_chinese_context", ""):
            return fail(f"{word} expected {expected_zh}, got {row.get('draft_meaning_zh_from_chinese_context')}")
        if not row.get("evidence_zh_simp"):
            return fail(f"{word} has no Chinese evidence")
    counts = Counter(row["candidate_source"] for row in rows)
    if counts.get("dictionary_guided_term_found_in_chinese_context", 0) < 5000:
        return fail(f"dictionary-guided Chinese-context candidates too low: {counts}")
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if summary.get("database_write_performed") is not False:
        return fail("summary must remain no-write")
    print(
        "lifestudy all words chinese context candidates smoke PASS "
        f"rows={len(rows)} dictionary_guided={counts.get('dictionary_guided_term_found_in_chinese_context', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
