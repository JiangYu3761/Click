#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_dictionary_guided_review_v2.py"
REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_dictionary_guided_review_v2.csv"
SUMMARY = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_dictionary_guided_review_v2_summary.json"


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def ensure_report() -> int:
    if REPORT.exists() and SUMMARY.exists():
        return 0
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        return fail(proc.stderr.strip() or proc.stdout.strip() or "review v2 build failed")
    return 0


def main() -> int:
    rc = ensure_report()
    if rc:
        return rc
    rows = list(csv.DictReader(REPORT.open(encoding="utf-8-sig")))
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if summary.get("database_write_performed") is not False:
        return fail("review v2 must be no-write")
    if len(rows) != 6321:
        return fail(f"expected 6321 dictionary-guided rows, got {len(rows)}")
    decisions = Counter(row["learning_review_decision"] for row in rows)
    if decisions.get("auto_accept_learning_candidate", 0) < 4000:
        return fail(f"auto accepted learning candidates too low: {decisions}")
    if any(str(row.get("front_end_import_ready")) == "True" for row in rows):
        return fail("review v2 must not mark rows as frontend import-ready")
    by_word = {row["word"]: row for row in rows}
    expected_accept = {
        "love": "爱",
        "world": "世界",
        "wonderful": "奇妙",
    }
    for word, meaning in expected_accept.items():
        row = by_word.get(word)
        if not row:
            return fail(f"missing expected review row: {word}")
        if row["learning_review_decision"] != "auto_accept_learning_candidate":
            return fail(f"{word} should be auto accepted for learning: {row['learning_review_decision']}")
        if meaning not in row["reviewed_meaning_zh_simp"]:
            return fail(f"{word} expected meaning {meaning}, got {row['reviewed_meaning_zh_simp']}")
    for word in ("things", "message", "holy"):
        row = by_word.get(word)
        if not row:
            return fail(f"missing expected manual review row: {word}")
        if row["learning_review_decision"] != "needs_manual_review":
            return fail(f"{word} should remain manual review: {row['learning_review_decision']}")
    print(
        "lifestudy dictionary-guided review v2 smoke PASS "
        f"rows={len(rows)} auto_accept={decisions.get('auto_accept_learning_candidate', 0)} "
        f"needs_review={decisions.get('needs_manual_review', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
