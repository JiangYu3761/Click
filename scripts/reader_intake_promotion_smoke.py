#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRAFT_SCRIPT = ROOT / "scripts" / "sentence_reader_intake_draft.py"
PROMOTE_SCRIPT = ROOT / "scripts" / "sentence_reader_promote_intake_draft.py"


def run_command(command: list[str], expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    if expect_ok and result.returncode != 0:
        raise RuntimeError(result.stdout)
    if not expect_ok and result.returncode == 0:
        raise RuntimeError(f"command unexpectedly passed: {' '.join(command)}\n{result.stdout}")
    return result


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="sentence-reader-v20e-intake-promotion-") as tmp:
            root = Path(tmp) / "hermes_cognitive_os"
            incoming = root / "incoming" / "sentence_reader"
            incoming.mkdir(parents=True, exist_ok=True)
            payload_path = incoming / "sync_promotion.payload.json"
            manifest_path = incoming / "sync_promotion.manifest.json"
            payload = {
                "schema": "sentence_reader.hermes_sync.v1",
                "generated_at": "2026-06-24T00:00:00+00:00",
                "source_app": "Sentence Reader",
                "target_system": "hermes_cognitive_os",
                "book": {
                    "title": "Good Strategy Bad Strategy",
                    "author": "Richard Rumelt",
                    "book_hash": "good-strategy-promotion-smoke",
                },
                "annotation_count": 1,
                "annotations": [
                    {
                        "id": "ann_promotion",
                        "kind": "note",
                        "source_text": "A strategy coordinates policies and actions around a diagnosis.",
                        "note_text": "Hermes should diagnose before giving action lists.",
                        "chapter_title": "Kernel",
                        "chapter_locator": "kernel.xhtml",
                        "sentence_index": "11",
                        "range_locator": {"sentenceIndex": "11"},
                    }
                ],
                "cognitive_contract": {"purpose": "Smoke test only."},
            }
            manifest = {
                "schema": "sentence_reader.hermes_ingestion_manifest.v1",
                "ingested_at": "2026-06-24T00:00:00+00:00",
                "source": {
                    "app": "Sentence Reader",
                    "sync_event_id": "sync_promotion",
                    "source_kind": "book",
                    "source_id": "book_promotion",
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
                "summary": {"book_title": "Good Strategy Bad Strategy", "annotation_count": 1},
            }
            payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            run_command([sys.executable, str(DRAFT_SCRIPT), "--cognitive-os-dir", str(root)])
            drafts = sorted((root / "incoming" / "sentence_reader_drafts").glob("*.draft.json"))
            if len(drafts) != 1:
                raise RuntimeError(f"expected one draft, got {drafts}")

            blocked = run_command(
                [
                    sys.executable,
                    str(PROMOTE_SCRIPT),
                    "--cognitive-os-dir",
                    str(root),
                    "--draft",
                    str(drafts[0]),
                    "--skip-quality-gate",
                    "--no-report",
                ],
                expect_ok=False,
            )
            if "missing_approved_flag" not in blocked.stdout:
                raise RuntimeError(f"promotion should require approved flag: {blocked.stdout}")

            report_path = root / "reports" / "promotion_report.json"
            promoted = run_command(
                [
                    sys.executable,
                    str(PROMOTE_SCRIPT),
                    "--cognitive-os-dir",
                    str(root),
                    "--draft",
                    str(drafts[0]),
                    "--approved",
                    "--skip-quality-gate",
                    "--report",
                    str(report_path),
                ]
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("promoted_count") != 1 or report.get("failed_count") != 0:
                raise RuntimeError(f"promotion report mismatch: {report}\n{promoted.stdout}")
            target_path = Path(report["results"][0]["target_path"])
            if not target_path.exists():
                raise RuntimeError(f"formal intake missing: {target_path}")
            intake = json.loads(target_path.read_text(encoding="utf-8"))
            if intake.get("book", {}).get("title") != "Good Strategy Bad Strategy":
                raise RuntimeError(f"formal intake book mismatch: {intake}")
            if (root / "compiled_packs" / "active_cognitive_pack.json").exists():
                raise RuntimeError("smoke should not rebuild active pack unless requested")

        print("reader intake promotion smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader intake promotion smoke FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
