#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "lifestudy_vocab_review"
PIPELINE_DIR = ROOT / "reports" / "lifestudy_vocab_pipeline"
FIRST50_IMPORTABLE = PIPELINE_DIR / "01_Genesis-120-pages-1-50-importable.json"
FULL_IMPORTABLE = PIPELINE_DIR / "01_Genesis-120-pages-1-1255-importable.json"
REVIEW_PACK = REPORT_DIR / "Genesis-review-pack.json"
REVIEWED_OVERRIDES = REPORT_DIR / "Genesis-review-overrides.reviewed.json"
ASSISTANT_OVERRIDES = REPORT_DIR / "Genesis-review-overrides.assistant-suggested.json"
ASSISTANT_SUGGESTIONS = REPORT_DIR / "Genesis-review-suggestions.json"
WORD_REVIEW_PACK = REPORT_DIR / "Genesis-word-review-pack.json"
WORD_FREQUENCY_REPORT = REPORT_DIR / "Genesis-word-frequency.json"
PHRASE_UNCOMMON_PACK = REPORT_DIR / "Genesis-phrase-uncommon-pack.json"
DEFAULT_DATABASE_URL = "postgresql://localhost/jiangyu_os"
BOOK_ID = "book_e0679064039e4e298e9faf3127b65876"
REVIEWED_PRECISION_TARGET = 0.85


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def count_grades(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(item.get("quality_grade") or "") for item in items)
    return {grade: counts.get(grade, 0) for grade in ["A", "B", "C", "D"]}


def count_decisions(payload: dict[str, Any] | None) -> dict[str, int]:
    counts = Counter()
    for item in (payload or {}).get("items") or []:
        counts[str(item.get("decision") or "pending").strip().lower()] += 1
    return {key: counts.get(key, 0) for key in ["pending", "approve", "correct", "reject"]}


def reviewed_precision(decisions: dict[str, int]) -> float | None:
    total = sum(decisions.values())
    pending = decisions.get("pending", 0)
    if total <= 0 or pending:
        return None
    return (decisions.get("approve", 0) + decisions.get("correct", 0)) / total


def db_counts(database_url: str) -> dict[str, Any]:
    try:
        import psycopg
    except ImportError:
        return {"ok": False, "error": "psycopg_missing"}
    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                checks = {
                    "book_glossary": (
                        "select count(*) from reader.book_glossary where book_id=%s",
                        (BOOK_ID,),
                    ),
                    "book_vocab_items": (
                        "select count(*) from reader.book_vocab_items where book_id=%s",
                        (BOOK_ID,),
                    ),
                    "domain_active": (
                        "select count(*) from reader.domain_glossary_entries "
                        "where domain='lifestudy' and volume='Genesis' and status='active'",
                        (),
                    ),
                    "domain_hidden": (
                        "select count(*) from reader.domain_glossary_entries "
                        "where domain='lifestudy' and volume='Genesis' and status='hidden'",
                        (),
                    ),
                    "dictionary_pollution": (
                        "select count(*) from reader.dictionary_entries "
                        "where lower(coalesce(source,'')) like %s "
                        "or lower(coalesce(source,'')) like %s "
                        "or lower(coalesce(source,'')) like %s",
                        ("%lifestudy%", "%life-study%", "%lifestudy_context%"),
                    ),
                }
                result: dict[str, Any] = {"ok": True}
                for name, (sql, params) in checks.items():
                    cur.execute(sql, params)
                    result[name] = int(cur.fetchone()[0])
                return result
    except Exception as exc:  # pragma: no cover - smoke surfaces the message.
        return {"ok": False, "error": str(exc)}


def stage(name: str, passed: bool, detail: str, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "detail": detail,
        "metrics": metrics or {},
    }


def build_report(database_url: str) -> dict[str, Any]:
    first50 = load_json(FIRST50_IMPORTABLE)
    full = load_json(FULL_IMPORTABLE)
    review_pack = load_json(REVIEW_PACK)
    reviewed = load_json(REVIEWED_OVERRIDES)
    assistant_suggestions = load_json(ASSISTANT_SUGGESTIONS)
    assistant_overrides = load_json(ASSISTANT_OVERRIDES)
    word_review_pack = load_json(WORD_REVIEW_PACK)
    word_frequency = load_json(WORD_FREQUENCY_REPORT)
    phrase_uncommon_pack = load_json(PHRASE_UNCOMMON_PACK)
    db = db_counts(database_url)

    first50_items = list((first50 or {}).get("items") or [])
    full_items = list((full or {}).get("items") or [])
    review_quality = dict((review_pack or {}).get("quality") or {})
    reviewed_decisions = count_decisions(reviewed)
    human_precision = reviewed_precision(reviewed_decisions)
    assistant_decisions = count_decisions(assistant_overrides)
    assistant_dry_run = (assistant_suggestions or {}).get("assistant_suggested_dry_run", {}).get("result") or {}

    stages = [
        stage(
            "genesis_first_50",
            bool(first50 and first50.get("schema") == "sentence_reader.lifestudy_vocab_importable.v1" and len(first50_items) > 0),
            "Genesis first 50 pages importable pack exists and contains A/B candidates.",
            {"importable_count": len(first50_items), "grade_counts": count_grades(first50_items)},
        ),
        stage(
            "genesis_full_run",
            bool(full and full.get("schema") == "sentence_reader.lifestudy_vocab_importable.v1" and len(full_items) > 0),
            "Genesis full importable pack exists and remains no-write.",
            {"importable_count": len(full_items), "grade_counts": count_grades(full_items), "database_write_performed": (full or {}).get("database_write_performed")},
        ),
        stage(
            "controlled_import",
            bool(
                db.get("ok")
                and db.get("domain_active") == len(full_items)
                and db.get("book_glossary") >= len(full_items)
                and db.get("book_vocab_items") >= len(full_items)
                and db.get("dictionary_pollution") == 0
            ),
            "Only Genesis A/B entries are present in the Life-study domain/book boundary; general dictionary is clean.",
            db,
        ),
        stage(
            "frontend_lookup",
            bool(review_pack and review_quality.get("missing_book_row_count") == 0 and review_quality.get("dictionary_pollution_count") == 0),
            "Review pack confirms book rows exist and lookup boundary is clean.",
            {
                "review_term_count": review_quality.get("term_count"),
                "missing_book_row_count": review_quality.get("missing_book_row_count"),
                "dictionary_pollution_count": review_quality.get("dictionary_pollution_count"),
            },
        ),
        stage(
            "genesis_single_word_review_pack",
            bool(
                word_review_pack
                and word_review_pack.get("schema") == "sentence_reader.lifestudy_single_word_review_pack.v1"
                and word_review_pack.get("database_write_performed") is False
                and (word_review_pack.get("quality") or {}).get("word_candidate_count", 0) > 0
                and (word_review_pack.get("quality") or {}).get("import_ready_count") == 0
            ),
            "Genesis single-word candidates are extracted into a review-only pack; none are imported before review.",
            dict((word_review_pack or {}).get("quality") or {}),
        ),
        stage(
            "genesis_word_frequency_report",
            bool(
                word_frequency
                and word_frequency.get("schema") == "sentence_reader.lifestudy_word_frequency.v1"
                and word_frequency.get("database_write_performed") is False
                and (word_frequency.get("quality") or {}).get("content_unique_word_count", 0) > 0
            ),
            "Genesis all-word frequency report exists with aligned Chinese context and low-confidence local dictionary fallbacks.",
            dict((word_frequency or {}).get("quality") or {}),
        ),
        stage(
            "genesis_phrase_uncommon_pack",
            bool(
                phrase_uncommon_pack
                and phrase_uncommon_pack.get("schema") == "sentence_reader.lifestudy_phrase_uncommon_pack.v1"
                and phrase_uncommon_pack.get("database_write_performed") is False
                and (phrase_uncommon_pack.get("quality") or {}).get("active_high_confidence_phrase_count") == 25
                and (phrase_uncommon_pack.get("quality") or {}).get("uncommon_context_word_count") == 34
            ),
            "Genesis phrase and uncommon-word review document exists, combining active phrases, review phrases, and domain words.",
            dict((phrase_uncommon_pack or {}).get("quality") or {}),
        ),
        stage(
            "genesis_review_gate",
            bool(
                human_precision is not None
                and human_precision >= REVIEWED_PRECISION_TARGET
                and reviewed_decisions.get("pending", 0) == 0
                and db.get("ok")
                and db.get("dictionary_pollution") == 0
            ),
            "Expansion beyond Genesis requires reviewed decisions for every A/B entry and reviewed precision >= 0.85.",
            {
                "decision_counts": reviewed_decisions,
                "human_reviewed_precision": human_precision,
                "reviewed_precision_target": REVIEWED_PRECISION_TARGET,
                "assistant_suggested_decision_counts": assistant_decisions,
                "assistant_suggested_dry_run_can_expand": assistant_dry_run.get("can_expand_next_volume"),
                "assistant_suggestions_policy": (assistant_suggestions or {}).get("policy"),
                "single_word_review_pending_count": ((word_review_pack or {}).get("quality") or {}).get("needs_review_count"),
                "word_frequency_content_unique_count": ((word_frequency or {}).get("quality") or {}).get("content_unique_word_count"),
                "word_frequency_suggested_meaning_count": ((word_frequency or {}).get("quality") or {}).get("suggested_meaning_count"),
                "phrase_uncommon_total_count": ((phrase_uncommon_pack or {}).get("quality") or {}).get("total_item_count"),
            },
        ),
    ]

    first_failed = next((item for item in stages if not item["passed"]), None)
    completed = [item["name"] for item in stages if item["passed"]]
    blocked_stage = first_failed["name"] if first_failed else None
    can_expand = blocked_stage is None
    next_action = (
        "run_next_volume_controlled_probe"
        if can_expand
        else "finish_genesis_review_decisions_without_writing_low_confidence_terms"
    )
    report = {
        "schema": "sentence_reader.lifestudy_vocab_stage_gate.v1",
        "generated_at": now_iso(),
        "database_write_performed": False,
        "current_stage": "ready_for_next_volume_probe" if can_expand else blocked_stage,
        "completed_stages": completed,
        "blocked_stage": blocked_stage,
        "can_continue_automatically": can_expand,
        "can_expand_next_volume": can_expand,
        "next_safe_action": next_action,
        "strict_note": (
            "Assistant suggestions may accelerate review, but they are not human-reviewed accuracy. "
            "Do not expand beyond Genesis while genesis_review_gate is blocked."
        ),
        "stages": stages,
    }
    return report


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Life-study Vocabulary Stage Gate",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Current stage: `{report['current_stage']}`",
        f"- Can continue automatically: `{report['can_continue_automatically']}`",
        f"- Can expand next volume: `{report['can_expand_next_volume']}`",
        f"- Next safe action: `{report['next_safe_action']}`",
        "",
        "## Stages",
        "",
    ]
    for item in report["stages"]:
        mark = "PASS" if item["passed"] else "BLOCKED"
        lines.extend(
            [
                f"### {item['name']} - {mark}",
                "",
                item["detail"],
                "",
                "```json",
                json.dumps(item.get("metrics") or {}, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    database_url = os.getenv("READER_DATABASE_URL", DEFAULT_DATABASE_URL)
    report = build_report(database_url)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "Genesis-stage-gate.json"
    md_path = REPORT_DIR / "Genesis-stage-gate.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, md_path)
    print(json.dumps({"schema": report["schema"], "current_stage": report["current_stage"], "can_expand_next_volume": report["can_expand_next_volume"], "blocked_stage": report["blocked_stage"], "outputs": {"json": str(json_path), "markdown": str(md_path)}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
