#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_PACK = ROOT / "reports" / "lifestudy_vocab_review" / "Genesis-review-pack.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "lifestudy_vocab_review"
APPLY_SCRIPT = ROOT / "scripts" / "lifestudy_context_vocab_apply_review.py"

SUGGESTED_CORRECTIONS = {
    "light and darkness": "光和黑暗",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_term(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def load_review_pack(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_vocab_review_pack.v1":
        raise SystemExit(f"unexpected review pack schema: {payload.get('schema')}")
    if payload.get("database_write_performed") is not False:
        raise SystemExit("refusing suggestions: review pack must be a no-write report")
    return payload


def suggest_item(item: dict[str, Any]) -> dict[str, Any]:
    term = normalize_term(str(item.get("term") or ""))
    grade = str(item.get("quality_grade") or "")
    meaning = str(item.get("current_meaning_zh") or "")
    evidence_zh = str(item.get("evidence_zh_simp") or "")
    flags = list(item.get("machine_flags") or [])
    if term in SUGGESTED_CORRECTIONS:
        corrected = SUGGESTED_CORRECTIONS[term]
        return {
            "term": term,
            "suggested_decision": "correct",
            "suggested_corrected_meaning_zh": corrected,
            "suggestion_confidence": "medium",
            "rationale": f"Chinese evidence contains a more literal phrase than the current shorthand: {corrected}.",
        }
    if grade == "A" and not flags and meaning and meaning in evidence_zh:
        return {
            "term": term,
            "suggested_decision": "approve",
            "suggested_corrected_meaning_zh": "",
            "suggestion_confidence": "high",
            "rationale": "Grade A, no machine flags, and current meaning appears in the aligned Chinese evidence.",
        }
    if grade == "B" and meaning and meaning in evidence_zh and set(flags).issubset({"grade_b_sample_required"}):
        return {
            "term": term,
            "suggested_decision": "approve",
            "suggested_corrected_meaning_zh": "",
            "suggestion_confidence": "medium",
            "rationale": "Grade B requires sampling, but the current meaning appears in the aligned Chinese evidence.",
        }
    return {
        "term": term,
        "suggested_decision": "pending",
        "suggested_corrected_meaning_zh": "",
        "suggestion_confidence": "low",
        "rationale": "Evidence is not strong enough for an assistant suggestion; keep manual review.",
    }


def build_outputs(review_pack: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    override_items: list[dict[str, Any]] = []
    for raw in review_pack.get("items") or []:
        suggestion = suggest_item(raw)
        merged = {
            **suggestion,
            "quality_grade": raw.get("quality_grade"),
            "current_meaning_zh": raw.get("current_meaning_zh") or "",
            "source_page": raw.get("source_page"),
            "evidence_en": raw.get("evidence_en") or "",
            "evidence_zh_simp": raw.get("evidence_zh_simp") or "",
            "machine_flags": raw.get("machine_flags") or [],
        }
        items.append(merged)
        note = f"assistant suggestion; not human-reviewed. {suggestion['rationale']}"
        override_items.append(
            {
                "term": suggestion["term"],
                "current_meaning_zh": raw.get("current_meaning_zh") or "",
                "decision": suggestion["suggested_decision"],
                "corrected_meaning_zh": suggestion["suggested_corrected_meaning_zh"],
                "note": note,
            }
        )
    counts = Counter(str(item["suggested_decision"]) for item in items)
    output_dir.mkdir(parents=True, exist_ok=True)
    suggestions_json = output_dir / "Genesis-review-suggestions.json"
    suggestions_md = output_dir / "Genesis-review-suggestions.md"
    suggested_overrides = output_dir / "Genesis-review-overrides.assistant-suggested.json"
    payload = {
        "schema": "sentence_reader.lifestudy_vocab_review_suggestions.v1",
        "generated_at": now_iso(),
        "source_review_pack": str(DEFAULT_REVIEW_PACK),
        "database_write_performed": False,
        "policy": "assistant_suggestions_not_human_review",
        "quality": {
            "term_count": len(items),
            "suggested_decision_counts": {key: counts.get(key, 0) for key in ["approve", "correct", "reject", "pending"]},
            "human_reviewed_precision": None,
            "precision_note": "Suggestions are evidence triage only; they are not a human-reviewed accuracy result.",
        },
        "outputs": {
            "suggestions_json": str(suggestions_json),
            "suggestions_markdown": str(suggestions_md),
            "assistant_suggested_overrides": str(suggested_overrides),
        },
        "items": items,
    }
    suggestions_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    suggested_overrides.write_text(
        json.dumps(
            {
                "schema": "sentence_reader.lifestudy_vocab_review_overrides.v1",
                "source_review_pack": str(DEFAULT_REVIEW_PACK),
                "instructions": [
                    "Assistant-generated suggestions only; verify before applying.",
                    "Do not treat this file as human review without checking the evidence.",
                ],
                "items": override_items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Life-study Genesis Review Suggestions",
        "",
        "- Policy: `assistant_suggestions_not_human_review`",
        f"- Terms: `{len(items)}`",
        f"- Suggested approve: `{counts.get('approve', 0)}`",
        f"- Suggested correct: `{counts.get('correct', 0)}`",
        f"- Suggested pending: `{counts.get('pending', 0)}`",
        "",
    ]
    for item in items:
        lines.extend(
            [
                f"## {item['term']}",
                "",
                f"- Suggestion: `{item['suggested_decision']}`",
                f"- Current: `{item['current_meaning_zh']}`",
                f"- Corrected: `{item['suggested_corrected_meaning_zh']}`",
                f"- Confidence: `{item['suggestion_confidence']}`",
                f"- Rationale: {item['rationale']}",
                f"- EN: {item['evidence_en']}",
                f"- ZH: {item['evidence_zh_simp']}",
                "",
            ]
        )
    suggestions_md.write_text("\n".join(lines), encoding="utf-8")
    return payload


def dry_run_suggested_overrides(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            sys.executable,
            str(APPLY_SCRIPT),
            "--review-pack",
            str(DEFAULT_REVIEW_PACK),
            "--overrides",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    parsed = json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else None
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "database_write_performed": False,
        "result": parsed,
        "stderr": proc.stderr,
    }


def main() -> int:
    review_pack = load_review_pack(DEFAULT_REVIEW_PACK)
    payload = build_outputs(review_pack, DEFAULT_OUTPUT_DIR)
    dry_run = dry_run_suggested_overrides(Path(payload["outputs"]["assistant_suggested_overrides"]))
    payload["assistant_suggested_dry_run"] = dry_run
    Path(payload["outputs"]["suggestions_json"]).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("schema", "quality", "outputs", "assistant_suggested_dry_run")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
