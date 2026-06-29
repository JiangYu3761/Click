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
SOURCE_CSV = REPORT_DIR / "lifestudy_all_words_chinese_context_candidates.csv"


WORD_RE_CACHE: dict[str, re.Pattern[str]] = {}

GENERIC_FRONTEND_WORDS = {
    "according",
    "also",
    "another",
    "became",
    "become",
    "come",
    "comes",
    "coming",
    "day",
    "days",
    "even",
    "first",
    "get",
    "give",
    "go",
    "good",
    "great",
    "have",
    "having",
    "know",
    "make",
    "man",
    "many",
    "may",
    "much",
    "need",
    "new",
    "old",
    "one",
    "people",
    "see",
    "seen",
    "take",
    "things",
    "time",
    "way",
    "work",
    "years",
}

SUSPICIOUS_MEANINGS = {
    "局面",
    "东西",
    "事情",
    "情形",
    "方面",
    "时候",
    "这个",
    "这些",
    "那个",
    "那些",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def word_re(word: str) -> re.Pattern[str]:
    if word not in WORD_RE_CACHE:
        WORD_RE_CACHE[word] = re.compile(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", re.IGNORECASE)
    return WORD_RE_CACHE[word]


def as_int(value: Any) -> int:
    try:
        return int(float(str(value or "0")))
    except ValueError:
        return 0


def read_rows() -> list[dict[str, str]]:
    if not SOURCE_CSV.exists():
        raise SystemExit(f"missing source CSV: {SOURCE_CSV}")
    return list(csv.DictReader(SOURCE_CSV.open(encoding="utf-8-sig")))


def review_row(raw: dict[str, str]) -> dict[str, Any]:
    word = str(raw.get("word") or "").strip().lower()
    meaning = str(raw.get("draft_meaning_zh_from_chinese_context") or "").strip()
    evidence_en = str(raw.get("evidence_en") or "").strip()
    evidence_zh = str(raw.get("evidence_zh_simp") or "").strip()
    confidence = str(raw.get("candidate_confidence") or "").strip()
    source = str(raw.get("candidate_source") or "").strip()
    freq = as_int(raw.get("total_content_frequency"))

    english_hit = bool(word and evidence_en and word_re(word).search(evidence_en))
    chinese_hit = bool(meaning and evidence_zh and meaning in evidence_zh)
    has_evidence = bool(english_hit and chinese_hit)
    suspicious = meaning in SUSPICIOUS_MEANINGS or len(meaning) > 8

    if source != "dictionary_guided_term_found_in_chinese_context":
        decision = "out_of_scope"
        reason = "不是词典辅助且中文证据命中的候选"
    elif not has_evidence:
        decision = "needs_manual_review"
        reason = "英文词或中文候选义没有同时命中证据句"
    elif suspicious:
        decision = "needs_manual_review"
        reason = "中文候选义过泛或可疑"
    elif confidence == "medium":
        decision = "auto_accept_learning_candidate"
        reason = "词典辅助候选已在中文证据句命中，且多处命中"
    else:
        decision = "needs_manual_review"
        reason = "只在少量中文证据中命中，暂不自动确认"

    if decision == "auto_accept_learning_candidate" and word in GENERIC_FRONTEND_WORDS:
        frontend_scope = "learning_only_generic_word"
    elif decision == "auto_accept_learning_candidate":
        frontend_scope = "possible_frontend_after_human_review"
    else:
        frontend_scope = "not_frontend_ready"

    return {
        "word": word,
        "lemma": raw.get("lemma") or word,
        "reviewed_meaning_zh_simp": meaning,
        "learning_review_decision": decision,
        "learning_review_reason": reason,
        "candidate_confidence": confidence,
        "candidate_source": source,
        "frontend_scope": frontend_scope,
        "front_end_import_ready": False,
        "requires_human_before_frontend": True,
        "total_content_frequency": freq,
        "volume_count": as_int(raw.get("volume_count")),
        "source_volume": raw.get("source_volume") or "",
        "source_page": raw.get("source_page") or "",
        "evidence_en": evidence_en,
        "evidence_zh_simp": evidence_zh,
        "english_evidence_hit": english_hit,
        "chinese_evidence_hit": chinese_hit,
        "variant_words": raw.get("variant_words") or "",
        "dictionary_guided_variants": raw.get("dictionary_guided_variants") or "",
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
    accepted = [row for row in payload["items"] if row["learning_review_decision"] == "auto_accept_learning_candidate"]
    needs = [row for row in payload["items"] if row["learning_review_decision"] == "needs_manual_review"]
    lines = [
        "# Life-study Dictionary-guided Review V2",
        "",
        "这个文件审核 6,321 个“较靠谱待审”候选。",
        "",
        "注意：本轮确认的是学习用候选，不是前台正式入库。",
        "",
        f"- Total dictionary-guided rows: `{payload['quality']['total_rows']}`",
        f"- Auto-accepted for learning: `{payload['quality']['auto_accept_learning_count']}`",
        f"- Needs manual review: `{payload['quality']['needs_manual_review_count']}`",
        f"- Possible frontend after human review: `{payload['quality']['possible_frontend_after_human_review_count']}`",
        f"- Learning-only generic words: `{payload['quality']['learning_only_generic_word_count']}`",
        "",
        "## Auto Accepted Samples",
        "",
    ]
    for row in accepted[:80]:
        lines.extend(
            [
                f"### {row['word']} -> {row['reviewed_meaning_zh_simp']}",
                "",
                f"- Frequency: `{row['total_content_frequency']}`",
                f"- Frontend scope: `{row['frontend_scope']}`",
                f"- Source: `{row['source_volume']} p{row['source_page']}`",
                f"- EN: {row['evidence_en']}",
                f"- ZH: {row['evidence_zh_simp']}",
                "",
            ]
        )
    lines.extend(["## Needs Manual Review Samples", ""])
    for row in needs[:80]:
        lines.extend(
            [
                f"### {row['word']} -> {row['reviewed_meaning_zh_simp']}",
                "",
                f"- Reason: {row['learning_review_reason']}",
                f"- Confidence: `{row['candidate_confidence']}`",
                f"- Frequency: `{row['total_content_frequency']}`",
                f"- Source: `{row['source_volume']} p{row['source_page']}`",
                f"- EN: {row['evidence_en']}",
                f"- ZH: {row['evidence_zh_simp']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    source_rows = [row for row in read_rows() if row.get("candidate_source") == "dictionary_guided_term_found_in_chinese_context"]
    reviewed = [review_row(row) for row in source_rows]
    reviewed.sort(
        key=lambda row: (
            row["learning_review_decision"] != "auto_accept_learning_candidate",
            row["frontend_scope"] != "possible_frontend_after_human_review",
            -int(row["total_content_frequency"]),
            row["word"],
        )
    )
    accept = [row for row in reviewed if row["learning_review_decision"] == "auto_accept_learning_candidate"]
    needs = [row for row in reviewed if row["learning_review_decision"] == "needs_manual_review"]
    possible_frontend = [row for row in accept if row["frontend_scope"] == "possible_frontend_after_human_review"]

    payload = {
        "schema": "sentence_reader.lifestudy_dictionary_guided_review_v2.v1",
        "generated_at": now_iso(),
        "source_csv": str(SOURCE_CSV),
        "database_write_performed": False,
        "policy": "dictionary_guided_learning_review_no_db_write_no_frontend_import",
        "quality": {
            "total_rows": len(reviewed),
            "auto_accept_learning_count": len(accept),
            "needs_manual_review_count": len(needs),
            "possible_frontend_after_human_review_count": len(possible_frontend),
            "learning_only_generic_word_count": sum(1 for row in accept if row["frontend_scope"] == "learning_only_generic_word"),
            "front_end_import_ready_count": 0,
            "decision_counts": dict(Counter(row["learning_review_decision"] for row in reviewed)),
            "frontend_scope_counts": dict(Counter(row["frontend_scope"] for row in reviewed)),
        },
        "items": reviewed,
    }

    json_path = REPORT_DIR / "lifestudy_dictionary_guided_review_v2.json"
    csv_path = REPORT_DIR / "lifestudy_dictionary_guided_review_v2.csv"
    accepted_csv_path = REPORT_DIR / "lifestudy_dictionary_guided_review_v2_auto_accept_learning.csv"
    possible_frontend_csv_path = REPORT_DIR / "lifestudy_dictionary_guided_review_v2_possible_frontend_after_human_review.csv"
    needs_csv_path = REPORT_DIR / "lifestudy_dictionary_guided_review_v2_needs_manual_review.csv"
    md_path = REPORT_DIR / "lifestudy_dictionary_guided_review_v2.md"
    summary_path = REPORT_DIR / "lifestudy_dictionary_guided_review_v2_summary.json"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, reviewed)
    write_csv(accepted_csv_path, accept)
    write_csv(possible_frontend_csv_path, possible_frontend)
    write_csv(needs_csv_path, needs)
    write_markdown(md_path, payload)
    summary = {k: payload[k] for k in ("schema", "generated_at", "source_csv", "database_write_performed", "policy", "quality")}
    summary["outputs"] = {
        "json": str(json_path),
        "csv": str(csv_path),
        "auto_accept_learning_csv": str(accepted_csv_path),
        "possible_frontend_after_human_review_csv": str(possible_frontend_csv_path),
        "needs_manual_review_csv": str(needs_csv_path),
        "markdown": str(md_path),
        "summary": str(summary_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
