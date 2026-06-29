#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sentence_reader_intake_draft.py"


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="sentence-reader-v20d-intake-draft-") as tmp:
            root = Path(tmp) / "hermes_cognitive_os"
            incoming = root / "incoming" / "sentence_reader"
            incoming.mkdir(parents=True, exist_ok=True)
            payload_path = incoming / "sync_smoke.payload.json"
            manifest_path = incoming / "sync_smoke.manifest.json"
            payload = {
                "schema": "sentence_reader.hermes_sync.v1",
                "generated_at": "2026-06-24T00:00:00+00:00",
                "source_app": "Sentence Reader",
                "target_system": "hermes_cognitive_os",
                "book": {
                    "title": "Good Strategy Bad Strategy",
                    "author": "Richard Rumelt",
                    "book_hash": "good-strategy-bad-strategy-smoke",
                },
                "annotation_count": 1,
                "annotations": [
                    {
                        "id": "ann_smoke",
                        "kind": "note",
                        "source_text": "A good strategy starts with a clear diagnosis of the challenge.",
                        "note_text": "Use diagnosis before action lists in Hermes answers.",
                        "chapter_title": "The Kernel",
                        "chapter_locator": "kernel.xhtml",
                        "sentence_index": "7",
                        "range_locator": {"sentenceIndex": "7"},
                    }
                ],
                "cognitive_contract": {
                    "purpose": "Turn verified reader annotations into source material.",
                    "rules": ["Do not mutate active pack from raw reader assets."],
                },
            }
            manifest = {
                "schema": "sentence_reader.hermes_ingestion_manifest.v1",
                "ingested_at": "2026-06-24T00:00:00+00:00",
                "source": {
                    "app": "Sentence Reader",
                    "sync_event_id": "sync_smoke",
                    "source_kind": "book",
                    "source_id": "book_smoke",
                    "source_payload_path": "/tmp/source.json",
                },
                "target": {
                    "system": "hermes_cognitive_os",
                    "queue": "incoming/sentence_reader",
                    "payload_path": str(payload_path),
                },
                "policy": {
                    "active_pack_mutation": False,
                    "requires_human_or_pipeline_review": True,
                    "reason": "Reader assets must be reviewed before active use.",
                },
                "summary": {"book_title": "Good Strategy Bad Strategy", "annotation_count": 1},
            }
            payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            report_path = root / "reports" / "intake_draft_report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--cognitive-os-dir",
                    str(root),
                    "--report",
                    str(report_path),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=20,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stdout)

            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("generated_count") != 1 or report.get("failed_count") != 0:
                raise RuntimeError(f"draft report mismatch: {report}")
            draft_path = Path(report["results"][0]["draft_path"])
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            if draft.get("schema") != "sentence_reader.book_intake_draft.v1":
                raise RuntimeError(f"draft schema mismatch: {draft}")
            if draft.get("promotion_status") != "needs_human_review":
                raise RuntimeError(f"draft promotion policy mismatch: {draft}")
            if draft.get("quality_gate", {}).get("promotion_allowed") is not False:
                raise RuntimeError(f"draft unexpectedly allows promotion: {draft}")
            candidate = draft.get("book_intake_candidate") or {}
            if candidate.get("book", {}).get("title") != "Good Strategy Bad Strategy":
                raise RuntimeError(f"candidate book mismatch: {candidate}")
            if "strategy" not in candidate.get("target_scenarios", []):
                raise RuntimeError(f"scenario inference missed strategy: {candidate}")
            formal_dir = root / "intakes"
            if formal_dir.exists() and list(formal_dir.glob("*.json")):
                raise RuntimeError("smoke should not create formal intakes")

        print("reader intake draft smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader intake draft smoke FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
