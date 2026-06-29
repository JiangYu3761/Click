#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORT_SCRIPT = ROOT / "scripts" / "lifestudy_context_vocab_import.py"
IMPORTABLE = ROOT / "reports" / "lifestudy_vocab_pipeline" / "01_Genesis-120-pages-1-1255-importable.json"
DATABASE_URL = "postgresql://localhost/jiangyu_os"


def fail(message: str) -> int:
    print(f"lifestudy context vocab import smoke FAIL: {message}")
    return 1


def first_book_id() -> str:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        row = conn.execute("SELECT id FROM reader.books ORDER BY updated_at DESC LIMIT 1").fetchone()
        return str((row or {}).get("id") or "")


def main() -> int:
    if not IMPORT_SCRIPT.exists():
        return fail(f"missing import script: {IMPORT_SCRIPT}")
    if not IMPORTABLE.exists():
        return fail(f"missing importable report: {IMPORTABLE}")

    source = IMPORT_SCRIPT.read_text(encoding="utf-8")
    required = [
        "mode\": \"apply\" if args.apply else \"dry_run\"",
        "if args.apply:",
        "--domain-staging",
        "grade not in {\"A\", \"B\"}",
        "import_allowed",
        "reader.book_glossary",
        "reader.book_glossary.source = 'user'",
        "reader.book_vocab_items",
        "meaning_source, '') <> 'user_glossary'",
        "reader.domain_glossary_entries",
        "target\": \"domain_staging\"",
        "database_write_performed",
    ]
    missing = [marker for marker in required if marker not in source]
    if missing:
        return fail(f"missing static markers: {missing}")

    book_id = first_book_id()
    if not book_id:
        return fail("no reader.books rows available for dry-run smoke")

    proc = subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            str(IMPORTABLE),
            "--book-id",
            book_id,
            "--database-url",
            DATABASE_URL,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = json.loads(proc.stdout)
    if payload.get("mode") != "dry_run":
        return fail(f"expected dry_run mode, got {payload.get('mode')}")
    if payload.get("database_write_performed") is not False:
        return fail("dry-run reported database write")
    if payload.get("candidate_count", 0) <= 0:
        return fail("dry-run found no accepted candidates")
    if not payload.get("accepted_terms"):
        return fail("dry-run accepted_terms is empty")

    domain_proc = subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            str(IMPORTABLE),
            "--domain-staging",
            "--domain",
            "lifestudy",
            "--volume",
            "Genesis",
            "--database-url",
            DATABASE_URL,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    domain_payload = json.loads(domain_proc.stdout)
    if domain_payload.get("mode") != "dry_run" or domain_payload.get("target") != "domain_staging":
        return fail(f"expected domain dry_run, got {domain_payload}")
    if domain_payload.get("database_write_performed") is not False:
        return fail("domain dry-run reported database write")
    if domain_payload.get("candidate_count", 0) <= 0:
        return fail("domain dry-run found no accepted candidates")

    print(
        "lifestudy context vocab import smoke PASS "
        f"book_id={book_id} candidates={payload.get('candidate_count')} domain_candidates={domain_payload.get('candidate_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
