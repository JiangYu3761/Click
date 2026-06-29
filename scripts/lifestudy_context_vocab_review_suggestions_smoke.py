#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_context_vocab_review_suggestions.py"
OUTPUT_DIR = ROOT / "reports" / "lifestudy_vocab_review"


def fail(message: str) -> int:
    print(f"lifestudy context vocab review suggestions smoke FAIL: {message}")
    return 1


def main() -> int:
    if not SCRIPT.exists():
        return fail(f"missing script: {SCRIPT}")
    source = SCRIPT.read_text(encoding="utf-8")
    markers = [
        "sentence_reader.lifestudy_vocab_review_suggestions.v1",
        "assistant_suggestions_not_human_review",
        "database_write_performed",
        "Genesis-review-overrides.assistant-suggested.json",
        "light and darkness",
    ]
    missing = [marker for marker in markers if marker not in source]
    if missing:
        return fail(f"missing static markers: {missing}")
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    summary = json.loads(proc.stdout)
    quality = summary.get("quality") or {}
    if quality.get("term_count") != 25:
        return fail(f"expected 25 suggestions, got {quality.get('term_count')}")
    if quality.get("human_reviewed_precision") is not None:
        return fail("suggestions must not claim human-reviewed precision")
    if quality.get("suggested_decision_counts", {}).get("correct") != 1:
        return fail(f"expected one suggested correction, got {quality.get('suggested_decision_counts')}")
    if summary.get("assistant_suggested_dry_run", {}).get("database_write_performed") is not False:
        return fail("suggested dry-run must not write database")
    dry_run = summary.get("assistant_suggested_dry_run", {}).get("result") or {}
    if dry_run.get("can_expand_next_volume") is not True:
        return fail(f"assistant suggested overrides should pass dry-run threshold, got {dry_run}")
    for name in [
        "Genesis-review-suggestions.json",
        "Genesis-review-suggestions.md",
        "Genesis-review-overrides.assistant-suggested.json",
    ]:
        path = OUTPUT_DIR / name
        if not path.exists() or path.stat().st_size <= 0:
            return fail(f"missing output: {path}")
    print("lifestudy context vocab review suggestions smoke PASS suggestions=25 dry_run_can_expand=true no_db_write=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
