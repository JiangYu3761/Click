#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_corpus_inventory.py"
REPORT = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_corpus_inventory.json"


def fail(message: str) -> int:
    print(f"lifestudy corpus inventory smoke FAIL: {message}")
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
    if payload.get("schema") != "sentence_reader.lifestudy_corpus_inventory.v1":
        return fail(f"unexpected schema: {payload.get('schema')}")
    if payload.get("database_write_performed") is not False:
        return fail("inventory must be no-write")
    counts = payload.get("counts") or {}
    if counts.get("processable_volume_count", 0) < 50:
        return fail(f"expected Life-study volume inventory, got {counts.get('processable_volume_count')}")
    rows = {row.get("volume_index"): row for row in payload.get("items") or []}
    for volume in ("01", "02", "03"):
        row = rows.get(volume)
        if not row:
            return fail(f"missing volume {volume}")
        if not row.get("full_done"):
            return fail(f"expected volume {volume} full no-write output to exist")
    if rows.get("04", {}).get("next_action") != "run_first50_no_write_probe":
        return fail("expected Numbers to be the next first-50 probe")
    print(
        "lifestudy corpus inventory smoke PASS "
        f"processable={counts.get('processable_volume_count')} full_done={counts.get('full_done_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
