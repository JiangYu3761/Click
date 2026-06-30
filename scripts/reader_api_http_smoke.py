#!/usr/bin/env python3
from __future__ import annotations

import argparse
import uuid
from typing import Optional

import httpx


BOOK_HASH_PREFIX = "reader-api-http-smoke-book"
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


def assert_ok(response: httpx.Response, label: str) -> dict:
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"{label} failed: status={response.status_code} body={response.text}")
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an HTTP smoke test against the running Sentence Reader API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    args = parser.parse_args()

    book_hash = f"{BOOK_HASH_PREFIX}-{uuid.uuid4().hex}"
    book_id: Optional[str] = None
    try:
        with httpx.Client(base_url=args.base_url, timeout=5.0) as client:
            health = assert_ok(client.get("/health"), "health")
            if not health.get("ok"):
                raise RuntimeError(f"health returned not ok: {health}")

            book = assert_ok(
                client.post(
                    "/books",
                    json={
                        "title": "Reader API HTTP Smoke",
                        "author": "Codex",
                        "source_kind": "epub",
                        "book_hash": book_hash,
                    },
                ),
                "book create",
            )
            book_id = book["id"]

            assert_ok(
                client.put(
                    f"/books/{book_id}/position",
                    json={
                        "chapter_locator": "http-smoke-chapter",
                        "page_index": 4,
                        "total_pages": 20,
                        "page_ratio": 0.21,
                        "locator": {"chapterIndex": 1, "pageIndex": 4},
                    },
                ),
                "position upsert",
            )
            position = assert_ok(client.get(f"/books/{book_id}/position"), "position get")
            if position["page_index"] != 4:
                raise RuntimeError(f"expected page_index 4, got {position}")

            annotation = assert_ok(
                client.post(
                    "/annotations",
                    json={
                        "book_id": book_id,
                        "kind": "red_highlight",
                        "source_text": "A persistent red highlight.",
                        "color": "red",
                        "chapter_locator": "http-smoke-chapter",
                        "range_locator": {"sentenceIndex": "7"},
                    },
                ),
                "annotation create",
            )
            annotations = assert_ok(client.get(f"/books/{book_id}/annotations"), "annotation list")
            if not any(item["id"] == annotation["id"] for item in annotations):
                raise RuntimeError("created annotation not found in list")

        print("reader api http smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader api http smoke FAIL: {exc}")
        return 1
    finally:
        cleanup(args.database_url, book_id, book_hash)


if __name__ == "__main__":
    raise SystemExit(main())
