#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_context_vocab_word_review_pack.py"
REPORT = ROOT / "reports" / "lifestudy_vocab_review" / "Genesis-word-review-pack.json"


def fail(message: str) -> int:
    print(f"lifestudy context vocab word review pack smoke FAIL: {message}")
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
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_single_word_review_pack.v1":
        return fail(f"unexpected schema: {payload.get('schema')}")
    if payload.get("database_write_performed") is not False:
        return fail("single word review pack must not write database")
    quality = payload.get("quality") or {}
    if quality.get("word_candidate_count") != 34:
        return fail(f"expected 34 word candidates, got {quality.get('word_candidate_count')}")
    if quality.get("import_ready_count") != 0:
        return fail("single word pack must not mark words import-ready before review")
    items = {item.get("term"): item for item in payload.get("items") or []}
    for term, meaning in {"economy": "经纶", "dispensing": "分赐", "church": "召会", "transformation": "变化"}.items():
        if (items.get(term) or {}).get("suggested_meaning_zh_simp") != meaning:
            return fail(f"missing expected suggestion {term} => {meaning}")
    print(
        "lifestudy context vocab word review pack smoke PASS "
        f"words={quality.get('word_candidate_count')} suggestions={quality.get('suggested_meaning_count')} no_db_write=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
