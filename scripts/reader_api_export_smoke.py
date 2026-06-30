#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import httpx


BOOK_HASH_PREFIX = "reader-api-v16-export-smoke"
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
    parser = argparse.ArgumentParser(description="Smoke-test the V1.6 export API contract.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    args = parser.parse_args()

    book_hash = f"{BOOK_HASH_PREFIX}-{uuid.uuid4().hex}"
    book_id: Optional[str] = None
    try:
        with tempfile.TemporaryDirectory(prefix="sentence-reader-v16-export-") as tmp:
            output_dir = Path(tmp)
            with httpx.Client(base_url=args.base_url, timeout=5.0) as client:
                health = assert_ok(client.get("/health"), "health")
                if not isinstance(health, dict) or not health.get("ok"):
                    raise RuntimeError(f"health returned not ok: {health}")

                book = assert_ok(
                    client.post(
                        "/books",
                        json={
                            "title": "V1.6 Export Smoke",
                            "author": "Codex",
                            "source_kind": "epub",
                            "book_hash": book_hash,
                            "file_path": "/tmp/sentence-reader-v16-export.epub",
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
                            "source_text": "Export must preserve source sentence text.",
                            "note_text": "Portable note text.",
                            "chapter_title": "Export Chapter",
                            "chapter_locator": "export/chapter.xhtml",
                            "range_locator": {"sentenceIndex": "8"},
                            "metadata": {"sentenceIndex": "8"},
                        },
                    ),
                    "note create",
                )
                assert isinstance(note, dict)

                red = assert_ok(
                    client.post(
                        "/annotations",
                        json={
                            "book_id": book_id,
                            "kind": "red_highlight",
                            "source_text": "Export must also include red highlights.",
                            "color": "red",
                            "chapter_title": "Export Chapter",
                            "chapter_locator": "export/chapter.xhtml",
                            "range_locator": {"sentenceIndex": "9"},
                            "metadata": {"sentenceIndex": "9"},
                        },
                    ),
                    "red create",
                )
                assert isinstance(red, dict)

                export = assert_ok(
                    client.post(
                        f"/books/{book_id}/export",
                        json={"output_dir": str(output_dir), "include_json": True},
                    ),
                    "export generate",
                )
                assert isinstance(export, dict)
                if export.get("annotation_count") != 2:
                    raise RuntimeError(f"expected 2 annotations exported, got {export}")

                markdown_path = Path(export["markdown_path"])
                json_path = Path(export["json_path"])
                if not markdown_path.exists() or not json_path.exists():
                    raise RuntimeError(f"export files missing: {export}")
                markdown_text = markdown_path.read_text(encoding="utf-8")
                json_payload = json.loads(json_path.read_text(encoding="utf-8"))
                if "Export must preserve source sentence text." not in markdown_text:
                    raise RuntimeError("markdown export missing note source text")
                if "Export must also include red highlights." not in markdown_text:
                    raise RuntimeError("markdown export missing red highlight text")
                if json_payload.get("schema") != "sentence_reader.annotations_export.v1":
                    raise RuntimeError(f"json export schema mismatch: {json_payload}")

                exports = assert_ok(client.get(f"/books/{book_id}/exports"), "export list")
                assert isinstance(exports, list)
                kinds = {item["export_kind"] for item in exports}
                if kinds != {"markdown", "json"}:
                    raise RuntimeError(f"expected markdown/json export records, got {exports}")

        print("reader api export smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader api export smoke FAIL: {exc}")
        return 1
    finally:
        cleanup(args.database_url, book_id, book_hash)


if __name__ == "__main__":
    raise SystemExit(main())
