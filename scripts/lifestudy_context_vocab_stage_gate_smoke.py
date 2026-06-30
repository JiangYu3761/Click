#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_context_vocab_stage_gate.py"
REPORT = ROOT / "reports" / "lifestudy_vocab_review" / "Genesis-stage-gate.json"


def fail(message: str) -> int:
    print(f"lifestudy context vocab stage gate smoke FAIL: {message}")
    return 1


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        return fail(proc.stderr.strip() or proc.stdout.strip())
    if not REPORT.exists():
        return fail("stage gate report was not written")
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("schema") != "sentence_reader.lifestudy_vocab_stage_gate.v1":
        return fail(f"unexpected schema: {report.get('schema')}")
    if report.get("database_write_performed") is not False:
        return fail("stage gate must not write database")
    stages = {item["name"]: item for item in report.get("stages") or []}
    for required in [
        "genesis_first_50",
        "genesis_full_run",
        "controlled_import",
        "frontend_lookup",
        "genesis_single_word_review_pack",
        "genesis_word_frequency_report",
        "genesis_phrase_uncommon_pack",
        "genesis_review_gate",
    ]:
        if required not in stages:
            return fail(f"missing stage: {required}")
    if not stages["genesis_first_50"].get("passed"):
        return fail("first 50 pages should already pass")
    if not stages["genesis_full_run"].get("passed"):
        return fail("Genesis full run should already pass")
    if not stages["controlled_import"].get("passed"):
        return fail("controlled import should already pass")
    if not stages["frontend_lookup"].get("passed"):
        return fail("frontend lookup should already pass")
    if not stages["genesis_single_word_review_pack"].get("passed"):
        return fail("single word review pack should already pass")
    if not stages["genesis_word_frequency_report"].get("passed"):
        return fail("word frequency report should already pass")
    if not stages["genesis_phrase_uncommon_pack"].get("passed"):
        return fail("phrase/uncommon pack should already pass")
    review_metrics = stages["genesis_review_gate"].get("metrics") or {}
    if not stages["genesis_review_gate"].get("passed"):
        return fail("Genesis review gate should pass after reviewed overrides are approved")
    if review_metrics.get("decision_counts", {}).get("pending") != 0:
        return fail(f"expected 0 pending reviewed decisions, got {review_metrics.get('decision_counts')}")
    if review_metrics.get("decision_counts", {}).get("approve") != 25:
        return fail(f"expected 25 approved reviewed decisions, got {review_metrics.get('decision_counts')}")
    if review_metrics.get("human_reviewed_precision") != 1:
        return fail(f"expected reviewed precision 1, got {review_metrics.get('human_reviewed_precision')}")
    if report.get("can_expand_next_volume") is not True:
        return fail("stage gate should allow next-volume probe after approved review")
    if review_metrics.get("assistant_suggested_dry_run_can_expand") is not True:
        return fail("assistant suggested dry-run should pass as a suggestion-only preflight")
    if review_metrics.get("single_word_review_pending_count") != 34:
        return fail(f"expected 34 pending single-word candidates, got {review_metrics.get('single_word_review_pending_count')}")
    if review_metrics.get("word_frequency_content_unique_count", 0) < 9000:
        return fail(f"expected at least 9000 content words, got {review_metrics.get('word_frequency_content_unique_count')}")
    if review_metrics.get("phrase_uncommon_total_count", 0) < 200:
        return fail(f"expected at least 200 phrase/uncommon items, got {review_metrics.get('phrase_uncommon_total_count')}")
    print("lifestudy context vocab stage gate smoke PASS current_stage=ready_for_next_volume_probe no_db_write=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
