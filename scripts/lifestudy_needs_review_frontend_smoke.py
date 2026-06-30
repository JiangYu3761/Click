#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE_SCRIPT = ROOT / "scripts" / "lifestudy_needs_review_frontend_queue.py"
ADJ_SCRIPT = ROOT / "scripts" / "lifestudy_needs_review_frontend_adjudication.py"
APPLY_SCRIPT = ROOT / "scripts" / "lifestudy_needs_review_frontend_apply.py"
BASE = ROOT / "reports" / "lifestudy_vocab_corpus"
QUEUE_SUMMARY = BASE / "lifestudy_needs_review_frontend_queue_summary.json"
ADJ_SUMMARY = BASE / "lifestudy_needs_review_frontend_adjudication_summary.json"
READY = BASE / "lifestudy_needs_review_frontend_ready_for_dry_run.csv"


def fail(message: str) -> int:
    print(f"lifestudy needs-review frontend smoke FAIL: {message}", file=sys.stderr)
    return 1


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    for script in (QUEUE_SCRIPT, ADJ_SCRIPT):
        code, stdout, stderr = run([sys.executable, str(script)])
        if code != 0:
            return fail(stderr.strip() or stdout.strip())

    queue_summary = json.loads(QUEUE_SUMMARY.read_text(encoding="utf-8"))
    queue_quality = queue_summary.get("quality") or {}
    if queue_summary.get("database_write_performed") is not False:
        return fail("queue stage must be no-write")
    if queue_quality.get("source_corrected_rows") != 3 or queue_quality.get("source_learning_rows") != 2197:
        return fail(f"queue read wrong source split: {queue_quality}")
    if queue_quality.get("excluded_reject_rows") != 5 or queue_quality.get("excluded_still_rows") != 0:
        return fail(f"queue exclusion counts wrong: {queue_quality}")
    if queue_quality.get("queue_rows") != 300:
        return fail(f"expected Top300 queue, got {queue_quality.get('queue_rows')}")
    if queue_quality.get("front_end_import_ready_count") != 0:
        return fail("queue must not mark import-ready")

    adj_summary = json.loads(ADJ_SUMMARY.read_text(encoding="utf-8"))
    adj_quality = adj_summary.get("quality") or {}
    if adj_summary.get("database_write_performed") is not False:
        return fail("adjudication stage must be no-write")
    if adj_quality.get("reviewed_rows") != 300:
        return fail(f"adjudication must review 300 rows, got {adj_quality.get('reviewed_rows')}")
    ready_count = int(adj_quality.get("front_end_candidate_ready_count") or 0)
    if ready_count <= 0 or ready_count >= 2205:
        return fail(f"ready count must be selective, got {ready_count}")
    if adj_quality.get("front_end_import_ready_count") != 0:
        return fail("adjudication must not mark import-ready")

    rows = list(csv.DictReader(READY.open(encoding="utf-8-sig")))
    if len(rows) != ready_count:
        return fail(f"ready CSV count mismatch: {len(rows)} != {ready_count}")
    for row in rows:
        if row.get("frontend_adjudication") not in {"frontend_ready", "frontend_corrected"}:
            return fail(f"invalid ready decision: {row.get('word')} {row.get('frontend_adjudication')}")
        if row.get("front_end_import_ready") != "false":
            return fail(f"ready rows must still not be import-ready: {row.get('word')}")
        if row.get("database_write_performed") != "false":
            return fail(f"ready rows must be no-write: {row.get('word')}")
        meaning = row.get("final_meaning_zh_simp") or ""
        if not meaning or any(part.strip() and part.strip() not in (row.get("evidence_zh_simp") or "") for part in meaning.replace("/", "；").split("；")):
            return fail(f"ready meaning not supported by Chinese evidence: {row.get('word')} -> {meaning}")

    code, stdout, stderr = run([sys.executable, str(APPLY_SCRIPT)])
    if code != 0:
        return fail(stderr.strip() or stdout.strip())
    payload = json.loads(stdout)
    if payload.get("mode") != "dry_run":
        return fail(f"apply must default to dry-run, got {payload.get('mode')}")
    if payload.get("database_write_performed") is not False:
        return fail("dry-run must not write database")
    if payload.get("target") != "reader.domain_glossary_entries":
        return fail(f"unexpected apply target: {payload.get('target')}")
    if payload.get("candidate_count") != ready_count:
        return fail(f"apply candidate count mismatch: {payload.get('candidate_count')} != {ready_count}")
    pollution = (payload.get("preflight") or {}).get("dictionary_pollution_count")
    if pollution != 0:
        return fail(f"general dictionary pollution detected: {pollution}")

    print(
        "lifestudy needs-review frontend smoke PASS "
        f"queue=300 ready={ready_count} dry_run_candidates={payload.get('candidate_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
