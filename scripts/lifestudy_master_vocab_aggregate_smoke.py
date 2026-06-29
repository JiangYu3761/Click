#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_SCRIPT = ROOT / "scripts" / "lifestudy_corpus_inventory.py"
AGGREGATE_SCRIPT = ROOT / "scripts" / "lifestudy_master_vocab_aggregate.py"
REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_master_vocab.json"
CSV_REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_master_vocab.csv"
MD_REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_master_vocab.md"


def fail(message: str) -> int:
    print(f"lifestudy master vocab aggregate smoke FAIL: {message}")
    return 1


def run_script(path: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.returncode, proc.stderr.strip() or proc.stdout.strip()


def main() -> int:
    for script in (INVENTORY_SCRIPT, AGGREGATE_SCRIPT):
        code, output = run_script(script)
        if code != 0:
            return fail(output)

    if not REPORT.exists():
        return fail(f"missing JSON report: {REPORT}")
    if not CSV_REPORT.exists():
        return fail(f"missing CSV report: {CSV_REPORT}")
    if not MD_REPORT.exists():
        return fail(f"missing Markdown report: {MD_REPORT}")

    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_master_vocab.v1":
        return fail(f"unexpected schema: {payload.get('schema')}")
    if payload.get("database_write_performed") is not False:
        return fail("master aggregate must be report-only and no-write")

    quality = payload.get("quality") or {}
    if quality.get("source_volume_count", 0) < 3:
        return fail(f"expected at least Genesis/Exodus/Leviticus sources, got {quality.get('source_volume_count')}")
    if quality.get("source_entry_count", 0) < 50:
        return fail(f"expected aggregated source entries, got {quality.get('source_entry_count')}")
    if quality.get("unique_term_count", 0) < 20:
        return fail(f"expected useful unique terms, got {quality.get('unique_term_count')}")

    items = payload.get("items") or []
    if not items:
        return fail("master aggregate has no vocabulary items")
    if not any((source.get("volume_index") == "03") for item in items for source in item.get("sources", [])):
        return fail("Leviticus sources are not present in the master aggregate")
    for item in items[:10]:
        sources = item.get("sources") or []
        if not sources:
            return fail(f"missing sources for term {item.get('term')}")
        for source in sources[:3]:
            for key in ("volume_index", "volume_title", "source_status", "source_page", "evidence_en", "evidence_zh_simp"):
                if key not in source:
                    return fail(f"missing source field {key} for term {item.get('term')}")

    print(
        "lifestudy master vocab aggregate smoke PASS "
        f"source_volumes={quality.get('source_volume_count')} "
        f"unique_terms={quality.get('unique_term_count')} "
        f"conflicts={quality.get('meaning_conflict_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
