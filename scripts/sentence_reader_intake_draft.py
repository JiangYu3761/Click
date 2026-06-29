#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_COGNITIVE_OS_DIR = Path(
    "/Users/jiangyu/Documents/Codex/2026-06-18/hermes-ai-q1-3-codernext-geminifour/outputs/hermes_cognitive_os"
)
INCOMING_DIR = Path("incoming") / "sentence_reader"
DRAFT_DIR = Path("incoming") / "sentence_reader_drafts"
FORMAL_INTAKE_DIR = Path("intakes")
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


class DraftError(ValueError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", text, flags=re.UNICODE).strip("-._")
    return slug[:80] or "reader"


def stable_id(*parts: Any) -> str:
    text = "-".join(str(part or "") for part in parts)
    slug = safe_slug(text).lower()
    slug = re.sub(r"[^a-z0-9_\-]+", "-", slug).strip("-_")
    return slug[:96] or "reader_intake_draft"


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DraftError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DraftError(f"expected JSON object: {path}")
    return payload


def truncate(text: Any, limit: int) -> str:
    value = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "..."


def first_text(values: list[Any]) -> str:
    for value in values:
        text = truncate(value, 2000)
        if text:
            return text
    return ""


def annotation_locator(annotation: dict[str, Any]) -> str:
    locator = annotation.get("chapter_locator") or ""
    chapter = annotation.get("chapter_title") or ""
    sentence_index = annotation.get("sentence_index") or ""
    range_locator = annotation.get("range_locator") if isinstance(annotation.get("range_locator"), dict) else {}
    if not sentence_index:
        sentence_index = range_locator.get("sentenceIndex") or range_locator.get("sentence_index") or ""
    pieces = [str(item) for item in [chapter, locator, sentence_index] if item not in {None, ""}]
    return "#".join(pieces)


def infer_scenarios(text: str) -> list[str]:
    lowered = text.lower()
    scenarios: list[str] = []
    keyword_map = [
        ("ads_analysis", ["ad", "ads", "advertising", "bid", "ctr", "cpc", "acos", "roas", "listing", "search term", "keyword", "amazon", "广告", "搜索词", "竞价", "点击率"]),
        ("douyin_content", ["douyin", "tiktok", "content", "hook", "retention", "抖音", "短视频", "选题", "完播", "脚本"]),
        ("strategy", ["strategy", "moat", "positioning", "战略", "定位", "竞争", "护城河"]),
        ("product_definition", ["product", "用户", "需求", "pain", "产品", "场景"]),
        ("ai_workflow", ["ai", "prompt", "workflow", "agent", "model", "llm", "自动化", "工作流", "模型"]),
        ("management", ["management", "team", "process", "管理", "团队", "流程"]),
    ]
    for scenario, keywords in keyword_map:
        if any(keyword in lowered or keyword in text for keyword in keywords):
            scenarios.append(scenario)
    return [item for item in scenarios if item in VALID_TASK_TYPES] or ["ai_workflow"]


def choose_primary_annotation(payload: dict[str, Any]) -> dict[str, Any]:
    annotations = payload.get("annotations")
    if not isinstance(annotations, list) or not annotations:
        raise DraftError("sync payload has no annotations")
    candidates = [item for item in annotations if isinstance(item, dict)]
    if not candidates:
        raise DraftError("sync payload annotations are invalid")
    noted = [item for item in candidates if truncate(item.get("note_text"), 2000)]
    return noted[0] if noted else candidates[0]


def build_candidate(draft_id: str, manifest: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    book = payload.get("book") if isinstance(payload.get("book"), dict) else {}
    annotation = choose_primary_annotation(payload)
    source_text = first_text(
        [
            annotation.get("source_text"),
            (annotation.get("evidence_unit") or {}).get("source_sentence") if isinstance(annotation.get("evidence_unit"), dict) else "",
        ]
    )
    note_text = first_text([annotation.get("note_text"), (annotation.get("evidence_unit") or {}).get("note") if isinstance(annotation.get("evidence_unit"), dict) else ""])
    book_title = truncate(book.get("title"), 160) or truncate((manifest.get("summary") or {}).get("book_title"), 160) or "Untitled reader note"
    book_id = stable_id(book.get("book_hash") or book_title)
    source_type = "book_note" if note_text else "highlight"
    combined_text = " ".join([book_title, source_text, note_text])
    scenarios = infer_scenarios(combined_text)

    return {
        "intake_id": draft_id,
        "source_type": source_type,
        "book": {
            "id": book_id,
            "title": book_title,
            "author": truncate(book.get("author"), 160) or "User to confirm",
        },
        "note": {
            "chapter": truncate(annotation.get("chapter_title") or annotation.get("chapter_locator"), 160),
            "location": truncate(annotation_locator(annotation), 200) or "Reader annotation",
            "content": truncate(source_text or note_text or "Reader annotation requires source text review.", 1200),
            "user_interpretation": truncate(note_text, 1200) or "Human review required: explain why this excerpt changes judgement.",
            "why_it_matters": truncate(note_text, 1200) or "Human review required: decide how this reading asset should change a project decision.",
        },
        "target_scenarios": scenarios,
        "proposed_model": {
            "id": f"{book_id}_reader_note_model",
            "name": "Reader note model draft",
            "solves": "Turn one reviewed reader annotation into a reusable judgement model without overclaiming from a single excerpt.",
            "judgement_steps": [
                "Verify the source sentence and locator before using the note.",
                "Separate the user's interpretation from what the book directly supports.",
                "Name the project scenario where this model should change a decision.",
                "Keep uncertainty explicit until more notes or cases support the model.",
            ],
            "evidence_required": [
                "source sentence",
                "user note or interpretation",
                "chapter locator or sentence index",
            ],
            "misuse_risks": [
                "Over-generalizing one excerpt into a permanent rule.",
                "Letting a highlight without user interpretation enter the active cognitive pack.",
            ],
            "output_requirements": [
                "Keep source text and locator visible.",
                "Mark the draft as review-required until promoted.",
                "State the next human review action.",
            ],
        },
        "project_applications": [
            {
                "project": "Hermes Cognitive OS",
                "rule": "Treat this as a reader-intake draft; do not promote it to active pack until a human or quality gate approves it.",
            }
        ],
        "desired_hermes_behavior": "Use this reading asset as evidence only after review; ask for missing interpretation when the note is ambiguous.",
    }


def validate_candidate(candidate: dict[str, Any]) -> list[str]:
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
            failures.append(f"missing candidate.{key}")
    if not re.match(r"^[a-z0-9_\-]+$", str(candidate.get("intake_id") or "")):
        failures.append("candidate.intake_id is not compile-safe")
    book = candidate.get("book") if isinstance(candidate.get("book"), dict) else {}
    note = candidate.get("note") if isinstance(candidate.get("note"), dict) else {}
    model = candidate.get("proposed_model") if isinstance(candidate.get("proposed_model"), dict) else {}
    if not book.get("id") or not book.get("title"):
        failures.append("candidate.book.id/title missing")
    if not note.get("content") or len(str(note.get("content"))) > 1200:
        failures.append("candidate.note.content invalid")
    if not note.get("user_interpretation") or not note.get("why_it_matters"):
        failures.append("candidate.note review fields missing")
    scenarios = candidate.get("target_scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        failures.append("candidate.target_scenarios missing")
    elif any(item not in VALID_TASK_TYPES for item in scenarios):
        failures.append("candidate.target_scenarios has invalid values")
    for key in ["id", "name", "solves", "judgement_steps", "evidence_required", "misuse_risks", "output_requirements"]:
        if not model.get(key):
            failures.append(f"candidate.proposed_model.{key} missing")
    return failures


def quality_gate(manifest: dict[str, Any], payload: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    score = 0

    if manifest.get("schema") == "sentence_reader.hermes_ingestion_manifest.v1":
        score += 10
    else:
        failures.append("unsupported_manifest_schema")

    if payload.get("schema") == "sentence_reader.hermes_sync.v1":
        score += 10
    else:
        failures.append("unsupported_payload_schema")

    if ((manifest.get("policy") or {}).get("active_pack_mutation")) is False:
        score += 10
    else:
        failures.append("unsafe_manifest_allows_active_pack_mutation")

    annotations = [item for item in payload.get("annotations", []) if isinstance(item, dict)] if isinstance(payload.get("annotations"), list) else []
    if annotations:
        score += 10
    else:
        failures.append("missing_annotations")

    book = payload.get("book") if isinstance(payload.get("book"), dict) else {}
    if truncate(book.get("title"), 200) or truncate((manifest.get("summary") or {}).get("book_title"), 200):
        score += 10
    else:
        failures.append("missing_book_title")

    if any(truncate(item.get("source_text") or ((item.get("evidence_unit") or {}).get("source_sentence") if isinstance(item.get("evidence_unit"), dict) else ""), 2000) for item in annotations):
        score += 15
    else:
        failures.append("missing_source_sentence")

    if any(truncate(item.get("note_text") or ((item.get("evidence_unit") or {}).get("note") if isinstance(item.get("evidence_unit"), dict) else ""), 2000) for item in annotations):
        score += 15
    else:
        warnings.append("missing_user_note_or_interpretation")

    if any(annotation_locator(item) for item in annotations):
        score += 10
    else:
        warnings.append("missing_locator")

    candidate_failures = validate_candidate(candidate)
    if not candidate_failures:
        score += 10
    else:
        failures.extend(candidate_failures)

    if not failures and score >= 80:
        status = "review_ready"
    elif not failures:
        status = "needs_review"
    else:
        status = "blocked"

    return {
        "schema": "sentence_reader.reader_intake_quality_gate.v1",
        "status": status,
        "score": score,
        "max_score": 100,
        "failures": failures,
        "warnings": warnings,
        "promotion_allowed": False,
        "promotion_reason": "Drafts must be reviewed before moving into hermes_cognitive_os/intakes or active pack.",
    }


def build_draft(manifest_path: Path, cognitive_os_dir: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    if manifest.get("schema") != "sentence_reader.hermes_ingestion_manifest.v1":
        raise DraftError(f"unsupported manifest schema: {manifest_path}")
    payload_path = Path(str(((manifest.get("target") or {}).get("payload_path") or ""))).expanduser()
    if not payload_path.is_absolute():
        payload_path = (manifest_path.parent / payload_path).resolve()
    payload = load_json(payload_path)
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    book = payload.get("book") if isinstance(payload.get("book"), dict) else {}
    draft_id = stable_id("reader", book.get("book_hash") or book.get("title"), source.get("sync_event_id") or manifest_path.stem)
    candidate = build_candidate(draft_id, manifest, payload)
    gate = quality_gate(manifest, payload, candidate)
    formal_target = cognitive_os_dir / FORMAL_INTAKE_DIR / f"{draft_id}.json"
    return {
        "schema": "sentence_reader.book_intake_draft.v1",
        "draft_id": draft_id,
        "created_at": now_iso(),
        "promotion_status": "needs_human_review",
        "source": {
            "manifest_path": str(manifest_path),
            "payload_path": str(payload_path),
            "sync_event_id": source.get("sync_event_id"),
            "book_title": (book.get("title") or (manifest.get("summary") or {}).get("book_title")),
        },
        "quality_gate": gate,
        "book_intake_candidate": candidate,
        "promotion_target": {
            "formal_intake_path": str(formal_target),
            "active_pack_mutation": False,
            "requires_commanded_promotion": True,
        },
        "review_checklist": [
            "Confirm the source sentence is a fair excerpt.",
            "Add or improve the user's interpretation if the draft used placeholders.",
            "Name exactly one judgement model this note should add or refine.",
            "Choose the project scenarios where Hermes should apply it.",
            "Only then move the candidate into hermes_cognitive_os/intakes and rebuild the active pack.",
        ],
    }


def draft_filename(draft: dict[str, Any]) -> str:
    return f"{stable_id(draft.get('draft_id'))}.draft.json"


def discover_manifests(incoming_dir: Path) -> list[Path]:
    if not incoming_dir.exists():
        return []
    return sorted(incoming_dir.glob("*.manifest.json"))


def run(cognitive_os_dir: Path, output_dir: Path | None, limit: int, allow_empty: bool) -> tuple[int, dict[str, Any]]:
    incoming_dir = cognitive_os_dir / INCOMING_DIR
    drafts_dir = output_dir or (cognitive_os_dir / DRAFT_DIR)
    manifests = discover_manifests(incoming_dir)
    if limit > 0:
        manifests = manifests[:limit]

    drafts_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for manifest_path in manifests:
        try:
            draft = build_draft(manifest_path, cognitive_os_dir)
            draft_path = drafts_dir / draft_filename(draft)
            draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            results.append(
                {
                    "manifest_path": str(manifest_path),
                    "draft_path": str(draft_path),
                    "draft_id": draft["draft_id"],
                    "quality_status": draft["quality_gate"]["status"],
                    "score": draft["quality_gate"]["score"],
                    "ok": True,
                }
            )
        except Exception as exc:  # noqa: BLE001 - continue per incoming asset.
            results.append({"manifest_path": str(manifest_path), "ok": False, "error": f"{exc.__class__.__name__}: {exc}"})

    ok_count = sum(1 for item in results if item.get("ok"))
    failed_count = sum(1 for item in results if not item.get("ok"))
    report = {
        "schema": "sentence_reader.intake_draft_report.v1",
        "generated_at": now_iso(),
        "cognitive_os_dir": str(cognitive_os_dir),
        "incoming_dir": str(incoming_dir),
        "drafts_dir": str(drafts_dir),
        "formal_intake_dir": str(cognitive_os_dir / FORMAL_INTAKE_DIR),
        "active_pack_mutation": False,
        "discovered_count": len(manifests),
        "generated_count": ok_count,
        "failed_count": failed_count,
        "results": results,
    }
    if not results and not allow_empty:
        return 2, report
    return (0 if failed_count == 0 else 1), report


def main() -> int:
    parser = argparse.ArgumentParser(description="Create reviewable Hermes book-intake drafts from Sentence Reader incoming assets.")
    parser.add_argument("--cognitive-os-dir", default=str(DEFAULT_COGNITIVE_OS_DIR))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--report", default="")
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()

    cognitive_os_dir = Path(args.cognitive_os_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else None
    code, report = run(cognitive_os_dir, output_dir, args.limit, args.allow_empty)
    if args.report:
        report_path = Path(args.report).expanduser()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
