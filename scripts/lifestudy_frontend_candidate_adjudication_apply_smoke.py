#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADJUDICATE = ROOT / "scripts" / "lifestudy_frontend_candidate_adjudication_v2.py"
APPLY = ROOT / "scripts" / "lifestudy_frontend_candidate_adjudication_apply.py"


def fail(message: str) -> int:
    print(f"lifestudy frontend candidate adjudication apply smoke FAIL: {message}")
    return 1


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    code, stdout, stderr = run([sys.executable, str(ADJUDICATE)])
    if code != 0:
        return fail(stderr.strip() or stdout.strip())
    code, stdout, stderr = run([sys.executable, str(APPLY)])
    if code != 0:
        return fail(stderr.strip() or stdout.strip())
    payload = json.loads(stdout)
    if payload.get("schema") != "sentence_reader.lifestudy_frontend_candidate_adjudication_apply.v1":
        return fail(f"unexpected apply schema: {payload.get('schema')}")
    if payload.get("mode") != "dry_run":
        return fail(f"smoke must default to dry-run, got {payload.get('mode')}")
    if payload.get("database_write_performed") is not False:
        return fail("dry-run must not write database")
    if payload.get("candidate_count") != 26:
        return fail(f"expected 26 adjudicated ready candidates, got {payload.get('candidate_count')}")
    terms = set(payload.get("terms") or [])
    for term in ("redemption", "righteousness", "reality", "anointing", "priesthood"):
        if term not in terms:
            return fail(f"missing corrected term in dry-run terms: {term}")
    for term in ("living", "sacrifice"):
        if term in terms:
            return fail(f"held term must not be in dry-run terms: {term}")
    pollution = ((payload.get("preflight") or {}).get("dictionary_pollution_count"))
    if pollution != 0:
        return fail(f"general dictionary pollution detected: {pollution}")
    if payload.get("target") != "reader.domain_glossary_entries":
        return fail(f"unexpected target: {payload.get('target')}")
    print(
        "lifestudy frontend candidate adjudication apply smoke PASS "
        f"dry_run_candidates={payload.get('candidate_count')} pollution={pollution}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
