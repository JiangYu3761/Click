#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "scripts" / "lifestudy_context_vocab_pipeline.py"
OUTPUT_DIR = ROOT / "reports" / "lifestudy_vocab_pipeline_smoke"
SOURCE_PDF = Path(
    os.getenv(
        "LIFESTUDY_GENESIS_BILINGUAL_PDF",
        str(ROOT / "private_data" / "lifestudy" / "bilingual" / "01_Genesis(120).pdf"),
    )
)


def fail(message: str) -> int:
    print(f"lifestudy context vocab pipeline smoke FAIL: {message}")
    return 1


def main() -> int:
    if not PIPELINE.exists():
        return fail(f"missing pipeline script: {PIPELINE}")
    if not SOURCE_PDF.exists():
        return fail(f"missing Genesis bilingual PDF: {SOURCE_PDF}")

    source = PIPELINE.read_text(encoding="utf-8")
    static_markers = [
        'OpenCC("t2s")',
        '"quality_grade"',
        '"import_allowed"',
        '"database_write_performed": False',
        '"can_advance_to_genesis_full"',
        "missing coordinator in OCR phrase",
    ]
    missing = [marker for marker in static_markers if marker not in source]
    if missing:
        return fail(f"missing static markers: {missing}")

    forbidden = ["INSERT INTO", "UPDATE reader.", "DELETE FROM reader.", "psycopg.connect", "db.connect"]
    leaked = [marker for marker in forbidden if marker in source]
    if leaked:
        return fail(f"pipeline must not write database, found: {leaked}")

    subprocess.run(
        [
            sys.executable,
            str(PIPELINE),
            str(SOURCE_PDF),
            "--pages",
            "6",
            "--limit",
            "0",
            "--output-dir",
            str(OUTPUT_DIR),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    report = OUTPUT_DIR / "01_Genesis-120-pages-1-6-pipeline.json"
    importable = OUTPUT_DIR / "01_Genesis-120-pages-1-6-importable.json"
    if not report.exists() or not importable.exists():
        return fail("pipeline did not create expected JSON reports")

    payload = json.loads(report.read_text(encoding="utf-8"))
    importable_payload = json.loads(importable.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_vocab_pipeline.v1":
        return fail(f"bad report schema: {payload.get('schema')}")
    if importable_payload.get("schema") != "sentence_reader.lifestudy_vocab_importable.v1":
        return fail(f"bad importable schema: {importable_payload.get('schema')}")
    if payload.get("simplified_converter") != "opencc:t2s" or payload.get("simplified_converter_degraded"):
        return fail(f"OpenCC did not run cleanly: {payload.get('simplified_converter')}")

    quality = payload.get("quality") or {}
    counts = quality.get("quality_grade_counts") or {}
    for grade in ("A", "B", "C", "D"):
        if grade not in counts:
            return fail(f"missing grade count: {grade}")
    if quality.get("database_write_performed") is not False or importable_payload.get("database_write_performed") is not False:
        return fail("report claims database write happened")

    candidates = payload.get("candidates") or []
    importable_items = payload.get("importable_candidates") or []
    for item in importable_items:
        if item.get("quality_grade") not in {"A", "B"}:
            return fail(f"C/D item leaked into importable list: {item}")
        if item.get("import_allowed") is not True or item.get("ui_visible") is not True:
            return fail(f"importable item missing import/ui flags: {item}")
        for key in ("evidence_en", "evidence_zh_simp", "source_page", "reason", "suggested_meaning_zh_simp"):
            if item.get(key) in (None, ""):
                return fail(f"importable item missing evidence field {key}: {item}")
    if any(item.get("term") == "light darkness" for item in importable_items):
        return fail("OCR-damaged phrase leaked into importable list")
    if any(item.get("term") == "light darkness" and item.get("quality_grade") != "D" for item in candidates):
        return fail("OCR-damaged phrase was not discarded")

    print(
        "lifestudy context vocab pipeline smoke PASS "
        f"candidates={quality.get('candidate_count')} "
        f"importable={quality.get('importable_candidate_count')} "
        f"grades={counts}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
