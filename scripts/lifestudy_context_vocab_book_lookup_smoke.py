#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = "postgresql://localhost/jiangyu_os"


def fail(message: str) -> int:
    print(f"lifestudy context vocab book lookup smoke FAIL: {message}")
    return 1


def main() -> int:
    sys.path.insert(0, str(ROOT))
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit("psycopg is required for book lookup smoke") from exc

    from reader_api import db
    from reader_api.app import lookup_book_word

    db.DATABASE_URL = DATABASE_URL
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        book = conn.execute(
            """
            SELECT b.id, b.title, bf.file_path
            FROM reader.books b
            LEFT JOIN LATERAL (
                SELECT file_path
                FROM reader.book_files
                WHERE book_id = b.id
                ORDER BY created_at DESC
                LIMIT 1
            ) bf ON true
            WHERE (
                lower(b.title) LIKE '%life-study of genesis%'
                OR b.title LIKE '%创世记生命读经%'
                OR lower(coalesce(bf.file_path, '')) LIKE '%life-study%'
                OR coalesce(bf.file_path, '') LIKE '%创世记生命读经%'
            )
            ORDER BY b.updated_at DESC
            LIMIT 1
            """
        ).fetchone()
        if not book:
            return fail("Genesis Life-study book is not imported")
        book_id = str(book["id"])
        glossary_count = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.book_glossary
            WHERE book_id = %s AND source = 'lifestudy_context'
            """,
            (book_id,),
        ).fetchone()["n"]
        vocab_grade_rows = conn.execute(
            """
            SELECT metadata->>'quality_grade' AS grade, count(*) AS n
            FROM reader.book_vocab_items
            WHERE book_id = %s AND meaning_source = 'lifestudy_context'
            GROUP BY metadata->>'quality_grade'
            ORDER BY metadata->>'quality_grade'
            """,
            (book_id,),
        ).fetchall()
        dictionary_pollution = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.dictionary_entries
            WHERE lower(coalesce(source, '')) LIKE '%lifestudy%'
               OR lower(coalesce(source, '')) LIKE '%life-study%'
               OR lower(coalesce(source, '')) LIKE '%lifestudy_context%'
            """
        ).fetchone()["n"]

    grade_counts = {str(row["grade"]): int(row["n"]) for row in vocab_grade_rows}
    if int(glossary_count) != 25:
        return fail(f"expected 25 Life-study book glossary entries, got {glossary_count}")
    if grade_counts.get("A", 0) != 19 or grade_counts.get("B", 0) != 6:
        return fail(f"expected A=19/B=6 book vocab entries, got {grade_counts}")
    if int(dictionary_pollution) != 0:
        return fail(f"Life-study entries leaked into dictionary_entries: {dictionary_pollution}")

    payload = lookup_book_word(book_id, "tree of life", None)
    item = payload.get("item") or {}
    if payload.get("found") is not True:
        return fail("lookup did not find tree of life")
    if item.get("meaning_source") != "book_glossary":
        return fail(f"expected book_glossary lookup source, got {item.get('meaning_source')}")
    if not item.get("context_meaning_zh"):
        return fail("lookup item has no Chinese context meaning")

    print(
        "lifestudy context vocab book lookup smoke PASS "
        f"book_id={book_id} glossary=25 grades={grade_counts} tree_of_life={item.get('context_meaning_zh')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
