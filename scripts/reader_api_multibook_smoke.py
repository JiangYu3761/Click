#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import Optional

import httpx


BOOK_HASHES = ("reader-api-v15-multibook-a", "reader-api-v15-multibook-b")
DEFAULT_BASE_URL = "http://127.0.0.1:18180"
DEFAULT_DATABASE_URL = "postgresql://localhost/sentence_reader"


def cleanup(database_url: str, book_ids: list[str]) -> None:
    try:
        import psycopg

        with psycopg.connect(database_url) as conn:
            for book_id in book_ids:
                conn.execute("DELETE FROM reader.books WHERE id = %s", (book_id,))
            conn.execute("DELETE FROM reader.books WHERE book_hash = ANY(%s)", (list(BOOK_HASHES),))
            conn.commit()
    except Exception:
        pass


def assert_ok(response: httpx.Response, label: str) -> dict | list:
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"{label} failed: status={response.status_code} body={response.text}")
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the V1.5 multi-book API contract.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    args = parser.parse_args()

    book_ids: list[str] = []
    try:
        cleanup(args.database_url, [])
        with httpx.Client(base_url=args.base_url, timeout=5.0) as client:
            health = assert_ok(client.get("/health"), "health")
            if not isinstance(health, dict) or not health.get("ok"):
                raise RuntimeError(f"health returned not ok: {health}")

            first = assert_ok(
                client.post(
                    "/books",
                    json={
                        "title": "V1.5 Multi Book A",
                        "source_kind": "epub",
                        "book_hash": BOOK_HASHES[0],
                        "file_path": "/tmp/sentence-reader-v15-a.epub",
                    },
                ),
                "first book create",
            )
            second = assert_ok(
                client.post(
                    "/books",
                    json={
                        "title": "V1.5 Multi Book B",
                        "source_kind": "epub",
                        "book_hash": BOOK_HASHES[1],
                        "file_path": "/tmp/sentence-reader-v15-b.epub",
                    },
                ),
                "second book create",
            )
            assert isinstance(first, dict)
            assert isinstance(second, dict)
            book_ids.extend([first["id"], second["id"]])

            listed = assert_ok(client.get("/books"), "book list")
            assert isinstance(listed, list)
            listed_hashes = {item["book_hash"] for item in listed}
            if not set(BOOK_HASHES).issubset(listed_hashes):
                raise RuntimeError(f"multi-book list missing hashes: {listed}")

            assert_ok(
                client.put(
                    f"/books/{first['id']}/position",
                    json={
                        "chapter_locator": "a/chapter.xhtml",
                        "page_index": 1,
                        "total_pages": 8,
                        "page_ratio": 0.142,
                        "locator": {"chapterIndex": 0, "pageIndex": 1},
                    },
                ),
                "first position",
            )
            assert_ok(
                client.put(
                    f"/books/{second['id']}/position",
                    json={
                        "chapter_locator": "b/chapter.xhtml",
                        "page_index": 5,
                        "total_pages": 12,
                        "page_ratio": 0.455,
                        "locator": {"chapterIndex": 2, "pageIndex": 5},
                    },
                ),
                "second position",
            )
            assert_ok(
                client.post(
                    "/annotations",
                    json={
                        "book_id": first["id"],
                        "kind": "note",
                        "source_text": "Book A note source.",
                        "note_text": "Only belongs to book A.",
                        "chapter_locator": "a/chapter.xhtml",
                        "range_locator": {"sentenceIndex": "1"},
                    },
                ),
                "first annotation",
            )
            assert_ok(
                client.post(
                    "/annotations",
                    json={
                        "book_id": second["id"],
                        "kind": "red_highlight",
                        "source_text": "Book B highlight source.",
                        "color": "red",
                        "chapter_locator": "b/chapter.xhtml",
                        "range_locator": {"sentenceIndex": "2"},
                    },
                ),
                "second annotation",
            )

            first_position = assert_ok(client.get(f"/books/{first['id']}/position"), "first position get")
            second_position = assert_ok(client.get(f"/books/{second['id']}/position"), "second position get")
            if first_position["chapter_locator"] != "a/chapter.xhtml":
                raise RuntimeError(f"first position leaked or failed: {first_position}")
            if second_position["chapter_locator"] != "b/chapter.xhtml":
                raise RuntimeError(f"second position leaked or failed: {second_position}")

            first_annotations = assert_ok(client.get(f"/books/{first['id']}/annotations"), "first annotations")
            second_annotations = assert_ok(client.get(f"/books/{second['id']}/annotations"), "second annotations")
            if len(first_annotations) != 1 or first_annotations[0]["kind"] != "note":
                raise RuntimeError(f"first annotations not isolated: {first_annotations}")
            if len(second_annotations) != 1 or second_annotations[0]["kind"] != "red_highlight":
                raise RuntimeError(f"second annotations not isolated: {second_annotations}")

        print("reader api multibook smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader api multibook smoke FAIL: {exc}")
        return 1
    finally:
        cleanup(args.database_url, book_ids)


if __name__ == "__main__":
    raise SystemExit(main())
