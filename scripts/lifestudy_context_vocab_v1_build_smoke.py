#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_context_vocab_v1_build.py"
REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_vocab_v1_review_pack.json"
IMPORTABLE = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_vocab_v1_importable.json"


def fail(message: str) -> int:
    print(f"lifestudy context vocab v1 build smoke FAIL: {message}")
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
    review = json.loads(REPORT.read_text(encoding="utf-8"))
    if review.get("schema") != "sentence_reader.lifestudy_context_vocab_v1_review_pack.v1":
        return fail(f"unexpected review schema: {review.get('schema')}")
    if review.get("database_write_performed") is not False:
        return fail("review pack must be no-write")
    quality = review.get("quality") or {}
    if quality.get("top_queue_count") != 500:
        return fail(f"expected top500 queue, got {quality.get('top_queue_count')}")
    if quality.get("auto_reviewed_import_ready_count", 0) < 20:
        return fail(f"expected useful auto-reviewed items, got {quality.get('auto_reviewed_import_ready_count')}")
    missing = set(quality.get("required_top_words_missing") or [])
    if missing:
        return fail(f"required top words missing: {sorted(missing)}")
    items = {item.get("term"): item for item in review.get("items") or []}
    for term, meaning in {"economy": "经纶", "dispensing": "分赐", "mingled": "调和"}.items():
        item = items.get(term)
        if not item:
            return fail(f"missing required item: {term}")
        if item.get("candidate_meaning_zh_simp") != meaning:
            return fail(f"wrong meaning for {term}: {item.get('candidate_meaning_zh_simp')}")
        if not item.get("evidence_en") or not item.get("evidence_zh_simp"):
            return fail(f"missing evidence for {term}")
    importable = json.loads(IMPORTABLE.read_text(encoding="utf-8"))
    if importable.get("schema") != "sentence_reader.lifestudy_context_vocab_v1_importable.v1":
        return fail(f"unexpected importable schema: {importable.get('schema')}")
    if importable.get("database_write_performed") is not False:
        return fail("importable pack must be no-write")
    print(
        "lifestudy context vocab v1 build smoke PASS "
        f"top={quality.get('top_queue_count')} "
        f"import_ready={quality.get('auto_reviewed_import_ready_count')} "
        f"needs_review={quality.get('needs_review_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
