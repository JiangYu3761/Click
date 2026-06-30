#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_COGNITIVE_OS_DIR = Path(
    str(Path.home() / "Library" / "Application Support" / "SentenceReader" / "CognitiveOS")
)
DRAFT_DIR = Path("incoming") / "sentence_reader_drafts"
REVIEW_QUEUE_DIR = Path("incoming") / "sentence_reader_drafts" / "review_queue"
FORMAL_INTAKE_DIR = Path("intakes")
PLACEHOLDER_MARKERS = [
    "Human review required",
    "待人工补充",
    "requires source text review",
]


class QueueError(ValueError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QueueError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise QueueError(f"expected JSON object: {path}")
    return data


def discover_drafts(root: Path) -> list[Path]:
    draft_dir = root / DRAFT_DIR
    if not draft_dir.exists():
        return []
    return sorted(draft_dir.glob("*.draft.json"))


def text_has_placeholder(value: Any) -> bool:
    text = str(value or "")
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


def candidate_placeholder_warnings(candidate: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    note = candidate.get("note") if isinstance(candidate.get("note"), dict) else {}
    for key in ["content", "user_interpretation", "why_it_matters"]:
        if text_has_placeholder(note.get(key)):
            warnings.append(f"candidate.note.{key}_placeholder")
    desired = candidate.get("desired_hermes_behavior")
    if text_has_placeholder(desired):
        warnings.append("candidate.desired_hermes_behavior_placeholder")
    return warnings


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
            failures.append(f"missing_candidate_{key}")
    book = candidate.get("book") if isinstance(candidate.get("book"), dict) else {}
    note = candidate.get("note") if isinstance(candidate.get("note"), dict) else {}
    model = candidate.get("proposed_model") if isinstance(candidate.get("proposed_model"), dict) else {}
    if not book.get("title"):
        failures.append("missing_book_title")
    if not note.get("content"):
        failures.append("missing_note_content")
    if not note.get("user_interpretation"):
        failures.append("missing_user_interpretation")
    if not note.get("why_it_matters"):
        failures.append("missing_why_it_matters")
    if not isinstance(candidate.get("target_scenarios"), list) or not candidate.get("target_scenarios"):
        failures.append("missing_target_scenarios")
    if not model.get("id") or not model.get("judgement_steps"):
        failures.append("missing_model_contract")
    return failures


def formal_target(root: Path, candidate: dict[str, Any], draft: dict[str, Any]) -> Path:
    promotion_target = draft.get("promotion_target") if isinstance(draft.get("promotion_target"), dict) else {}
    explicit = promotion_target.get("formal_intake_path")
    if explicit:
        return Path(str(explicit)).expanduser()
    intake_id = str(candidate.get("intake_id") or draft.get("draft_id") or "reader_intake").strip()
    return root / FORMAL_INTAKE_DIR / f"{intake_id}.json"


def classify_item(root: Path, draft_path: Path) -> dict[str, Any]:
    try:
        draft = load_json(draft_path)
    except Exception as exc:  # noqa: BLE001 - report bad drafts instead of stopping the queue.
        return {
            "draft_path": str(draft_path),
            "status": "blocked",
            "blocking_reasons": [f"{exc.__class__.__name__}: {exc}"],
            "warnings": [],
        }

    candidate = draft.get("book_intake_candidate") if isinstance(draft.get("book_intake_candidate"), dict) else {}
    quality = draft.get("quality_gate") if isinstance(draft.get("quality_gate"), dict) else {}
    target = formal_target(root, candidate, draft)
    failures: list[str] = []
    warnings: list[str] = []

    if draft.get("schema") != "sentence_reader.book_intake_draft.v1":
        failures.append("unsupported_draft_schema")
    if quality.get("promotion_allowed") is not False:
        failures.append("unsafe_quality_gate_allows_promotion")
    if (draft.get("promotion_target") or {}).get("active_pack_mutation") is not False:
        failures.append("unsafe_active_pack_mutation")
    quality_status = str(quality.get("status") or "missing")
    quality_failures = quality.get("failures") if isinstance(quality.get("failures"), list) else []
    quality_warnings = quality.get("warnings") if isinstance(quality.get("warnings"), list) else []
    failures.extend(str(item) for item in quality_failures)
    warnings.extend(str(item) for item in quality_warnings)
    failures.extend(candidate_failures(candidate))
    warnings.extend(candidate_placeholder_warnings(candidate))

    if target.exists():
        status = "already_promoted"
    elif failures or quality_status == "blocked":
        status = "blocked"
    elif quality_status == "review_ready" and not warnings:
        status = "ready_to_approve"
    else:
        status = "needs_review"

    promote_command = [
        "python3",
        "scripts/sentence_reader_promote_intake_draft.py",
        "--draft",
        str(draft_path),
        "--approved",
    ]
    promote_and_rebuild_command = promote_command + ["--rebuild-active-pack"]
    dry_run_command = promote_command + ["--dry-run"]
    if status == "needs_review":
        promote_command.append("--allow-needs-review")
        promote_and_rebuild_command.append("--allow-needs-review")
        dry_run_command.append("--allow-needs-review")

    book = candidate.get("book") if isinstance(candidate.get("book"), dict) else {}
    note = candidate.get("note") if isinstance(candidate.get("note"), dict) else {}
    model = candidate.get("proposed_model") if isinstance(candidate.get("proposed_model"), dict) else {}
    return {
        "draft_path": str(draft_path),
        "draft_id": draft.get("draft_id"),
        "status": status,
        "book_title": book.get("title") or draft.get("source", {}).get("book_title"),
        "source_sync_event_id": (draft.get("source") or {}).get("sync_event_id") if isinstance(draft.get("source"), dict) else None,
        "candidate_intake_id": candidate.get("intake_id"),
        "model_id": model.get("id"),
        "target_path": str(target),
        "quality_status": quality_status,
        "quality_score": quality.get("score"),
        "blocking_reasons": failures,
        "warnings": warnings,
        "source_excerpt": str(note.get("content") or "")[:260],
        "user_interpretation": str(note.get("user_interpretation") or "")[:260],
        "commands": {
            "dry_run": " ".join(dry_run_command),
            "approve_only": " ".join(promote_command),
            "approve_rebuild_quality_gate": " ".join(promote_and_rebuild_command),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Sentence Reader Draft Review Queue",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Draft count: {report['draft_count']}",
        f"- Ready: {report['counts'].get('ready_to_approve', 0)}",
        f"- Needs review: {report['counts'].get('needs_review', 0)}",
        f"- Blocked: {report['counts'].get('blocked', 0)}",
        f"- Already promoted: {report['counts'].get('already_promoted', 0)}",
        "",
        "## Items",
        "",
    ]
    if not report["items"]:
        lines.append("No draft items found.")
        return "\n".join(lines) + "\n"
    for index, item in enumerate(report["items"], start=1):
        lines.extend(
            [
                f"### {index}. {item.get('book_title') or item.get('draft_id')}",
                "",
                f"- Status: `{item['status']}`",
                f"- Draft: `{item.get('draft_path')}`",
                f"- Target: `{item.get('target_path')}`",
                f"- Quality: `{item.get('quality_status')}` / `{item.get('quality_score')}`",
                f"- Model: `{item.get('model_id')}`",
                "",
            ]
        )
        if item.get("source_excerpt"):
            lines.extend(["Source excerpt:", "", f"> {item['source_excerpt']}", ""])
        if item.get("user_interpretation"):
            lines.extend(["User interpretation:", "", item["user_interpretation"], ""])
        if item.get("blocking_reasons"):
            lines.extend(["Blocking reasons:", ""])
            lines.extend(f"- {reason}" for reason in item["blocking_reasons"])
            lines.append("")
        if item.get("warnings"):
            lines.extend(["Warnings:", ""])
            lines.extend(f"- {warning}" for warning in item["warnings"])
            lines.append("")
        lines.extend(["Suggested command:", "", f"```bash\n{item['commands']['approve_rebuild_quality_gate']}\n```", ""])
    return "\n".join(lines) + "\n"


def build_report(root: Path, limit: int) -> dict[str, Any]:
    draft_paths = discover_drafts(root)
    if limit > 0:
        draft_paths = draft_paths[:limit]
    items = [classify_item(root, path) for path in draft_paths]
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {
        "schema": "sentence_reader.intake_review_queue.v1",
        "generated_at": now_iso(),
        "cognitive_os_dir": str(root),
        "draft_dir": str(root / DRAFT_DIR),
        "review_queue_dir": str(root / REVIEW_QUEUE_DIR),
        "draft_count": len(items),
        "counts": counts,
        "items": items,
        "operator_rules": [
            "Do not approve blocked drafts.",
            "Prefer approving review_ready drafts with no placeholder warnings.",
            "For needs_review drafts, improve the note or pass --allow-needs-review intentionally.",
            "Use --rebuild-active-pack only after reviewing the formal intake output.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a review queue for Sentence Reader Cognitive OS intake drafts.")
    parser.add_argument("--cognitive-os-dir", default=str(DEFAULT_COGNITIVE_OS_DIR))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--markdown", default="")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()

    root = Path(args.cognitive_os_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else root / REVIEW_QUEUE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report).expanduser() if args.report else output_dir / "sentence_reader_review_queue.json"
    markdown_path = Path(args.markdown).expanduser() if args.markdown else output_dir / "sentence_reader_review_queue.md"

    report = build_report(root, args.limit)
    report["report_path"] = str(report_path)
    report["markdown_path"] = str(markdown_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["draft_count"] == 0 and not args.allow_empty:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
