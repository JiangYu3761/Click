#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "reader" / "001_reader_schema.sql"
LIBRARY_MIGRATION = ROOT / "migrations" / "reader" / "002_library_ui.sql"
APP = ROOT / "reader_api" / "app.py"
CONFIG = ROOT / "reader_api" / "config.py"
REQUIREMENTS = ROOT / "requirements-reader-api.txt"
TESTS = ROOT / "tests" / "test_reader_api_mock.py"
STATUS = ROOT / "scripts" / "reader_pg_status.py"
LIVE_SMOKE = ROOT / "scripts" / "reader_api_live_smoke.py"
HTTP_SMOKE = ROOT / "scripts" / "reader_api_http_smoke.py"
NOTES_LOOP_SMOKE = ROOT / "scripts" / "reader_api_notes_loop_smoke.py"
MULTIBOOK_SMOKE = ROOT / "scripts" / "reader_api_multibook_smoke.py"
EXPORT_SMOKE = ROOT / "scripts" / "reader_api_export_smoke.py"
AUDIO_NOTES_SMOKE = ROOT / "scripts" / "reader_api_audio_notes_smoke.py"
HERMES_SYNC_SMOKE = ROOT / "scripts" / "reader_api_hermes_sync_smoke.py"
HERMES_INGEST_SMOKE = ROOT / "scripts" / "reader_api_hermes_ingest_smoke.py"
COGNITIVE_OPERATOR_SMOKE = ROOT / "scripts" / "reader_api_cognitive_operator_smoke.py"
IPAD_LAN_SMOKE = ROOT / "scripts" / "reader_api_ipad_lan_smoke.py"
V12_ACCEPTANCE = ROOT / "scripts" / "v12_data_acceptance.sh"
V14_ACCEPTANCE = ROOT / "scripts" / "v14_notes_acceptance.sh"

REQUIRED_TABLES = [
    "reader.books",
    "reader.book_files",
    "reader.chapters",
    "reader.sentences",
    "reader.annotations",
    "reader.reading_positions",
    "reader.audio_notes",
    "reader.exports",
    "reader.sync_events",
    "reader.library_state",
]

REQUIRED_ENDPOINT_MARKERS = [
    '@app.get("/health")',
    '@app.get("/library"',
    '@app.get("/api/library/dashboard")',
    '@app.post("/api/library/import")',
    '@app.post("/api/library/books/{book_id}/hide")',
    '@app.post("/api/library/books/{book_id}/reveal")',
    '@app.get("/lan/reader"',
    '@app.get("/lan/books")',
    '@app.get("/lan/books/{book_id}/manifest")',
    '@app.get("/lan/books/{book_id}/chapters/{chapter_index}")',
    '@app.get("/lan/books/{book_id}/asset/{asset_path:path}")',
    '@app.post("/lan/audio-notes/transcribe")',
    '@app.post("/books")',
    '@app.get("/books")',
    '@app.get("/books/{book_id}")',
    '@app.put("/books/{book_id}/position")',
    '@app.get("/books/{book_id}/position")',
    '@app.post("/sentences")',
    '@app.post("/annotations")',
    '@app.get("/books/{book_id}/annotations")',
    '@app.post("/books/{book_id}/export")',
    '@app.get("/books/{book_id}/exports")',
    '@app.post("/books/{book_id}/sync/hermes")',
    '@app.get("/books/{book_id}/sync-events")',
    '@app.post("/sync/hermes/ingest")',
    '@app.get("/cognitive/dashboard")',
    '@app.post("/cognitive/dashboard")',
    '@app.get("/cognitive/review-queue")',
    '@app.post("/cognitive/review-queue")',
    '@app.post("/cognitive/review-item")',
    '@app.post("/cognitive/operator/dry-run")',
    '@app.post("/cognitive/operator/preflight")',
    '@app.post("/cognitive/operator/approve")',
    '@app.post("/audio-notes")',
    '@app.patch("/audio-notes/{audio_note_id}")',
    '@app.get("/books/{book_id}/audio-notes")',
    '@app.patch("/annotations/{annotation_id}")',
    '@app.delete("/annotations/{annotation_id}")',
    '@app.post("/exports")',
]


def main() -> int:
    missing_files = [
        path
        for path in (
            MIGRATION,
            LIBRARY_MIGRATION,
            APP,
            CONFIG,
            REQUIREMENTS,
            TESTS,
            STATUS,
            LIVE_SMOKE,
            HTTP_SMOKE,
            NOTES_LOOP_SMOKE,
            MULTIBOOK_SMOKE,
            EXPORT_SMOKE,
            AUDIO_NOTES_SMOKE,
            HERMES_SYNC_SMOKE,
            HERMES_INGEST_SMOKE,
            COGNITIVE_OPERATOR_SMOKE,
            IPAD_LAN_SMOKE,
            V12_ACCEPTANCE,
            V14_ACCEPTANCE,
        )
        if not path.exists()
    ]
    if missing_files:
        print(f"reader api static FAIL missing_files={[str(path) for path in missing_files]}")
        return 1

    migration = MIGRATION.read_text(encoding="utf-8") + "\n" + LIBRARY_MIGRATION.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    requirements = REQUIREMENTS.read_text(encoding="utf-8")

    missing_tables = [table for table in REQUIRED_TABLES if table not in migration]
    missing_endpoints = [marker for marker in REQUIRED_ENDPOINT_MARKERS if marker not in app]
    tests = TESTS.read_text(encoding="utf-8")

    missing_requirements = [name for name in ("fastapi", "uvicorn", "psycopg", "pytest", "httpx") if name not in requirements]
    missing_test_markers = [
        marker
        for marker in (
            "test_health_uses_reader_database_contract",
            "test_book_sentence_note_position_crud_flow",
            "test_red_highlight_and_export_flow",
            "test_generated_markdown_json_export_flow",
            "test_audio_note_lifecycle",
            "test_multi_book_list_and_independent_state",
            "test_hermes_sync_payload_and_event_flow",
            "test_hermes_ingestion_worker_marks_pending_event_synced",
        )
        if marker not in tests
    ]

    if missing_tables or missing_endpoints or missing_requirements or missing_test_markers:
        print(
            "reader api static FAIL "
            f"missing_tables={missing_tables} "
            f"missing_endpoints={missing_endpoints} "
            f"missing_requirements={missing_requirements} "
            f"missing_test_markers={missing_test_markers}"
        )
        return 1

    print("reader api static PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
