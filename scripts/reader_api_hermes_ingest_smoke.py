#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import httpx


BOOK_HASH_PREFIX = "reader-api-v20c-hermes-ingest-smoke"
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
    parser = argparse.ArgumentParser(description="Smoke-test the V2.0C Hermes ingestion worker.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    args = parser.parse_args()

    book_hash = f"{BOOK_HASH_PREFIX}-{uuid.uuid4().hex}"
    book_id: Optional[str] = None
    try:
        with tempfile.TemporaryDirectory(prefix="sentence-reader-v20c-hermes-ingest-") as tmp:
            tmp_dir = Path(tmp)
            with httpx.Client(base_url=args.base_url, timeout=8.0) as client:
                health = assert_ok(client.get("/health"), "health")
                if not isinstance(health, dict) or not health.get("ok"):
                    raise RuntimeError(f"health returned not ok: {health}")

                book = assert_ok(
                    client.post(
                        "/books",
                        json={
                            "title": "V2.0C Hermes Ingest Smoke",
                            "author": "Codex",
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
                            "source_text": "Reader ingestion should hand evidence to Hermes without changing the active pack.",
                            "note_text": "Keep ingestion as an incoming asset until reviewed.",
                            "chapter_title": "Worker",
                            "chapter_locator": "worker.xhtml",
                            "range_locator": {"sentenceIndex": "21"},
                            "metadata": {"sentenceIndex": "21"},
                        },
                    ),
                    "annotation create",
                )
                assert isinstance(note, dict)

                sync = assert_ok(
                    client.post(
                        f"/books/{book_id}/sync/hermes",
                        json={"output_dir": str(tmp_dir / "sync")},
                    ),
                    "sync create",
                )
                assert isinstance(sync, dict)
                if sync.get("status") != "pending":
                    raise RuntimeError(f"sync did not create pending event: {sync}")

                ingest = assert_ok(
                    client.post(
                        "/sync/hermes/ingest",
                        json={
                            "cognitive_os_dir": str(tmp_dir / "hermes_cognitive_os"),
                            "sync_event_ids": [sync["sync_event"]["id"]],
                        },
                    ),
                    "ingest",
                )
                assert isinstance(ingest, dict)
                if ingest.get("synced_count") != 1 or ingest.get("failed_count") != 0:
                    raise RuntimeError(f"ingest mismatch: {ingest}")

                event = ingest["events"][0]
                payload_path = Path(event["payload_path"])
                manifest_path = Path(event["manifest_path"])
                if not payload_path.exists() or not manifest_path.exists():
                    raise RuntimeError(f"ingest files missing: {event}")
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("schema") != "sentence_reader.hermes_ingestion_manifest.v1":
                    raise RuntimeError(f"manifest schema mismatch: {manifest}")
                if manifest.get("policy", {}).get("active_pack_mutation") is not False:
                    raise RuntimeError(f"manifest policy unsafe: {manifest}")

                events = assert_ok(client.get(f"/books/{book_id}/sync-events"), "sync events")
                assert isinstance(events, list)
                if len(events) != 1 or events[0].get("status") != "synced":
                    raise RuntimeError(f"sync event was not marked synced: {events}")

        print("reader api hermes ingest smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader api hermes ingest smoke FAIL: {exc}")
        return 1
    finally:
        cleanup(args.database_url, book_id, book_hash)


if __name__ == "__main__":
    raise SystemExit(main())
