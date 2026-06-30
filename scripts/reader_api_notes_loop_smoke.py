#!/usr/bin/env python3
from __future__ import annotations

import argparse
import uuid
from typing import Optional

import httpx


BOOK_HASH_PREFIX = "reader-api-notes-loop-smoke-book"
DEFAULT_BASE_URL = "http://127.0.0.1:18180"
DEFAULT_DATABASE_URL = "postgresql://localhost/sentence_reader"


def cleanup(database_url: str, book_id: Optional[str], book_hash: Optional[str]) -> None:
    try:
        import psycopg

        with psycopg.connect(database_url) as conn:
            if book_id:
                conn.execute("DELETE FROM reader.books WHERE id = %s", (book_id,))
            if book_hash:
                conn.execute("DELETE FROM reader.books WHERE book_hash = %s", (book_hash,))
            conn.commit()
    except Exception:
        pass


def assert_ok(response: httpx.Response, label: str) -> dict | list:
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"{label} failed: status={response.status_code} body={response.text}")
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the V1.4 notes management API loop.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    args = parser.parse_args()

    book_hash = f"{BOOK_HASH_PREFIX}-{uuid.uuid4().hex}"
    book_id: Optional[str] = None
    try:
        with httpx.Client(base_url=args.base_url, timeout=5.0) as client:
            health = assert_ok(client.get("/health"), "health")
            if not isinstance(health, dict) or not health.get("ok"):
                raise RuntimeError(f"health returned not ok: {health}")

            book = assert_ok(
                client.post(
                    "/books",
                    json={
                        "title": "Reader API Notes Loop Smoke",
                        "source_kind": "epub",
                        "book_hash": book_hash,
                    },
                ),
                "book create",
            )
            assert isinstance(book, dict)
            book_id = book["id"]

            note = assert_ok(
                client.post(
                    "/annotations",
                    json={
                        "book_id": book_id,
                        "kind": "note",
                        "source_text": "A note source sentence.",
                        "note_text": "Initial note.",
                        "chapter_title": "Smoke Chapter",
                        "chapter_locator": "notes-loop-chapter",
                        "range_locator": {"sentenceIndex": "3"},
                        "metadata": {"sentenceIndex": "3"},
                    },
                ),
                "note create",
            )
            assert isinstance(note, dict)

            patched = assert_ok(
                client.patch(f"/annotations/{note['id']}", json={"note_text": "Updated note."}),
                "note patch",
            )
            assert isinstance(patched, dict)
            if patched.get("note_text") != "Updated note.":
                raise RuntimeError(f"note patch did not persist: {patched}")

            red = assert_ok(
                client.post(
                    "/annotations",
                    json={
                        "book_id": book_id,
                        "kind": "red_highlight",
                        "source_text": "A red source sentence.",
                        "color": "red",
                        "chapter_title": "Smoke Chapter",
                        "chapter_locator": "notes-loop-chapter",
                        "range_locator": {"sentenceIndex": "4"},
                        "metadata": {"sentenceIndex": "4"},
                    },
                ),
                "red create",
            )
            assert isinstance(red, dict)

            listed = assert_ok(client.get(f"/books/{book_id}/annotations"), "annotation list")
            assert isinstance(listed, list)
            if len(listed) != 2:
                raise RuntimeError(f"expected 2 annotations before delete, got {len(listed)}")

            deleted = assert_ok(client.delete(f"/annotations/{red['id']}"), "red delete")
            assert isinstance(deleted, dict)
            if not deleted.get("ok"):
                raise RuntimeError(f"delete returned not ok: {deleted}")

            listed_after = assert_ok(client.get(f"/books/{book_id}/annotations"), "annotation list after delete")
            assert isinstance(listed_after, list)
            if len(listed_after) != 1 or listed_after[0]["id"] != note["id"]:
                raise RuntimeError(f"unexpected annotations after delete: {listed_after}")

        print("reader api notes loop smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader api notes loop smoke FAIL: {exc}")
        return 1
    finally:
        cleanup(args.database_url, book_id, book_hash)


if __name__ == "__main__":
    raise SystemExit(main())
