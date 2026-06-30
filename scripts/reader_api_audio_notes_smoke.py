#!/usr/bin/env python3
from __future__ import annotations

import argparse
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import httpx


BOOK_HASH_PREFIX = "reader-api-v17-audio-notes-smoke"
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
    parser = argparse.ArgumentParser(description="Smoke-test the V1.7 audio note persistence contract.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    args = parser.parse_args()

    book_hash = f"{BOOK_HASH_PREFIX}-{uuid.uuid4().hex}"
    book_id: Optional[str] = None
    try:
        with tempfile.TemporaryDirectory(prefix="sentence-reader-v17-audio-") as tmp:
            audio_path = Path(tmp) / "note.wav"
            audio_path.write_bytes(b"fake wav bytes")

            with httpx.Client(base_url=args.base_url, timeout=5.0) as client:
                health = assert_ok(client.get("/health"), "health")
                if not isinstance(health, dict) or not health.get("ok"):
                    raise RuntimeError(f"health returned not ok: {health}")

                book = assert_ok(
                    client.post(
                        "/books",
                        json={
                            "title": "V1.7 Audio Notes Smoke",
                            "source_kind": "epub",
                            "book_hash": book_hash,
                        },
                    ),
                    "book create",
                )
                assert isinstance(book, dict)
                book_id = book["id"]

                pending = assert_ok(
                    client.post(
                        "/audio-notes",
                        json={
                            "book_id": book_id,
                            "audio_path": str(audio_path),
                            "duration_seconds": 3.2,
                            "provider": "funasr",
                            "status": "pending",
                        },
                    ),
                    "audio note pending",
                )
                assert isinstance(pending, dict)
                if pending.get("status") != "pending":
                    raise RuntimeError(f"pending audio note status mismatch: {pending}")

                annotation = assert_ok(
                    client.post(
                        "/annotations",
                        json={
                            "book_id": book_id,
                            "kind": "note",
                            "source_text": "Voice source sentence.",
                            "note_text": "Voice transcript text.",
                            "chapter_locator": "voice/chapter.xhtml",
                        },
                    ),
                    "annotation create",
                )
                assert isinstance(annotation, dict)

                patched = assert_ok(
                    client.patch(
                        f"/audio-notes/{pending['id']}",
                        json={
                            "annotation_id": annotation["id"],
                            "provider": "funasr",
                            "transcript": "Voice transcript text.",
                            "raw_result": {"segments": 1},
                            "status": "transcribed",
                        },
                    ),
                    "audio note patch",
                )
                assert isinstance(patched, dict)
                if patched.get("status") != "transcribed" or patched.get("annotation_id") != annotation["id"]:
                    raise RuntimeError(f"audio note patch mismatch: {patched}")

                listed = assert_ok(client.get(f"/books/{book_id}/audio-notes"), "audio note list")
                assert isinstance(listed, list)
                if len(listed) != 1 or listed[0].get("transcript") != "Voice transcript text.":
                    raise RuntimeError(f"audio note list mismatch: {listed}")

        print("reader api audio notes smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader api audio notes smoke FAIL: {exc}")
        return 1
    finally:
        cleanup(args.database_url, book_id, book_hash)


if __name__ == "__main__":
    raise SystemExit(main())
