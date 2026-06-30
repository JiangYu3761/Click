#!/usr/bin/env python3
from __future__ import annotations

import argparse
from uuid import uuid4


DEFAULT_DATABASE_URL = "postgresql://localhost/sentence_reader"


def _load_psycopg():
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise SystemExit(
            "reader pg smoke SKIP: psycopg is not installed. "
            "Install requirements-reader-api.txt after PostgreSQL is available."
        ) from exc
    return psycopg, Jsonb


def new_id(prefix: str) -> str:
    return f"{prefix}_smoke_{uuid4().hex}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a PostgreSQL CRUD smoke test for Sentence Reader V1.2.")
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    args = parser.parse_args()

    psycopg, Jsonb = _load_psycopg()
    book_id = new_id("book")
    sentence_id = new_id("sent")
    annotation_id = new_id("ann")

    try:
        with psycopg.connect(args.database_url) as conn:
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO reader.books (id, title, author, source_kind, book_hash)
                    VALUES (%s, 'Smoke Book', 'Codex', 'epub', %s)
                    """,
                    (book_id, f"hash-{book_id}"),
                )
                conn.execute(
                    """
                    INSERT INTO reader.sentences (
                        id, book_id, chapter_locator, sentence_index, sentence_text_hash, text, range_locator
                    )
                    VALUES (%s, %s, 'chapter-1', 1, 'sentence-hash', 'Sentence text.', %s)
                    """,
                    (sentence_id, book_id, Jsonb({"href": "chapter1.xhtml"})),
                )
                conn.execute(
                    """
                    INSERT INTO reader.annotations (
                        id, book_id, sentence_id, kind, source_text, note_text, chapter_locator, range_locator
                    )
                    VALUES (%s, %s, %s, 'note', 'Sentence text.', 'Note text.', 'chapter-1', %s)
                    """,
                    (annotation_id, book_id, sentence_id, Jsonb({"href": "chapter1.xhtml"})),
                )
                conn.execute(
                    """
                    INSERT INTO reader.reading_positions (
                        book_id, chapter_locator, page_index, total_pages, page_ratio, locator
                    )
                    VALUES (%s, 'chapter-1', 2, 10, 0.2, %s)
                    """,
                    (book_id, Jsonb({"page": 3})),
                )
                count = conn.execute(
                    "SELECT count(*) AS count FROM reader.annotations WHERE book_id = %s",
                    (book_id,),
                ).fetchone()[0]
                if count != 1:
                    raise RuntimeError(f"expected 1 annotation, got {count}")
                conn.execute("DELETE FROM reader.books WHERE id = %s", (book_id,))
            conn.commit()
    except psycopg.OperationalError as exc:
        raise SystemExit(
            "reader pg smoke BLOCKED: PostgreSQL is not reachable. "
            f"database_url={args.database_url} detail={exc}"
        ) from exc

    print("reader pg smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
