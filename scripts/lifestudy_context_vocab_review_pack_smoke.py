#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_context_vocab_review_pack.py"
IMPORTABLE = ROOT / "reports" / "lifestudy_vocab_pipeline" / "01_Genesis-120-pages-1-1255-importable.json"
BOOK_ID = "book_e0679064039e4e298e9faf3127b65876"


def fail(message: str) -> int:
    print(f"lifestudy context vocab review pack smoke FAIL: {message}")
    return 1


def main() -> int:
    if not SCRIPT.exists():
        return fail(f"missing script: {SCRIPT}")
    if not IMPORTABLE.exists():
        return fail(f"missing importable report: {IMPORTABLE}")
    source = SCRIPT.read_text(encoding="utf-8")
    markers = [
        "sentence_reader.lifestudy_vocab_review_pack.v1",
        "sentence_reader.lifestudy_vocab_review_overrides.v1",
        "database_write_performed",
        "can_expand_next_volume",
        "human_review_pending_count",
        "dictionary_pollution_count",
        "source='user'",
    ]
    missing = [marker for marker in markers if marker not in source]
    if missing:
        return fail(f"missing static markers: {missing}")

    tmp_ctx = tempfile.TemporaryDirectory(prefix="lifestudy-review-pack-smoke-")
    output_dir = Path(tmp_ctx.name)
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(IMPORTABLE),
            "--book-id",
            BOOK_ID,
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    summary = json.loads(proc.stdout)
    quality = summary.get("quality") or {}
    if quality.get("term_count") != 25:
        return fail(f"expected 25 terms, got {quality.get('term_count')}")
    if quality.get("grade_counts") != {"A": 19, "B": 6}:
        return fail(f"unexpected grade counts: {quality.get('grade_counts')}")
    if quality.get("database_write_performed") is not None:
        return fail("summary quality should not carry database_write_performed")
    if quality.get("human_review_pending_count") != 25:
        return fail(f"expected 25 pending human reviews, got {quality.get('human_review_pending_count')}")
    if quality.get("can_expand_next_volume") is not False:
        return fail("review pack without overrides must block next-volume expansion")
    if quality.get("missing_book_row_count") != 0:
        return fail(f"book import rows missing: {quality.get('missing_book_row_count')}")
    if quality.get("dictionary_pollution_count") != 0:
        return fail(f"dictionary pollution detected: {quality.get('dictionary_pollution_count')}")

    report_path = Path(summary["outputs"]["json"])
    csv_path = Path(summary["outputs"]["csv"])
    markdown_path = Path(summary["outputs"]["markdown"])
    template_path = Path(summary["outputs"]["override_template"])
    for path in (report_path, csv_path, markdown_path, template_path):
        if not path.exists() or path.stat().st_size <= 0:
            return fail(f"missing output: {path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("database_write_performed") is not False:
        return fail("review report must not write database")
    if any(item.get("quality_grade") not in {"A", "B"} for item in report.get("items") or []):
        return fail("review report included non-A/B item")
    if not all(item.get("evidence_en") and item.get("evidence_zh_simp") for item in report.get("items") or []):
        return fail("review report has item without bilingual evidence")
    template = json.loads(template_path.read_text(encoding="utf-8"))
    if template.get("schema") != "sentence_reader.lifestudy_vocab_review_overrides.v1":
        return fail(f"unexpected override template schema: {template.get('schema')}")
    print(
        "lifestudy context vocab review pack smoke PASS "
        f"terms={quality.get('term_count')} pending={quality.get('human_review_pending_count')} outputs=temp"
    )
    tmp_ctx.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
