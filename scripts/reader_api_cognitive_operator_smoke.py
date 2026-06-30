#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reader_api.app import app


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


def write_ready_draft(cognitive_root: Path) -> Path:
    draft_dir = cognitive_root / "incoming" / "sentence_reader_drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / "reader_strategy_model.draft.json"
    draft = {
        "schema": "sentence_reader.book_intake_draft.v1",
        "draft_id": "draft_reader_strategy_model",
        "created_at": "2026-06-24T00:00:00+00:00",
        "source": {
            "app": "Sentence Reader",
            "sync_event_id": "sync_reader_strategy_model",
            "book_title": "Good Strategy Bad Strategy",
        },
        "book_intake_candidate": {
            "intake_id": "reader_strategy_model",
            "source_type": "book_note",
            "book": {
                "id": "good_strategy_bad_strategy",
                "title": "Good Strategy Bad Strategy",
                "author": "Richard Rumelt",
            },
            "note": {
                "content": "A good strategy starts from diagnosis before coherent action.",
                "user_interpretation": "When Hermes reviews reader notes, it should diagnose the core challenge before listing actions.",
                "why_it_matters": "This prevents shallow advice and keeps book-derived thinking tied to evidence.",
            },
            "target_scenarios": ["strategy", "ai_workflow"],
            "proposed_model": {
                "id": "diagnosis_before_action",
                "name": "Diagnosis Before Action",
                "solves": "Avoids jumping to tactics before understanding the constraint.",
                "judgement_steps": [
                    "Name the core challenge.",
                    "Separate symptoms from causes.",
                    "Choose a coherent action sequence.",
                ],
                "evidence_required": [
                    "Source sentence or user note.",
                    "Business context or project constraint.",
                ],
                "misuse_risks": [
                    "Over-diagnosing simple tasks.",
                    "Inventing evidence not present in the note.",
                ],
                "output_requirements": [
                    "State diagnosis.",
                    "State action sequence.",
                    "State uncertainty.",
                ],
            },
            "project_applications": ["Sentence Reader review flow"],
            "desired_hermes_behavior": "Use diagnosis before action when converting reader notes into decisions.",
        },
        "quality_gate": {
            "schema": "sentence_reader.reader_intake_quality_gate.v1",
            "status": "review_ready",
            "score": 0.92,
            "promotion_allowed": False,
            "failures": [],
            "warnings": [],
        },
        "promotion_target": {
            "active_pack_mutation": False,
            "requires_commanded_promotion": True,
        },
    }
    draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    return draft_path


def assert_ok(response, label: str) -> dict:
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"{label} failed: status={response.status_code} body={response.text}")
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise RuntimeError(f"{label} returned not ok: {payload}")
    return payload


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="sentence-reader-v20h-cognitive-api-") as tmp:
            cognitive_root = Path(tmp) / "hermes_cognitive_os"
            cognitive_root.mkdir(parents=True, exist_ok=True)
            copy_cognitive_build_support(cognitive_root)

            with TestClient(app) as client:
                queue = assert_ok(
                    client.post(
                        "/cognitive/review-queue",
                        json={"cognitive_os_dir": str(cognitive_root), "limit": 100},
                    ),
                    "review queue",
                )
                if queue.get("schema") != "sentence_reader.intake_review_queue.v1":
                    raise RuntimeError(f"queue schema mismatch: {queue}")
                if queue.get("draft_count") != 0 or queue.get("counts") != {}:
                    raise RuntimeError(f"empty queue mismatch: {queue}")
                if not Path(queue["report_path"]).exists() or not Path(queue["markdown_path"]).exists():
                    raise RuntimeError(f"queue report files missing: {queue}")

                dry_run = assert_ok(
                    client.post(
                        "/cognitive/operator/dry-run",
                        json={"cognitive_os_dir": str(cognitive_root), "all_ready": True, "allow_empty": True},
                    ),
                    "operator dry-run",
                )
                if dry_run.get("schema") != "sentence_reader.active_pack_operator_report.v1":
                    raise RuntimeError(f"operator schema mismatch: {dry_run}")
                if dry_run.get("status") != "dry_run" or dry_run.get("dry_run") is not True:
                    raise RuntimeError(f"operator was not dry-run only: {dry_run}")
                if dry_run.get("approved") is not False or dry_run.get("selected_count") != 0:
                    raise RuntimeError(f"operator dry-run safety mismatch: {dry_run}")
                if not Path(dry_run["report_path"]).exists():
                    raise RuntimeError(f"operator report missing: {dry_run}")

                draft_path = write_ready_draft(cognitive_root)
                queue_with_item = assert_ok(
                    client.post(
                        "/cognitive/review-queue",
                        json={"cognitive_os_dir": str(cognitive_root), "limit": 100},
                    ),
                    "review queue with item",
                )
                counts = queue_with_item.get("counts") or {}
                if counts.get("ready_to_approve") != 1:
                    raise RuntimeError(f"ready draft was not surfaced: {queue_with_item}")

                dashboard = assert_ok(
                    client.post(
                        "/cognitive/dashboard",
                        json={"cognitive_os_dir": str(cognitive_root), "limit": 100, "history_limit": 20},
                    ),
                    "cognitive dashboard",
                )
                if dashboard.get("schema") != "sentence_reader.cognitive_dashboard.v1":
                    raise RuntimeError(f"dashboard schema mismatch: {dashboard}")
                if dashboard.get("counts", {}).get("ready_to_approve") != 1:
                    raise RuntimeError(f"dashboard queue counts mismatch: {dashboard}")
                if not Path(dashboard["markdown_path"]).exists():
                    raise RuntimeError(f"dashboard markdown missing: {dashboard}")

                detail = assert_ok(
                    client.post(
                        "/cognitive/review-item",
                        json={"cognitive_os_dir": str(cognitive_root), "candidate_intake_id": "reader_strategy_model"},
                    ),
                    "review item",
                )
                if detail.get("schema") != "sentence_reader.cognitive_review_item.v1":
                    raise RuntimeError(f"detail schema mismatch: {detail}")
                if detail.get("approval_policy", {}).get("app_can_mutate_active_pack") is not False:
                    raise RuntimeError(f"detail approval policy unsafe: {detail.get('approval_policy')}")
                if detail.get("queue_item", {}).get("draft_path") != str(draft_path):
                    raise RuntimeError(f"detail selected wrong draft: {detail.get('queue_item')}")
                if not Path(detail["markdown_path"]).exists():
                    raise RuntimeError(f"detail markdown missing: {detail}")

                preflight = assert_ok(
                    client.post(
                        "/cognitive/operator/preflight",
                        json={
                            "cognitive_os_dir": str(cognitive_root),
                            "candidate_intake_ids": ["reader_strategy_model"],
                        },
                    ),
                    "operator preflight",
                )
                if preflight.get("status") != "dry_run" or preflight.get("selected_count") != 1:
                    raise RuntimeError(f"selected preflight mismatch: {preflight}")
                if preflight.get("approved") is not False:
                    raise RuntimeError(f"preflight should not approve writes: {preflight}")
                if list((cognitive_root / "intakes").glob("*.json")):
                    raise RuntimeError("preflight unexpectedly wrote formal intakes")

                rejected = client.post(
                    "/cognitive/operator/approve",
                    json={
                        "cognitive_os_dir": str(cognitive_root),
                        "candidate_intake_id": "reader_strategy_model",
                        "confirmation_text": "APPROVE wrong_model",
                    },
                )
                if rejected.status_code != 422:
                    raise RuntimeError(f"approval should reject bad confirmation: {rejected.status_code} {rejected.text}")

                approved = assert_ok(
                    client.post(
                        "/cognitive/operator/approve",
                        json={
                            "cognitive_os_dir": str(cognitive_root),
                            "candidate_intake_id": "reader_strategy_model",
                            "confirmation_text": "APPROVE reader_strategy_model",
                            "skip_quality_gate": True,
                            "skip_quality_gate_reason": "temporary smoke root does not carry the full quality gate fixture",
                        },
                    ),
                    "operator approve",
                )
                if approved.get("status") != "success" or approved.get("approved") is not True:
                    raise RuntimeError(f"approval result mismatch: {approved}")
                if approved.get("dry_run") is not False or approved.get("selected_count") != 1:
                    raise RuntimeError(f"approval should be one non-dry-run draft: {approved}")
                if not list((cognitive_root / "intakes").glob("reader_strategy_model.json")):
                    raise RuntimeError("approval did not write the formal intake")
                if not (cognitive_root / "compiled_packs" / "active_cognitive_pack.json").exists():
                    raise RuntimeError("approval did not rebuild active cognitive pack")
                rollback_manifest = Path(approved.get("rollback_manifest", {}).get("rollback_manifest_path", ""))
                if not rollback_manifest.exists():
                    raise RuntimeError(f"approval did not write rollback manifest: {approved.get('rollback_manifest')}")

                dashboard_after_approval = assert_ok(
                    client.post(
                        "/cognitive/dashboard",
                        json={"cognitive_os_dir": str(cognitive_root), "limit": 100, "history_limit": 20},
                    ),
                    "cognitive dashboard after approval",
                )
                history = dashboard_after_approval.get("approval_history") or []
                if not any(item.get("status") == "success" and item.get("approved") is True for item in history):
                    raise RuntimeError(f"dashboard did not surface approval history: {dashboard_after_approval}")
                markdown = Path(dashboard_after_approval["markdown_path"]).read_text(encoding="utf-8")
                if "Approval History" not in markdown or "Rollback" not in markdown:
                    raise RuntimeError(f"dashboard markdown missing history/rollback: {markdown[:600]}")

        print("reader api cognitive operator smoke PASS")
        return 0
    except Exception as exc:
        print(f"reader api cognitive operator smoke FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
