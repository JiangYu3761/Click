#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = "postgresql://localhost/jiangyu_os"


EXPECTED_MEANINGS = {
    "redemption": "救赎",
    "righteousness": "公义",
    "reality": "实际",
    "anointing": "受膏；膏油的涂抹",
    "priesthood": "祭司职分",
}

HELD_TERMS = {"living", "sacrifice"}


def fail(message: str) -> int:
    print(f"lifestudy frontend candidate adjudication applied smoke FAIL: {message}", file=sys.stderr)
    return 1


def main() -> int:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit("psycopg is required for adjudication applied smoke") from exc

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            SELECT term, meaning_zh, metadata
            FROM reader.domain_glossary_entries
            WHERE domain = 'lifestudy'
              AND volume = 'All'
              AND language = 'en'
              AND status = 'active'
              AND metadata ->> 'source' = 'lifestudy_frontend_candidate_adjudication_v2'
            """
        ).fetchall()
        dictionary_pollution = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.dictionary_entries
            WHERE lower(coalesce(source, '')) LIKE '%lifestudy_adjudication%'
               OR lower(coalesce(source, '')) LIKE '%lifestudy_frontend_candidate%'
            """
        ).fetchone()["n"]

    if dictionary_pollution != 0:
        return fail(f"general dictionary pollution detected: {dictionary_pollution}")
    if len(rows) != 26:
        return fail(f"expected 26 applied adjudicated domain terms, got {len(rows)}")
    by_term = {str(row["term"]).lower(): row for row in rows}
    for term, meaning in EXPECTED_MEANINGS.items():
        row = by_term.get(term)
        if not row:
            return fail(f"missing applied corrected term: {term}")
        if row.get("meaning_zh") != meaning:
            return fail(f"{term} meaning mismatch: {row.get('meaning_zh')} != {meaning}")
    for term in HELD_TERMS:
        if term in by_term:
            return fail(f"held term must not be applied: {term}")
    print("lifestudy frontend candidate adjudication applied smoke PASS applied=26 pollution=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
