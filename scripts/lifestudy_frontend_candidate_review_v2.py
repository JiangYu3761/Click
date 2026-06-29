#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"
SOURCE_CSV = REPORT_DIR / "lifestudy_dictionary_guided_review_v2_possible_frontend_after_human_review.csv"


DOMAIN_HINTS = {
    "anointing",
    "apostles",
    "apostle",
    "altar",
    "blessing",
    "body",
    "calling",
    "church",
    "consecration",
    "dispensation",
    "element",
    "enjoyment",
    "experience",
    "expression",
    "faith",
    "fellowship",
    "gospel",
    "glory",
    "grace",
    "heavenly",
    "knowledge",
    "kingdom",
    "living",
    "ministry",
    "organic",
    "offering",
    "praise",
    "priest",
    "priesthood",
    "principle",
    "reality",
    "recovery",
    "redemption",
    "revelation",
    "resurrection",
    "righteousness",
    "salvation",
    "sanctuary",
    "saints",
    "sin",
    "sacrifice",
    "tabernacle",
    "testament",
    "truth",
    "vision",
    "worship",
}

GENERIC_LOW_VALUE = {
    "able",
    "already",
    "always",
    "another",
    "anything",
    "became",
    "become",
    "coming",
    "could",
    "every",
    "everything",
    "first",
    "going",
    "great",
    "having",
    "little",
    "many",
    "much",
    "never",
    "nothing",
    "often",
    "perhaps",
    "really",
    "second",
    "several",
    "something",
    "still",
    "thing",
    "things",
    "through",
    "together",
    "under",
    "without",
}

PROPER_NAME_LEARNING_ONLY = {
    "abraham",
    "adam",
    "christ",
    "david",
    "israel",
    "jacob",
    "jehovah",
    "jesus",
    "john",
    "joseph",
    "moses",
    "paul",
    "peter",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_int(value: Any) -> int:
    try:
        return int(float(str(value or "0")))
    except ValueError:
        return 0


def read_rows() -> list[dict[str, str]]:
    if not SOURCE_CSV.exists():
        raise SystemExit(f"missing source CSV: {SOURCE_CSV}")
    return list(csv.DictReader(SOURCE_CSV.open(encoding="utf-8-sig")))


def score_row(row: dict[str, str]) -> tuple[float, list[str]]:
    word = str(row.get("word") or "").lower()
    meaning = str(row.get("reviewed_meaning_zh_simp") or "")
    freq = as_int(row.get("total_content_frequency"))
    volume_count = as_int(row.get("volume_count"))
    score = 0.0
    reasons: list[str] = []

    score += min(freq, 2000) / 100
    score += min(volume_count, 51) / 3
    if word in DOMAIN_HINTS:
        score += 45
        reasons.append("domain_hint")
    if len(word) >= 6:
        score += 5
    if 1 <= len(meaning) <= 4:
        score += 8
    if word in PROPER_NAME_LEARNING_ONLY:
        score -= 25
        reasons.append("proper_name_learning_only")
    if word in GENERIC_LOW_VALUE:
        score -= 35
        reasons.append("generic_low_value")
    if str(row.get("candidate_confidence")) == "medium":
        score += 10
        reasons.append("medium_confidence")
    return round(score, 3), reasons


def classify_row(raw: dict[str, str]) -> dict[str, Any]:
    score, reasons = score_row(raw)
    word = str(raw.get("word") or "").lower()
    if "generic_low_value" in reasons:
        suggested = "reject_for_frontend"
        reason = "普通功能词或泛词，学习可看，前台优先释义价值低"
    elif "proper_name_learning_only" in reasons and word not in DOMAIN_HINTS:
        suggested = "learning_only"
        reason = "人名/专名，学习可看，普通词典足够，不优先进入 Life-study 领域词库"
    elif word in DOMAIN_HINTS and score >= 55:
        suggested = "approve_after_human_check"
        reason = "高频、多卷、中文证据命中，适合人工确认后进入前台候选"
    else:
        suggested = "needs_human_review"
        reason = "候选有价值，但前台优先展示仍需人工判断"
    return {
        "word": word,
        "reviewed_meaning_zh_simp": raw.get("reviewed_meaning_zh_simp") or "",
        "suggested_frontend_decision": suggested,
        "frontend_review_reason": reason,
        "frontend_priority_score": score,
        "score_reasons": reasons,
        "front_end_import_ready": False,
        "requires_human_before_frontend": True,
        "total_content_frequency": as_int(raw.get("total_content_frequency")),
        "volume_count": as_int(raw.get("volume_count")),
        "source_volume": raw.get("source_volume") or "",
        "source_page": raw.get("source_page") or "",
        "evidence_en": raw.get("evidence_en") or "",
        "evidence_zh_simp": raw.get("evidence_zh_simp") or "",
        "learning_review_decision": raw.get("learning_review_decision") or "",
        "learning_review_reason": raw.get("learning_review_reason") or "",
    }


def csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    rows = payload["items"]
    lines = [
        "# Life-study Frontend Candidate Review V2",
        "",
        "这个文件不是入库文件。它只把学习候选中更适合前台的词挑出来，供下一轮人工确认。",
        "",
        f"- Source rows: `{payload['quality']['source_rows']}`",
        f"- Top review rows: `{payload['quality']['top_review_rows']}`",
        f"- Suggested approve after human check: `{payload['quality']['approve_after_human_check_count']}`",
        f"- Needs human review: `{payload['quality']['needs_human_review_count']}`",
        f"- Learning only: `{payload['quality']['learning_only_count']}`",
        f"- Reject for frontend: `{payload['quality']['reject_for_frontend_count']}`",
        f"- Front-end import ready: `{payload['quality']['front_end_import_ready_count']}`",
        "",
    ]
    for row in rows[:120]:
        lines.extend(
            [
                f"## {row['word']} -> {row['reviewed_meaning_zh_simp']}",
                "",
                f"- Suggested decision: `{row['suggested_frontend_decision']}`",
                f"- Score: `{row['frontend_priority_score']}`",
                f"- Reason: {row['frontend_review_reason']}",
                f"- Frequency: `{row['total_content_frequency']}`",
                f"- Volume count: `{row['volume_count']}`",
                f"- Source: `{row['source_volume']} p{row['source_page']}`",
                f"- EN: {row['evidence_en']}",
                f"- ZH: {row['evidence_zh_simp']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_override_template(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "sentence_reader.lifestudy_frontend_candidate_review_v2_overrides_template.v1",
        "generated_at": now_iso(),
        "database_write_performed": False,
        "policy": "human_review_template_no_db_write",
        "instructions": {
            "human_decision": "approve / correct / reject / needs_review",
            "corrected_meaning_zh_simp": "required when human_decision=correct",
            "front_end_import_ready": "must remain false until a separate controlled apply step",
        },
        "items": [
            {
                "word": row["word"],
                "suggested_meaning_zh_simp": row["reviewed_meaning_zh_simp"],
                "human_decision": "pending",
                "corrected_meaning_zh_simp": "",
                "front_end_import_ready": False,
                "source_volume": row["source_volume"],
                "source_page": row["source_page"],
                "evidence_en": row["evidence_en"],
                "evidence_zh_simp": row["evidence_zh_simp"],
                "note": "",
            }
            for row in rows
        ],
    }


def main() -> int:
    reviewed = [classify_row(row) for row in read_rows()]
    reviewed.sort(
        key=lambda row: (
            row["suggested_frontend_decision"] != "approve_after_human_check",
            -float(row["frontend_priority_score"]),
            -int(row["total_content_frequency"]),
            row["word"],
        )
    )
    top500 = reviewed[:500]
    approve = [row for row in top500 if row["suggested_frontend_decision"] == "approve_after_human_check"]
    needs = [row for row in top500 if row["suggested_frontend_decision"] == "needs_human_review"]
    learning_only = [row for row in top500 if row["suggested_frontend_decision"] == "learning_only"]
    reject = [row for row in top500 if row["suggested_frontend_decision"] == "reject_for_frontend"]

    payload = {
        "schema": "sentence_reader.lifestudy_frontend_candidate_review_v2.v1",
        "generated_at": now_iso(),
        "source_csv": str(SOURCE_CSV),
        "database_write_performed": False,
        "policy": "top500_frontend_candidate_review_no_db_write_human_required",
        "quality": {
            "source_rows": len(reviewed),
            "top_review_rows": len(top500),
            "approve_after_human_check_count": len(approve),
            "needs_human_review_count": len(needs),
            "learning_only_count": len(learning_only),
            "reject_for_frontend_count": len(reject),
            "front_end_import_ready_count": 0,
            "decision_counts": dict(Counter(row["suggested_frontend_decision"] for row in top500)),
        },
        "items": top500,
    }

    json_path = REPORT_DIR / "lifestudy_frontend_candidate_review_v2_top500.json"
    csv_path = REPORT_DIR / "lifestudy_frontend_candidate_review_v2_top500.csv"
    approve_csv_path = REPORT_DIR / "lifestudy_frontend_candidate_review_v2_approve_after_human_check.csv"
    template_json_path = REPORT_DIR / "lifestudy_frontend_candidate_review_v2_overrides_template.json"
    template_csv_path = REPORT_DIR / "lifestudy_frontend_candidate_review_v2_overrides_template.csv"
    md_path = REPORT_DIR / "lifestudy_frontend_candidate_review_v2.md"
    summary_path = REPORT_DIR / "lifestudy_frontend_candidate_review_v2_summary.json"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, top500)
    write_csv(approve_csv_path, approve)
    template = build_override_template(approve)
    template_json_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(template_csv_path, template["items"])
    write_markdown(md_path, payload)
    summary = {k: payload[k] for k in ("schema", "generated_at", "source_csv", "database_write_performed", "policy", "quality")}
    summary["outputs"] = {
        "json": str(json_path),
        "csv": str(csv_path),
        "approve_after_human_check_csv": str(approve_csv_path),
        "overrides_template_json": str(template_json_path),
        "overrides_template_csv": str(template_csv_path),
        "markdown": str(md_path),
        "summary": str(summary_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
