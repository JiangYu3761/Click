#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRAFT_SCRIPT = ROOT / "scripts" / "sentence_reader_intake_draft.py"
QUEUE_SCRIPT = ROOT / "scripts" / "sentence_reader_review_queue.py"


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout)
    return result


def write_payload_pair(incoming: Path, event_id: str, note_text: str | None) -> None:
    payload_path = incoming / f"{event_id}.payload.json"
    manifest_path = incoming / f"{event_id}.manifest.json"
    annotation = {
        "id": f"ann_{event_id}",
        "kind": "note" if note_text else "red_highlight",
        "source_text": "A good strategy starts from diagnosis before action.",
        "chapter_title": "Kernel",
        "chapter_locator": f"{event_id}.xhtml",
        "sentence_index": "3",
        "range_locator": {"sentenceIndex": "3"},
    }
    if note_text:
        annotation["note_text"] = note_text
    payload = {
        "schema": "sentence_reader.hermes_sync.v1",
        "generated_at": "2026-06-24T00:00:00+00:00",
        "source_app": "Sentence Reader",
        "target_system": "hermes_cognitive_os",
        "book": {
            "title": f"Good Strategy Bad Strategy {event_id}",
            "author": "Richard Rumelt",
            "book_hash": f"good-strategy-{event_id}",
        },
        "annotation_count": 1,
        "annotations": [annotation],
        "cognitive_contract": {"purpose": "Smoke test only."},
    }
    manifest = {
        "schema": "sentence_reader.hermes_ingestion_manifest.v1",
        "ingested_at": "2026-06-24T00:00:00+00:00",
        "source": {
            "app": "Sentence Reader",
            "sync_event_id": event_id,
            "source_kind": "book",
            "source_id": f"book_{event_id}",
        },
        "target": {
            "system": "hermes_cognitive_os",
            "queue": "incoming/sentence_reader",
            "payload_path": str(payload_path),
        },
        "policy": {
            "active_pack_mutation": False,
            "requires_human_or_pipeline_review": True,
            "reason": "Smoke test.",
        },
        "summary": {"book_title": payload["book"]["title"], "annotation_count": 1},
    }
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="sentence-reader-v20f-review-queue-") as tmp:
            root = Path(tmp) / "hermes_cognitive_os"
            incoming = root / "incoming" / "sentence_reader"
            incoming.mkdir(parents=True, exist_ok=True)
            write_payload_pair(incoming, "ready", "Diagnose first; then decide what action sequence is coherent.")
            write_payload_pair(incoming, "needs_review", None)

            run_command([sys.executable, str(DRAFT_SCRIPT), "--cognitive-os-dir", str(root)])
            report_path = root / "reports" / "queue.json"
            markdown_path = root / "reports" / "queue.md"
            run_command(
                [
                    sys.executable,
                    str(QUEUE_SCRIPT),
                    "--cognitive-os-dir",
                    str(root),
                    "--report",
                    str(report_path),
                    "--markdown",
                    str(markdown_path),
                ]
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("schema") != "sentence_reader.intake_review_queue.v1":
                raise RuntimeError(f"queue schema mismatch: {report}")
            counts = report.get("counts") or {}
            if counts.get("ready_to_approve") != 1 or counts.get("needs_review") != 1:
                raise RuntimeError(f"queue counts mismatch: {counts}")
            commands = [item.get("commands", {}).get("approve_rebuild_quality_gate", "") for item in report["items"]]
            if not all("--approved" in command for command in commands):
                raise RuntimeError(f"approval commands missing --approved: {commands}")
            if not all("--rebuild-active-pack" in command for command in commands):
                raise RuntimeError(f"approval commands missing rebuild gate: {commands}")
            markdown = markdown_path.read_text(encoding="utf-8")
            if "Sentence Reader Draft Review Queue" not in markdown or "ready_to_approve" not in markdown:
                raise RuntimeError(f"markdown queue incomplete: {markdown[:500]}")

        print("reader review queue smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader review queue smoke FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
