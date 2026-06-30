#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"
CORRECTED_CSV = REPORT_DIR / "lifestudy_needs_review_corrected_learning_candidate.csv"
LEARNING_CSV = REPORT_DIR / "lifestudy_needs_review_learning_only.csv"
REJECT_CSV = REPORT_DIR / "lifestudy_needs_review_reject.csv"
STILL_CSV = REPORT_DIR / "lifestudy_needs_review_still_needs_manual_review.csv"

EXPECTED_CORRECTED = 3
EXPECTED_LEARNING = 2197
EXPECTED_REJECT = 5
EXPECTED_STILL = 0
QUEUE_SIZE = 300

DOMAIN_TERMS = {
    "ascension",
    "authority",
    "building",
    "consecration",
    "covenant",
    "fellowship",
    "function",
    "glory",
    "gospel",
    "grace",
    "heavenly",
    "holy",
    "inheritance",
    "local",
    "minister",
    "ministry",
    "parable",
    "peace",
    "pray",
    "prayer",
    "preach",
    "priesthood",
    "revelation",
    "riches",
    "sanctification",
    "sermon",
    "testify",
    "truth",
    "vision",
}

GENERIC_LOW_VALUE = {
    "able",
    "according",
    "actually",
    "also",
    "another",
    "anything",
    "aspect",
    "became",
    "become",
    "case",
    "come",
    "comes",
    "coming",
    "could",
    "day",
    "days",
    "ever",
    "every",
    "everything",
    "far",
    "first",
    "forth",
    "get",
    "give",
    "go",
    "going",
    "good",
    "great",
    "hand",
    "have",
    "having",
    "however",
    "indicates",
    "issue",
    "know",
    "little",
    "look",
    "made",
    "main",
    "make",
    "making",
    "many",
    "matter",
    "may",
    "much",
    "need",
    "needed",
    "never",
    "nothing",
    "often",
    "old",
    "one",
    "people",
    "perhaps",
    "person",
    "place",
    "point",
    "probably",
    "put",
    "reading",
    "really",
    "receive",
    "remain",
    "see",
    "seen",
    "set",
    "several",
    "show",
    "six",
    "something",
    "still",
    "take",
    "therefore",
    "thing",
    "things",
    "through",
    "time",
    "today",
    "together",
    "try",
    "under",
    "way",
    "without",
    "work",
    "years",
}

PROPER_OR_BOOK_NAME = {
    "abraham",
    "adam",
    "corinthians",
    "david",
    "genesis",
    "israel",
    "jacob",
    "jehovah",
    "jesus",
    "john",
    "joseph",
    "moses",
    "paul",
    "peter",
    "siloam",
}

SUSPICIOUS_MEANINGS = {
    "事情",
    "东西",
    "方面",
    "方向",
    "情形",
    "局面",
    "中心",
    "要求",
    "问题",
    "事实",
    "分数",
    "人手",
    "日落",
    "一看",
    "主要部分",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_int(value: Any) -> int:
    try:
        return int(float(str(value or "0")))
    except ValueError:
        return 0


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"missing input CSV: {path}")
    return list(csv.DictReader(path.open(encoding="utf-8-sig")))


def word_hit(word: str, evidence_en: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", evidence_en or "", re.IGNORECASE))


def load_inputs() -> tuple[list[dict[str, str]], dict[str, int]]:
    corrected = load_csv(CORRECTED_CSV)
    learning = load_csv(LEARNING_CSV)
    reject = load_csv(REJECT_CSV)
    still = load_csv(STILL_CSV)
    counts = {
        "corrected": len(corrected),
        "learning": len(learning),
        "reject": len(reject),
        "still": len(still),
    }
    expected = {
        "corrected": EXPECTED_CORRECTED,
        "learning": EXPECTED_LEARNING,
        "reject": EXPECTED_REJECT,
        "still": EXPECTED_STILL,
    }
    if counts != expected:
        raise SystemExit(f"unexpected needs-review split counts: {counts} != {expected}")

    rows: list[dict[str, str]] = []
    for row in corrected:
        if row.get("adjudication_decision") != "corrected_learning_candidate":
            raise SystemExit("corrected source contains non-corrected row")
        item = dict(row)
        item["source_split"] = "corrected_learning_candidate"
        rows.append(item)
    for row in learning:
        if row.get("adjudication_decision") != "learning_only":
            raise SystemExit("learning source contains non-learning row")
        item = dict(row)
        item["source_split"] = "learning_only"
        rows.append(item)
    return rows, counts


def score_row(row: dict[str, str]) -> tuple[float, list[str], str]:
    word = str(row.get("word") or "").strip().lower()
    meaning = str(row.get("final_meaning_zh_simp") or "").strip()
    evidence_en = row.get("evidence_en") or ""
    evidence_zh = row.get("evidence_zh_simp") or ""
    freq = as_int(row.get("total_content_frequency"))
    volume_count = as_int(row.get("volume_count"))
    reasons: list[str] = []
    score = 0.0

    score += min(freq, 2000) / 80
    score += min(volume_count, 51) / 2
    if word in DOMAIN_TERMS:
        score += 55
        reasons.append("life_study_domain_hint")
    if row.get("source_split") == "corrected_learning_candidate":
        score += 40
        reasons.append("same_record_corrected")
    if 6 <= len(word) <= 13:
        score += 8
    if 1 <= len(meaning) <= 5:
        score += 8
    if word in GENERIC_LOW_VALUE:
        score -= 70
        reasons.append("generic_low_value")
    if word in PROPER_OR_BOOK_NAME:
        score -= 45
        reasons.append("proper_or_book_name")
    if meaning in SUSPICIOUS_MEANINGS:
        score -= 55
        reasons.append("over_generic_or_misaligned_meaning")
    if not word_hit(word, evidence_en):
        score -= 100
        reasons.append("english_evidence_not_matched")
    if meaning and meaning not in evidence_zh:
        score -= 100
        reasons.append("chinese_evidence_not_matched")

    if any(reason in reasons for reason in ("english_evidence_not_matched", "chinese_evidence_not_matched")):
        bucket = "blocked_by_evidence"
    elif "generic_low_value" in reasons or "over_generic_or_misaligned_meaning" in reasons:
        bucket = "learning_only_keep"
    elif "proper_or_book_name" in reasons and row.get("source_split") != "corrected_learning_candidate":
        bucket = "learning_only_keep"
    elif score >= 60:
        bucket = "frontend_candidate"
    else:
        bucket = "reserve_learning_candidate"
    return round(score, 3), reasons, bucket


def build_rows() -> tuple[list[dict[str, Any]], dict[str, int]]:
    raw_rows, counts = load_inputs()
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        score, reasons, bucket = score_row(raw)
        rows.append(
            {
                "word": str(raw.get("word") or "").strip().lower(),
                "lemma": raw.get("lemma") or raw.get("word") or "",
                "candidate_meaning_zh_simp": raw.get("final_meaning_zh_simp") or "",
                "original_meaning_zh_simp": raw.get("original_meaning_zh_simp") or "",
                "source_split": raw.get("source_split") or "",
                "source_adjudication_decision": raw.get("adjudication_decision") or "",
                "source_adjudication_reason": raw.get("adjudication_reason") or "",
                "uncertainty_reason_group": raw.get("uncertainty_reason_group") or "",
                "frontend_priority_score": score,
                "frontend_priority_reasons": reasons,
                "frontend_queue_bucket": bucket,
                "front_end_import_ready": False,
                "database_write_performed": False,
                "total_content_frequency": as_int(raw.get("total_content_frequency")),
                "volume_count": as_int(raw.get("volume_count")),
                "source_volume": raw.get("source_volume") or "",
                "source_page": raw.get("source_page") or "",
                "evidence_en": raw.get("evidence_en") or "",
                "evidence_zh_simp": raw.get("evidence_zh_simp") or "",
            }
        )
    rows.sort(
        key=lambda row: (
            row["frontend_queue_bucket"] != "frontend_candidate",
            -float(row["frontend_priority_score"]),
            -int(row["total_content_frequency"]),
            row["word"],
        )
    )
    return rows, counts


def csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fieldnames})


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    quality = payload["quality"]
    lines = [
        "# Life-study Needs-review Frontend Queue",
        "",
        "本队列只从 2,205 needs_manual_review 的二审结果中取 `corrected_learning_candidate` 和 `learning_only`，不读取旧 26 个前台词，也不读取 4,116 个已初审通过词。",
        "",
        f"- Source corrected rows: `{quality['source_corrected_rows']}`",
        f"- Source learning rows: `{quality['source_learning_rows']}`",
        f"- Queue rows: `{quality['queue_rows']}`",
        f"- Frontend candidates in queue: `{quality['frontend_candidate_count']}`",
        f"- Front-end import ready: `{quality['front_end_import_ready_count']}`",
        f"- Database write performed: `{payload['database_write_performed']}`",
        "",
        "## Bucket Counts",
        "",
    ]
    for bucket, count in sorted(quality["bucket_counts"].items()):
        lines.append(f"- `{bucket}`: `{count}`")
    lines.append("")
    for row in payload["items"][:120]:
        lines.extend(
            [
                f"## {row['word']} -> {row['candidate_meaning_zh_simp']}",
                "",
                f"- Bucket: `{row['frontend_queue_bucket']}`",
                f"- Score: `{row['frontend_priority_score']}`",
                f"- Reasons: `{json.dumps(row['frontend_priority_reasons'], ensure_ascii=False)}`",
                f"- Source split: `{row['source_split']}`",
                f"- Source: `{row['source_volume']} p{row['source_page']}`",
                f"- EN: {row['evidence_en']}",
                f"- ZH: {row['evidence_zh_simp']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    all_rows, split_counts = build_rows()
    queue_rows = all_rows[:QUEUE_SIZE]
    frontend = [row for row in queue_rows if row["frontend_queue_bucket"] == "frontend_candidate"]
    payload = {
        "schema": "sentence_reader.lifestudy_needs_review_frontend_queue.v1",
        "generated_at": now_iso(),
        "source_csvs": {
            "corrected_learning_candidate": str(CORRECTED_CSV),
            "learning_only": str(LEARNING_CSV),
        },
        "excluded_csvs": {
            "reject": str(REJECT_CSV),
            "still_needs_manual_review": str(STILL_CSV),
        },
        "database_write_performed": False,
        "policy": "top300_frontend_queue_from_2205_needs_review_adjudication_only_no_db_write",
        "quality": {
            "source_corrected_rows": split_counts["corrected"],
            "source_learning_rows": split_counts["learning"],
            "excluded_reject_rows": split_counts["reject"],
            "excluded_still_rows": split_counts["still"],
            "source_eligible_rows": len(all_rows),
            "queue_rows": len(queue_rows),
            "frontend_candidate_count": len(frontend),
            "front_end_import_ready_count": 0,
            "bucket_counts": dict(Counter(row["frontend_queue_bucket"] for row in queue_rows)),
        },
        "items": queue_rows,
    }
    json_path = REPORT_DIR / "lifestudy_needs_review_frontend_queue_top300.json"
    csv_path = REPORT_DIR / "lifestudy_needs_review_frontend_queue_top300.csv"
    frontend_csv_path = REPORT_DIR / "lifestudy_needs_review_frontend_queue_candidates.csv"
    md_path = REPORT_DIR / "lifestudy_needs_review_frontend_queue_top300.md"
    summary_path = REPORT_DIR / "lifestudy_needs_review_frontend_queue_summary.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, queue_rows)
    write_csv(frontend_csv_path, frontend)
    write_markdown(md_path, payload)
    summary = {k: payload[k] for k in ("schema", "generated_at", "source_csvs", "excluded_csvs", "database_write_performed", "policy", "quality")}
    summary["outputs"] = {
        "json": str(json_path),
        "csv": str(csv_path),
        "frontend_candidates_csv": str(frontend_csv_path),
        "markdown": str(md_path),
        "summary": str(summary_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
