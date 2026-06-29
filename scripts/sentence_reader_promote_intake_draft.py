#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_COGNITIVE_OS_DIR = Path(
    "/Users/jiangyu/Documents/Codex/2026-06-18/hermes-ai-q1-3-codernext-geminifour/outputs/hermes_cognitive_os"
)
DRAFT_DIR = Path("incoming") / "sentence_reader_drafts"
FORMAL_INTAKE_DIR = Path("intakes")
PROMOTION_REPORT_DIR = Path("incoming") / "sentence_reader_drafts" / "promotions"
VALID_TASK_TYPES = {
    "strategy",
    "moat",
    "ads_analysis",
    "douyin_content",
    "user_research",
    "product_definition",
    "operations_bottleneck",
    "management",
    "decision_bias",
    "ai_workflow",
    "coding",
}


class PromotionError(ValueError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PromotionError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PromotionError(f"expected JSON object: {path}")
    return data


def safe_intake_id(value: Any) -> str:
    raw = str(value or "").strip().lower()
    cleaned = re.sub(r"[^a-z0-9_\-]+", "-", raw).strip("-_")
    if not cleaned:
        raise PromotionError("missing intake_id")
    return cleaned[:120]


def candidate_failures(candidate: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    required = [
        "intake_id",
        "source_type",
        "book",
        "note",
        "target_scenarios",
        "proposed_model",
        "project_applications",
        "desired_hermes_behavior",
    ]
    for key in required:
        if key not in candidate:
            failures.append(f"missing {key}")
    if not re.match(r"^[a-z0-9_\-]+$", str(candidate.get("intake_id") or "")):
        failures.append("intake_id must be lowercase letters, numbers, hyphen or underscore")

    book = candidate.get("book") if isinstance(candidate.get("book"), dict) else {}
    note = candidate.get("note") if isinstance(candidate.get("note"), dict) else {}
    model = candidate.get("proposed_model") if isinstance(candidate.get("proposed_model"), dict) else {}
    scenarios = candidate.get("target_scenarios")

    if not book.get("id") or not book.get("title"):
        failures.append("book.id/title missing")
    content = str(note.get("content") or "")
    if not content or len(content) > 1200:
        failures.append("note.content missing or too long")
    if not note.get("user_interpretation"):
        failures.append("note.user_interpretation missing")
    if not note.get("why_it_matters"):
        failures.append("note.why_it_matters missing")
    if not isinstance(scenarios, list) or not scenarios:
        failures.append("target_scenarios missing")
    elif any(item not in VALID_TASK_TYPES for item in scenarios):
        failures.append("target_scenarios invalid")
    for key in ["id", "name", "solves", "judgement_steps", "evidence_required", "misuse_risks", "output_requirements"]:
        if not model.get(key):
            failures.append(f"proposed_model.{key} missing")
    for key in ["judgement_steps", "evidence_required", "misuse_risks", "output_requirements"]:
        if model.get(key) is not None and not isinstance(model.get(key), list):
            failures.append(f"proposed_model.{key} must be a list")
    return failures


def discover_drafts(root: Path) -> list[Path]:
    draft_dir = root / DRAFT_DIR
    if not draft_dir.exists():
        return []
    return sorted(draft_dir.glob("*.draft.json"))


def is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def target_for_candidate(root: Path, candidate: dict[str, Any]) -> Path:
    intake_id = safe_intake_id(candidate.get("intake_id"))
    return root / FORMAL_INTAKE_DIR / f"{intake_id}.json"


def evaluate_draft(
    draft_path: Path,
    root: Path,
    approved: bool,
    allow_needs_review: bool,
    overwrite: bool,
) -> dict[str, Any]:
    draft = load_json(draft_path)
    failures: list[str] = []
    warnings: list[str] = []

    if draft.get("schema") != "sentence_reader.book_intake_draft.v1":
        failures.append("unsupported_draft_schema")
    if not approved:
        failures.append("missing_approved_flag")

    quality = draft.get("quality_gate") if isinstance(draft.get("quality_gate"), dict) else {}
    quality_status = str(quality.get("status") or "")
    if quality_status == "blocked":
        failures.append("quality_gate_blocked")
    elif quality_status != "review_ready" and not allow_needs_review:
        failures.append(f"quality_gate_not_review_ready:{quality_status or 'missing'}")

    promotion_target = draft.get("promotion_target") if isinstance(draft.get("promotion_target"), dict) else {}
    if promotion_target.get("active_pack_mutation") is not False:
        failures.append("draft_allows_active_pack_mutation")
    if promotion_target.get("requires_commanded_promotion") is not True:
        failures.append("draft_missing_commanded_promotion_policy")

    candidate = draft.get("book_intake_candidate")
    if not isinstance(candidate, dict):
        failures.append("missing_book_intake_candidate")
        candidate = {}
    failures.extend(candidate_failures(candidate))

    target_path = target_for_candidate(root, candidate)
    if not is_under(target_path, root / FORMAL_INTAKE_DIR):
        failures.append("target_path_outside_intakes")
    if target_path.exists() and not overwrite:
        failures.append("target_intake_exists")

    if quality_status == "needs_review" and allow_needs_review:
        warnings.append("promoting_needs_review_draft_by_explicit_override")

    return {
        "draft_path": str(draft_path),
        "draft_id": draft.get("draft_id"),
        "quality_status": quality_status,
        "quality_score": quality.get("score"),
        "candidate_intake_id": candidate.get("intake_id"),
        "target_path": str(target_path),
        "failures": failures,
        "warnings": warnings,
        "ok": not failures,
        "candidate": candidate,
    }


def write_candidate(result: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        return
    target_path = Path(result["target_path"])
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(result["candidate"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_rebuild(root: Path) -> dict[str, Any]:
    script = root / "scripts" / "build_active_cognitive_pack.py"
    if not script.exists():
        return {"ok": False, "skipped": True, "reason": f"missing {script}"}
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
    return {"ok": result.returncode == 0, "returncode": result.returncode, "output": result.stdout}


def run_quality_gate(root: Path) -> dict[str, Any]:
    script = root / "v2_book_intake_quality_gate.py"
    if not script.exists():
        return {"ok": False, "skipped": True, "reason": f"missing {script}"}
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
    return {"ok": result.returncode == 0, "returncode": result.returncode, "output": result.stdout}


def report_path(root: Path) -> Path:
    return root / PROMOTION_REPORT_DIR / f"promotion_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"


def run(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    root = Path(args.cognitive_os_dir).expanduser()
    draft_paths = [Path(item).expanduser() for item in args.draft]
    if args.all_review_ready:
        draft_paths.extend(discover_drafts(root))
    draft_paths = sorted(dict.fromkeys(path.resolve() for path in draft_paths))

    results = [
        evaluate_draft(
            path,
            root=root,
            approved=args.approved,
            allow_needs_review=args.allow_needs_review,
            overwrite=args.overwrite,
        )
        for path in draft_paths
    ]

    promoted = 0
    for result in results:
        if result["ok"]:
            write_candidate(result, dry_run=args.dry_run)
            promoted += 0 if args.dry_run else 1

    failed = sum(1 for item in results if not item["ok"])
    rebuild = {"ok": False, "skipped": True, "reason": "not requested"}
    quality_gate = {"ok": False, "skipped": True, "reason": "not requested"}
    if args.rebuild_active_pack and not args.dry_run and failed == 0 and results:
        rebuild = run_rebuild(root)
        if rebuild.get("ok") and not args.skip_quality_gate:
            quality_gate = run_quality_gate(root)
        elif args.skip_quality_gate:
            quality_gate = {"ok": True, "skipped": True, "reason": "skip_quality_gate requested"}

    report = {
        "schema": "sentence_reader.intake_draft_promotion_report.v1",
        "generated_at": now_iso(),
        "cognitive_os_dir": str(root),
        "draft_count": len(results),
        "promoted_count": promoted,
        "failed_count": failed,
        "dry_run": args.dry_run,
        "approved": args.approved,
        "allow_needs_review": args.allow_needs_review,
        "overwrite": args.overwrite,
        "active_pack_rebuild_requested": args.rebuild_active_pack,
        "active_pack_rebuild": rebuild,
        "quality_gate": quality_gate,
        "results": [
            {key: value for key, value in result.items() if key != "candidate"}
            for result in results
        ],
    }
    if args.report:
        output = Path(args.report).expanduser()
    else:
        output = report_path(root)
    if not args.no_report:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["report_path"] = str(output)

    if not results:
        return (0 if args.allow_empty else 2), report
    if failed:
        return 1, report
    if args.rebuild_active_pack and not args.dry_run:
        if not rebuild.get("ok") or not quality_gate.get("ok"):
            return 3, report
    return 0, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote reviewed Sentence Reader intake drafts into formal Hermes Cognitive OS intakes.")
    parser.add_argument("--cognitive-os-dir", default=str(DEFAULT_COGNITIVE_OS_DIR))
    parser.add_argument("--draft", action="append", default=[], help="Draft JSON path. Can be passed more than once.")
    parser.add_argument("--all-review-ready", action="store_true", help="Discover all drafts in incoming/sentence_reader_drafts.")
    parser.add_argument("--approved", action="store_true", help="Required to write formal intakes.")
    parser.add_argument("--allow-needs-review", action="store_true", help="Override quality status needs_review. Blocked drafts still fail.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rebuild-active-pack", action="store_true")
    parser.add_argument("--skip-quality-gate", action="store_true")
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--report", default="")
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args()

    code, report = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
