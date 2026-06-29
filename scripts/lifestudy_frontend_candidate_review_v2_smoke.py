#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_frontend_candidate_review_v2.py"
BASE = ROOT / "reports" / "lifestudy_vocab_corpus"
SUMMARY = BASE / "lifestudy_frontend_candidate_review_v2_summary.json"
APPROVE = BASE / "lifestudy_frontend_candidate_review_v2_approve_after_human_check.csv"
TEMPLATE = BASE / "lifestudy_frontend_candidate_review_v2_overrides_template.json"


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def ensure_report() -> int:
    if SUMMARY.exists() and APPROVE.exists() and TEMPLATE.exists():
        return 0
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        return fail(proc.stderr.strip() or proc.stdout.strip() or "frontend candidate review failed")
    return 0


def main() -> int:
    rc = ensure_report()
    if rc:
        return rc
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if summary.get("database_write_performed") is not False:
        return fail("frontend candidate review must be no-write")
    quality = summary.get("quality") or {}
    if quality.get("front_end_import_ready_count") != 0:
        return fail("frontend candidate review must not mark rows import-ready")
    rows = list(csv.DictReader(APPROVE.open(encoding="utf-8-sig")))
    if len(rows) != 28:
        return fail(f"expected 28 approve-after-human-check candidates, got {len(rows)}")
    by_word = {row["word"]: row for row in rows}
    for word in ["salvation", "grace", "glory", "anointing", "priesthood", "sanctuary", "consecration"]:
        if word not in by_word:
            return fail(f"missing domain candidate: {word}")
    for word in ["matter", "therefore", "actually", "person", "however"]:
        if word in by_word:
            return fail(f"generic word should not be in approve-after-human-check candidates: {word}")
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    if template.get("database_write_performed") is not False:
        return fail("override template must be no-write")
    if any(item.get("front_end_import_ready") is not False for item in template.get("items") or []):
        return fail("override template must keep front_end_import_ready false")
    print("lifestudy frontend candidate review v2 smoke PASS rows=28 import_ready=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
