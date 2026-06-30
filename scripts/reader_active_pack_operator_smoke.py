#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRAFT_SCRIPT = ROOT / "scripts" / "sentence_reader_intake_draft.py"
OPERATOR_SCRIPT = ROOT / "scripts" / "sentence_reader_active_pack_operator.py"


def run_command(command: list[str], expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
    if expect_ok and result.returncode != 0:
        raise RuntimeError(result.stdout)
    if not expect_ok and result.returncode == 0:
        raise RuntimeError(f"command unexpectedly passed: {' '.join(command)}\n{result.stdout}")
    return result


def copy_cognitive_build_support(root: Path) -> None:
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "compile_cognitive_intake.py").write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not target or not target.exists():
        print("missing intake path")
        return 1
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("intake_id"):
        print("invalid intake")
        return 1
    print(json.dumps({"ok": True, "intake_id": data["intake_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
        encoding="utf-8",
    )
    (scripts_dir / "build_active_cognitive_pack.py").write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    intakes_dir = ROOT / "intakes"
    compiled_dir = ROOT / "compiled_packs"
    compiled_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for path in sorted(intakes_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        items.append({"path": str(path), "intake_id": data.get("intake_id"), "source_type": data.get("source_type")})
    pack = {
        "schema": "sentence_reader.active_cognitive_pack.smoke.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "intake_count": len(items),
        "items": items,
    }
    for name in ["active_cognitive_pack.json", "merged_active_pack_v1_5.json"]:
        (compiled_dir / name).write_text(json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(json.dumps({"ok": True, "intake_count": len(items)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
        encoding="utf-8",
    )
    (root / "routing_manifest.json").write_text(
        json.dumps(
            {
                "schema": "sentence_reader.cognitive_os_routing_manifest.smoke.v1",
                "routes": [{"source": "sentence_reader", "target": "intakes"}],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_payload_pair(root: Path) -> None:
    incoming = root / "incoming" / "sentence_reader"
    incoming.mkdir(parents=True, exist_ok=True)
    payload_path = incoming / "operator.payload.json"
    manifest_path = incoming / "operator.manifest.json"
    payload = {
        "schema": "sentence_reader.hermes_sync.v1",
        "generated_at": "2026-06-24T00:00:00+00:00",
        "source_app": "Sentence Reader",
        "target_system": "hermes_cognitive_os",
        "book": {
            "title": "Good Strategy Bad Strategy",
            "author": "Richard Rumelt",
            "book_hash": "good-strategy-operator-smoke",
        },
        "annotation_count": 1,
        "annotations": [
            {
                "id": "ann_operator",
                "kind": "note",
                "source_text": "A good strategy starts from diagnosis before coherent action.",
                "note_text": "Hermes should diagnose the challenge before listing actions.",
                "chapter_title": "Kernel",
                "chapter_locator": "kernel.xhtml",
                "sentence_index": "9",
                "range_locator": {"sentenceIndex": "9"},
            }
        ],
        "cognitive_contract": {"purpose": "Smoke test only."},
    }
    manifest = {
        "schema": "sentence_reader.hermes_ingestion_manifest.v1",
        "ingested_at": "2026-06-24T00:00:00+00:00",
        "source": {
            "app": "Sentence Reader",
            "sync_event_id": "operator",
            "source_kind": "book",
            "source_id": "book_operator",
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


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="sentence-reader-v20g-active-pack-") as tmp:
            cognitive = Path(tmp) / "hermes_cognitive_os"
            copy_cognitive_build_support(cognitive)
            write_payload_pair(cognitive)
            run_command([sys.executable, str(DRAFT_SCRIPT), "--cognitive-os-dir", str(cognitive)])

            blocked = run_command(
                [
                    sys.executable,
                    str(OPERATOR_SCRIPT),
                    "--cognitive-os-dir",
                    str(cognitive),
                    "--all-ready",
                    "--skip-quality-gate",
                ],
                expect_ok=False,
            )
            if "missing --approved" not in blocked.stdout:
                raise RuntimeError(f"operator should require approval: {blocked.stdout}")

            run_dir = cognitive / "operator_run"
            result = run_command(
                [
                    sys.executable,
                    str(OPERATOR_SCRIPT),
                    "--cognitive-os-dir",
                    str(cognitive),
                    "--all-ready",
                    "--approved",
                    "--skip-quality-gate",
                    "--run-dir",
                    str(run_dir),
                ]
            )
            report_path = run_dir / "active_pack_operator_report.json"
            if not report_path.exists():
                raise RuntimeError(f"missing operator report: {result.stdout}")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("schema") != "sentence_reader.active_pack_operator_report.v1":
                raise RuntimeError(f"operator schema mismatch: {report}")
            if report.get("status") != "success":
                raise RuntimeError(f"operator did not succeed: {report}")
            if report.get("selected_count") != 1:
                raise RuntimeError(f"operator selected count mismatch: {report}")
            if not report.get("active_pack_rebuild", {}).get("ok"):
                raise RuntimeError(f"active pack rebuild failed: {report.get('active_pack_rebuild')}")
            if not report.get("quality_gate", {}).get("skipped"):
                raise RuntimeError(f"quality gate should be explicitly skipped in smoke: {report.get('quality_gate')}")
            if not (cognitive / "compiled_packs" / "active_cognitive_pack.json").exists():
                raise RuntimeError("active pack was not built")
            if not list((cognitive / "intakes").glob("*.json")):
                raise RuntimeError("formal intake was not written")
            rollback_manifest = Path(report["rollback_manifest"]["rollback_manifest_path"])
            if not rollback_manifest.exists():
                raise RuntimeError("rollback manifest missing")

        print("reader active pack operator smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader active pack operator smoke FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
