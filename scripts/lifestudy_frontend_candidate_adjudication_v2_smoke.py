#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_frontend_candidate_adjudication_v2.py"
BASE = ROOT / "reports" / "lifestudy_vocab_corpus"
SUMMARY = BASE / "lifestudy_frontend_candidate_adjudication_v2_summary.json"
CSV = BASE / "lifestudy_frontend_candidate_adjudication_v2.csv"
READY_CSV = BASE / "lifestudy_frontend_candidate_adjudication_v2_ready_for_dry_run.csv"


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def ensure_report() -> int:
    if SUMMARY.exists() and CSV.exists() and READY_CSV.exists():
        return 0
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        return fail(proc.stderr.strip() or proc.stdout.strip() or "adjudication failed")
    return 0


def main() -> int:
    rc = ensure_report()
    if rc:
        return rc
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if summary.get("database_write_performed") is not False:
        return fail("adjudication must be no-write")
    quality = summary.get("quality") or {}
    if quality.get("source_rows") != 28:
        return fail(f"expected 28 source rows, got {quality.get('source_rows')}")
    if quality.get("front_end_candidate_ready_count") != 26:
        return fail(f"expected 26 ready candidates, got {quality.get('front_end_candidate_ready_count')}")
    if quality.get("front_end_import_ready_count") != 0:
        return fail("adjudication must not mark rows import-ready")

    rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig")))
    by_word = {row["word"]: row for row in rows}
    expected = {
        "redemption": ("correct", "救赎", "true"),
        "righteousness": ("correct", "公义", "true"),
        "reality": ("correct", "实际", "true"),
        "anointing": ("correct", "受膏；膏油的涂抹", "true"),
        "priesthood": ("correct", "祭司职分", "true"),
        "living": ("learning_only", "生活", "false"),
        "sacrifice": ("needs_more_evidence", "牺牲", "false"),
    }
    for word, (decision, meaning, ready) in expected.items():
        row = by_word.get(word)
        if not row:
            return fail(f"missing adjudicated word: {word}")
        if row.get("codex_adjudication") != decision:
            return fail(f"{word} decision mismatch: {row.get('codex_adjudication')} != {decision}")
        if row.get("final_meaning_zh_simp") != meaning:
            return fail(f"{word} meaning mismatch: {row.get('final_meaning_zh_simp')} != {meaning}")
        if row.get("front_end_candidate_ready") != ready:
            return fail(f"{word} ready mismatch: {row.get('front_end_candidate_ready')} != {ready}")
    if any(row.get("front_end_import_ready") != "false" for row in rows):
        return fail("all rows must keep front_end_import_ready=false")

    ready_rows = list(csv.DictReader(READY_CSV.open(encoding="utf-8-sig")))
    if len(ready_rows) != 26:
        return fail(f"expected 26 ready rows, got {len(ready_rows)}")
    if any(row.get("word") in {"living", "sacrifice"} for row in ready_rows):
        return fail("living/sacrifice must not be in ready-for-dry-run CSV")
    print("lifestudy frontend candidate adjudication v2 smoke PASS rows=28 ready=26 import_ready=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
