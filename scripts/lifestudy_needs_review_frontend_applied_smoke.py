#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READY = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_needs_review_frontend_ready_for_dry_run.csv"
DATABASE_URL = "postgresql://localhost/sentence_reader"
SOURCE_TITLE = "Life-study Needs-review Frontend V1"


def fail(message: str) -> int:
    print(f"lifestudy needs-review frontend applied smoke FAIL: {message}", file=sys.stderr)
    return 1


def main() -> int:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        return fail(f"psycopg missing: {exc}")

    rows = list(csv.DictReader(READY.open(encoding="utf-8-sig")))
    terms = [row["word"].lower() for row in rows]
    if len(terms) != 15:
        return fail(f"expected 15 ready terms, got {len(terms)}")

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        applied = conn.execute(
            """
            SELECT lower(term) AS term, meaning_zh, source_title, quality_grade, confidence, evidence_en, evidence_zh, metadata
            FROM reader.domain_glossary_entries
            WHERE domain = 'lifestudy'
              AND volume = 'All'
              AND language = 'en'
              AND status = 'active'
              AND lower(term) = ANY(%s::text[])
            """,
            (terms,),
        ).fetchall()
        dictionary_pollution = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.dictionary_entries
            WHERE lower(coalesce(source, '')) LIKE '%lifestudy_needs_review_frontend%'
               OR lower(coalesce(source, '')) LIKE '%life-study needs-review%'
            """
        ).fetchone()["n"]

    if len(applied) != len(terms):
        return fail(f"applied term count mismatch: {len(applied)} != {len(terms)}")
    by_term = {row["term"]: row for row in applied}
    expected_meanings = {row["word"].lower(): row["final_meaning_zh_simp"] for row in rows}
    for term, meaning in expected_meanings.items():
        row = by_term.get(term)
        if not row:
            return fail(f"missing applied term: {term}")
        if row["meaning_zh"] != meaning:
            return fail(f"{term} meaning mismatch: {row['meaning_zh']} != {meaning}")
        if row["source_title"] != SOURCE_TITLE:
            return fail(f"{term} source title mismatch: {row['source_title']}")
        if row["quality_grade"] != "B":
            return fail(f"{term} quality grade should be B")
        if not row["evidence_en"] or not row["evidence_zh"]:
            return fail(f"{term} missing evidence")
        metadata = row["metadata"] or {}
        if metadata.get("source") != "lifestudy_needs_review_frontend_v1":
            return fail(f"{term} metadata source mismatch: {metadata}")
    if dictionary_pollution != 0:
        return fail(f"dictionary pollution detected: {dictionary_pollution}")
    print("lifestudy needs-review frontend applied smoke PASS applied=15 dictionary_pollution=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
