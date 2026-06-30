#!/usr/bin/env python3
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Optional

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reader_api.app import app
from reader_api.config import database_url


BOOK_HASH_PREFIX = "reader-api-live-smoke-book"


def cleanup(book_id: Optional[str], book_hash: Optional[str]) -> None:
    try:
        import psycopg

        with psycopg.connect(database_url()) as conn:
            if book_id:
                conn.execute("DELETE FROM reader.books WHERE id = %s", (book_id,))
            if book_hash:
                conn.execute("DELETE FROM reader.books WHERE book_hash = %s", (book_hash,))
            conn.commit()
    except Exception:
        pass


def main() -> int:
    client = TestClient(app)
    book_hash = f"{BOOK_HASH_PREFIX}-{uuid.uuid4().hex}"
    book_id: Optional[str] = None
    try:
        health = client.get("/health")
        if health.status_code != 200 or not health.json().get("ok"):
            raise RuntimeError(f"health failed: status={health.status_code} body={health.text}")

        book = client.post(
            "/books",
            json={
                "title": "Reader API Live Smoke",
                "author": "Codex",
                "source_kind": "epub",
                "book_hash": book_hash,
            },
        )
        if book.status_code != 200:
            raise RuntimeError(f"book create failed: status={book.status_code} body={book.text}")
        book_id = book.json()["id"]

        sentence = client.post(
            "/sentences",
            json={
                "book_id": book_id,
                "chapter_locator": "live-smoke-chapter",
                "sentence_index": 1,
                "sentence_text_hash": "live-smoke-sentence",
                "text": "Sentence Reader persists whole-sentence thinking.",
                "range_locator": {"href": "chapter.xhtml"},
            },
        )
        if sentence.status_code != 200:
            raise RuntimeError(f"sentence create failed: status={sentence.status_code} body={sentence.text}")
        sentence_id = sentence.json()["id"]

        annotation = client.post(
            "/annotations",
            json={
                "book_id": book_id,
                "sentence_id": sentence_id,
                "kind": "note",
                "source_text": "Sentence Reader persists whole-sentence thinking.",
                "note_text": "Live smoke note.",
                "chapter_locator": "live-smoke-chapter",
                "range_locator": {"href": "chapter.xhtml"},
            },
        )
        if annotation.status_code != 200:
            raise RuntimeError(f"annotation create failed: status={annotation.status_code} body={annotation.text}")

        position = client.put(
            f"/books/{book_id}/position",
            json={
                "chapter_locator": "live-smoke-chapter",
                "page_index": 3,
                "total_pages": 12,
                "page_ratio": 0.25,
                "locator": {"href": "chapter.xhtml", "page": 4},
            },
        )
        if position.status_code != 200:
            raise RuntimeError(f"position upsert failed: status={position.status_code} body={position.text}")

        annotations = client.get(f"/books/{book_id}/annotations")
        if annotations.status_code != 200 or len(annotations.json()) != 1:
            raise RuntimeError(f"annotation list failed: status={annotations.status_code} body={annotations.text}")

        print("reader api live smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader api live smoke BLOCKED: {exc}")
        return 2
    finally:
        cleanup(book_id, book_hash)


if __name__ == "__main__":
    raise SystemExit(main())
