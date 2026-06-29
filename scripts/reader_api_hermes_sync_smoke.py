#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Optional

import httpx


BOOK_HASH = "reader-api-v19-hermes-sync-smoke"
DEFAULT_BASE_URL = "http://127.0.0.1:18180"
DEFAULT_DATABASE_URL = "postgresql://localhost/jiangyu_os"


def cleanup(database_url: str, book_id: Optional[str]) -> None:
    try:
        import psycopg

        with psycopg.connect(database_url) as conn:
            if book_id:
                conn.execute("DELETE FROM reader.books WHERE id = %s", (book_id,))
            conn.execute("DELETE FROM reader.books WHERE book_hash = %s", (BOOK_HASH,))
            conn.commit()
    except Exception:
        pass


def assert_ok(response: httpx.Response, label: str) -> dict | list:
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"{label} failed: status={response.status_code} body={response.text}")
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the V1.9 Hermes/Cognitive OS sync payload contract.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    args = parser.parse_args()

    book_id: Optional[str] = None
    try:
        cleanup(args.database_url, None)
        with tempfile.TemporaryDirectory(prefix="sentence-reader-v19-hermes-sync-") as tmp:
            output_dir = Path(tmp)
            with httpx.Client(base_url=args.base_url, timeout=5.0) as client:
                health = assert_ok(client.get("/health"), "health")
                if not isinstance(health, dict) or not health.get("ok"):
                    raise RuntimeError(f"health returned not ok: {health}")

                book = assert_ok(
                    client.post(
                        "/books",
                        json={
                            "title": "V1.9 Hermes Sync Smoke",
                            "author": "Codex",
                            "source_kind": "epub",
                            "book_hash": BOOK_HASH,
                            "file_path": "/tmp/sentence-reader-v19-hermes.epub",
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
                            "source_text": "Hermes sync must keep source evidence attached to interpretation.",
                            "note_text": "This should become reusable cognitive source material.",
                            "chapter_title": "Cognitive Sync",
                            "chapter_locator": "cognitive/sync.xhtml",
                            "range_locator": {"sentenceIndex": "11"},
                            "metadata": {"sentenceIndex": "11"},
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
                            "source_text": "Red highlights can be synced as low-friction signals.",
                            "color": "red",
                            "chapter_title": "Cognitive Sync",
                            "chapter_locator": "cognitive/sync.xhtml",
                            "range_locator": {"sentenceIndex": "12"},
                            "metadata": {"sentenceIndex": "12"},
                        },
                    ),
                    "red create",
                )
                assert isinstance(red, dict)

                sync = assert_ok(
                    client.post(
                        f"/books/{book_id}/sync/hermes",
                        json={"output_dir": str(output_dir), "include_red_highlights": True},
                    ),
                    "hermes sync",
                )
                assert isinstance(sync, dict)
                if sync.get("annotation_count") != 2 or sync.get("status") != "pending":
                    raise RuntimeError(f"sync response mismatch: {sync}")

                payload_path = Path(sync["payload_path"])
                if not payload_path.exists():
                    raise RuntimeError(f"sync payload file missing: {payload_path}")
                payload = json.loads(payload_path.read_text(encoding="utf-8"))
                if payload.get("schema") != "sentence_reader.hermes_sync.v1":
                    raise RuntimeError(f"sync payload schema mismatch: {payload}")
                if payload.get("target_system") != "hermes_cognitive_os":
                    raise RuntimeError(f"sync target mismatch: {payload}")
                if payload.get("annotation_count") != 2:
                    raise RuntimeError(f"sync annotation count mismatch: {payload}")
                if "cognitive_contract" not in payload:
                    raise RuntimeError("sync payload missing cognitive contract")

                events = assert_ok(client.get(f"/books/{book_id}/sync-events"), "sync events")
                assert isinstance(events, list)
                if len(events) != 1 or events[0].get("payload", {}).get("payload_path") != str(payload_path):
                    raise RuntimeError(f"sync event mismatch: {events}")

        print("reader api hermes sync smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader api hermes sync smoke FAIL: {exc}")
        return 1
    finally:
        cleanup(args.database_url, book_id)


if __name__ == "__main__":
    raise SystemExit(main())
