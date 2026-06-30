#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "v1_schema.sql"
REQUIRED_TABLES = {
    "books",
    "reading_positions",
    "sentences",
    "annotations",
    "exports",
    "hermes_sync_queue",
}


def main() -> int:
    sql = SCHEMA.read_text(encoding="utf-8")
    connection = sqlite3.connect(":memory:")
    connection.executescript(sql)
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    tables = {row[0] for row in rows}
    missing = sorted(REQUIRED_TABLES - tables)
    if missing:
        print(f"schema FAIL missing={missing}")
        return 1

    connection.execute(
        """
        INSERT INTO books (id, title, author, file_path, book_hash, file_kind, created_at)
        VALUES ('book-1', 'Positioning', 'Al Ries', '/tmp/positioning.epub', 'bookhash', 'epub', '2026-06-23T00:00:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO sentences (id, book_hash, chapter_locator, chapter_title, sentence_index, sentence_text_hash, text, range_locator_json, created_at)
        VALUES ('sentence-1', 'bookhash', 'chapter-1', 'Chapter 1', 1, 'hash', 'Sentence text.', '{"href":"chapter1.xhtml"}', '2026-06-23T00:00:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO annotations (id, book_hash, sentence_id, kind, source_text, note_text, color, chapter_title, chapter_locator, range_locator_json, created_at, updated_at)
        VALUES ('annotation-1', 'bookhash', 'sentence-1', 'note', 'Sentence text.', 'Note text.', NULL, 'Chapter 1', 'chapter-1', '{"href":"chapter1.xhtml"}', '2026-06-23T00:00:00Z', '2026-06-23T00:00:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO hermes_sync_queue (id, annotation_id, payload_json, status, created_at, updated_at)
        VALUES ('sync-1', 'annotation-1', '{"schema_version":"sentence_reader.hermes_sync.v1"}', 'pending', '2026-06-23T00:00:00Z', '2026-06-23T00:00:00Z')
        """
    )
    connection.commit()
    print(f"schema PASS tables={len(tables)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

