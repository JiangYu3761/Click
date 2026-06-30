#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "lifestudy_context_vocab_v1_build.py"
APPLY = ROOT / "scripts" / "lifestudy_context_vocab_v1_apply.py"


def fail(message: str) -> int:
    print(f"lifestudy context vocab v1 apply smoke FAIL: {message}")
    return 1


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    code, stdout, stderr = run([sys.executable, str(BUILD)])
    if code != 0:
        return fail(stderr.strip() or stdout.strip())
    code, stdout, stderr = run([sys.executable, str(APPLY)])
    if code != 0:
        return fail(stderr.strip() or stdout.strip())
    payload = json.loads(stdout)
    if payload.get("schema") != "sentence_reader.lifestudy_context_vocab_v1_apply.v1":
        return fail(f"unexpected apply schema: {payload.get('schema')}")
    if payload.get("mode") != "dry_run":
        return fail(f"smoke must default to dry-run, got {payload.get('mode')}")
    if payload.get("database_write_performed") is not False:
        return fail("dry-run must not write database")
    if payload.get("candidate_count", 0) < 20:
        return fail(f"expected import-ready candidates, got {payload.get('candidate_count')}")
    pollution = ((payload.get("preflight") or {}).get("dictionary_pollution_count"))
    if pollution != 0:
        return fail(f"general dictionary pollution detected: {pollution}")
    for term in ("economy", "dispensing", "mingled"):
        if term not in payload.get("terms", []):
            return fail(f"missing expected import term: {term}")
    print(
        "lifestudy context vocab v1 apply smoke PASS "
        f"dry_run_candidates={payload.get('candidate_count')} pollution={pollution}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
