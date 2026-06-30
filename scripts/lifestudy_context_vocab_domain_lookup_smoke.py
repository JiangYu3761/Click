#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = "postgresql://localhost/sentence_reader"


def fail(message: str) -> int:
    print(f"lifestudy context vocab domain lookup smoke FAIL: {message}")
    return 1


def main() -> int:
    sys.path.insert(0, str(ROOT))
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit("psycopg is required for domain lookup smoke") from exc

    from reader_api import db
    from reader_api.app import lookup_book_word, stable_id

    db.DATABASE_URL = DATABASE_URL
    book_id = stable_id("book", "lifestudy-domain-lookup-smoke")
    book_hash = "lifestudy-domain-lookup-smoke"

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        entry = conn.execute(
            """
            SELECT term, meaning_zh, quality_grade
            FROM reader.domain_glossary_entries
            WHERE domain = 'lifestudy'
              AND volume = 'Genesis'
              AND language = 'en'
              AND status = 'active'
              AND quality_grade IN ('A', 'B')
            ORDER BY CASE quality_grade WHEN 'A' THEN 0 ELSE 1 END, confidence DESC, term ASC
            LIMIT 1
            """
        ).fetchone()
        if not entry:
            return fail("no active Genesis A/B domain glossary entry available")
        conn.execute(
            """
            INSERT INTO reader.books (id, title, author, source_kind, book_hash, created_at, updated_at)
            VALUES (%s, 'Life-study of Genesis Smoke', 'Witness Lee', 'epub', %s, now(), now())
            ON CONFLICT (id) DO UPDATE
            SET title = EXCLUDED.title,
                author = EXCLUDED.author,
                book_hash = EXCLUDED.book_hash,
                updated_at = now()
            """,
            (book_id, book_hash),
        )
        conn.commit()

    try:
        payload = lookup_book_word(book_id, str(entry["term"]), None)
        item = payload.get("item") or {}
        if payload.get("found") is not True:
            return fail(f"lookup did not find domain term: {entry['term']}")
        if item.get("meaning_source") != "lifestudy_domain_glossary":
            return fail(f"unexpected meaning_source: {item.get('meaning_source')}")
        if item.get("reviewable") is not False:
            return fail("domain glossary item must not be reviewable as current-book vocab")
        if not item.get("context_meaning_zh"):
            return fail("domain glossary item has no Chinese meaning")
    finally:
        with psycopg.connect(DATABASE_URL) as conn:
            conn.execute("DELETE FROM reader.books WHERE id = %s", (book_id,))
            conn.commit()

    print(
        "lifestudy context vocab domain lookup smoke PASS "
        f"term={entry['term']} grade={entry['quality_grade']} meaning={entry['meaning_zh']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
