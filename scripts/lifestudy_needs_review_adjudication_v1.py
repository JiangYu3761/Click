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
SOURCE_CSV = REPORT_DIR / "lifestudy_dictionary_guided_review_v2_needs_manual_review.csv"

EXPECTED_INPUT_ROWS = 2205

WORD_RE_CACHE: dict[str, re.Pattern[str]] = {}

HEADER_NOISE_WORDS = {"message", "sermon"}
CHINESE_BOOK_TITLES = (
    "创世记",
    "出埃及记",
    "利未记",
    "民数记",
    "申命记",
    "约书亚记",
    "士师记",
    "路得记",
    "撒母耳记",
    "列王纪",
    "历代志",
    "以斯拉记",
    "尼希米记",
    "以斯帖记",
    "约伯记",
    "诗篇",
    "箴言",
    "传道书",
    "雅歌",
    "以赛亚书",
    "耶利米书",
    "耶利米哀歌",
    "以西结书",
    "但以理书",
    "马太福音",
    "马可福音",
    "路加福音",
    "约翰福音",
    "使徒行传",
    "罗马书",
    "哥林多前书",
    "哥林多后书",
    "加拉太书",
    "以弗所书",
    "腓立比书",
    "歌罗西书",
    "帖撒罗尼迦前书",
    "帖撒罗尼迦后书",
    "提摩太前书",
    "提摩太后书",
    "提多书",
    "腓利门书",
    "希伯来书",
    "雅各书",
    "彼得前书",
    "彼得后书",
    "约翰一书",
    "约翰二书",
    "约翰三书",
    "犹大书",
    "启示录",
)
CHINESE_BOOK_TITLE_RE = "|".join(re.escape(title) for title in sorted(CHINESE_BOOK_TITLES, key=len, reverse=True))
HEADER_NOISE_PATTERNS = [
    re.compile(r"Life-Study of [A-Za-z ]+ Message", re.IGNORECASE),
    re.compile(rf"(?:{CHINESE_BOOK_TITLE_RE})生命读经第篇第页"),
    re.compile(r"生命读经第篇第页"),
]

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

MEANING_SUBSTRING_FALSE_POSITIVES = {
    "启示": ["启示录"],
}

SAME_RECORD_CORRECTIONS = {
    "sermon": ["讲道"],
    "sermons": ["讲道"],
    "siloam": ["西罗亚"],
    "misuse": ["误用"],
    "misused": ["误用"],
    "misuses": ["误用"],
    "misusing": ["误用"],
    "overuse": ["过度使用"],
    "overused": ["过度使用"],
    "overusing": ["过度使用"],
}

GENERIC_ENGLISH_WORDS = {
    "according",
    "also",
    "another",
    "became",
    "become",
    "case",
    "come",
    "comes",
    "coming",
    "day",
    "days",
    "ever",
    "even",
    "first",
    "get",
    "give",
    "go",
    "good",
    "great",
    "have",
    "having",
    "however",
    "know",
    "make",
    "making",
    "many",
    "may",
    "much",
    "need",
    "new",
    "old",
    "one",
    "people",
    "perhaps",
    "place",
    "probably",
    "receive",
    "see",
    "seen",
    "several",
    "something",
    "take",
    "thing",
    "things",
    "time",
    "today",
    "way",
    "work",
    "years",
}

FIELDNAMES = [
    "word",
    "lemma",
    "original_meaning_zh_simp",
    "final_meaning_zh_simp",
    "adjudication_decision",
    "adjudication_reason",
    "uncertainty_reason_group",
    "meaning_source_policy",
    "same_record_english_hit",
    "same_record_chinese_hit",
    "database_write_performed",
    "front_end_import_ready",
    "total_content_frequency",
    "volume_count",
    "source_volume",
    "source_page",
    "evidence_en",
    "evidence_zh_simp",
    "variant_words",
    "dictionary_guided_variants",
    "previous_learning_review_reason",
]


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


def parse_json_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def read_rows() -> list[dict[str, str]]:
    if not SOURCE_CSV.exists():
        raise SystemExit(f"missing source CSV: {SOURCE_CSV}")
    rows = list(csv.DictReader(SOURCE_CSV.open(encoding="utf-8-sig")))
    if len(rows) != EXPECTED_INPUT_ROWS:
        raise SystemExit(f"expected {EXPECTED_INPUT_ROWS} input rows, got {len(rows)}")
    if any(row.get("learning_review_decision") != "needs_manual_review" for row in rows):
        raise SystemExit("source contains rows outside needs_manual_review")
    return rows


def clean_header_noise(text: str) -> str:
    cleaned = text or ""
    for pattern in HEADER_NOISE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned


def meaning_in_clean_zh(meaning: str, evidence_zh: str) -> bool:
    if not meaning:
        return False
    cleaned = clean_header_noise(evidence_zh)
    for target, false_positive_terms in MEANING_SUBSTRING_FALSE_POSITIVES.items():
        if meaning == target:
            for false_positive in false_positive_terms:
                cleaned = cleaned.replace(false_positive, "")
    return meaning in cleaned


def correction_from_same_record(word: str, evidence_zh: str) -> str:
    cleaned = clean_header_noise(evidence_zh)
    candidates = SAME_RECORD_CORRECTIONS.get(word, [])
    for candidate in candidates:
        if candidate in cleaned:
            return candidate
    return ""


def english_variant_hit(word: str, variants: list[str], evidence_en: str) -> bool:
    candidates = {word, *variants}
    return any(candidate and word_re(candidate).search(evidence_en or "") for candidate in candidates)


def likely_header_noise(word: str, evidence_en: str, evidence_zh: str) -> bool:
    if word in HEADER_NOISE_WORDS and any(pattern.search(evidence_en or "") for pattern in HEADER_NOISE_PATTERNS):
        return True
    if word == "sermon" and "启示录生命读经" in (evidence_zh or ""):
        return True
    return False


def uncertainty_group(
    *,
    word: str,
    meaning: str,
    evidence_en: str,
    evidence_zh: str,
    same_english_hit: bool,
    same_chinese_hit: bool,
    previous_reason: str,
) -> str:
    if likely_header_noise(word, evidence_en, evidence_zh):
        return "ocr_or_header_noise"
    if not same_english_hit:
        return "english_evidence_not_matched"
    if not same_chinese_hit:
        return "chinese_meaning_not_matched"
    if meaning in SUSPICIOUS_MEANINGS:
        return "over_generic_chinese_meaning"
    if word in GENERIC_ENGLISH_WORDS:
        return "generic_or_common_learning_word"
    if "少量中文证据" in previous_reason:
        return "low_evidence_count_but_same_record_matched"
    return "same_record_evidence_matched"


def adjudicate_row(raw: dict[str, str]) -> dict[str, Any]:
    word = str(raw.get("word") or "").strip().lower()
    meaning = str(raw.get("reviewed_meaning_zh_simp") or "").strip()
    evidence_en = str(raw.get("evidence_en") or "").strip()
    evidence_zh = str(raw.get("evidence_zh_simp") or "").strip()
    variants = parse_json_list(raw.get("variant_words") or "[]")
    previous_reason = str(raw.get("learning_review_reason") or "")
    same_english_hit = english_variant_hit(word, variants, evidence_en)
    same_chinese_hit = meaning_in_clean_zh(meaning, evidence_zh)
    corrected_meaning = correction_from_same_record(word, evidence_zh) if same_english_hit else ""
    group = uncertainty_group(
        word=word,
        meaning=meaning,
        evidence_en=evidence_en,
        evidence_zh=evidence_zh,
        same_english_hit=same_english_hit,
        same_chinese_hit=same_chinese_hit,
        previous_reason=previous_reason,
    )

    if corrected_meaning:
        decision = "corrected_learning_candidate"
        reason = "原候选义来自子串或错位命中；同条中文证据可修正出更准确的学习义。"
        final_meaning = corrected_meaning
        group = "same_record_corrected_meaning"
    elif group == "ocr_or_header_noise":
        decision = "reject"
        reason = "英文或中文命中来自页眉、书名、信息标题等噪声，不是同条中英对应翻译。"
        final_meaning = ""
    elif group == "over_generic_chinese_meaning":
        decision = "reject"
        reason = "中文候选义过泛，虽然出现在证据句中，但不能安全作为这个英文词的学习义。"
        final_meaning = ""
    elif same_english_hit and same_chinese_hit:
        decision = "learning_only"
        reason = "同一条英文证据和中文证据都命中；本轮只确认学习词库用途，不进入前台正式词典。"
        final_meaning = meaning
    else:
        decision = "still_needs_manual_review"
        reason = "同条中英证据不足；需要同卷、同页或相邻页补充证据后才能判断。"
        final_meaning = ""

    return {
        "word": word,
        "lemma": raw.get("lemma") or word,
        "original_meaning_zh_simp": meaning,
        "final_meaning_zh_simp": final_meaning,
        "adjudication_decision": decision,
        "adjudication_reason": reason,
        "uncertainty_reason_group": group,
        "meaning_source_policy": "same_record_evidence_only",
        "same_record_english_hit": same_english_hit,
        "same_record_chinese_hit": same_chinese_hit,
        "database_write_performed": False,
        "front_end_import_ready": False,
        "total_content_frequency": as_int(raw.get("total_content_frequency")),
        "volume_count": as_int(raw.get("volume_count")),
        "source_volume": raw.get("source_volume") or "",
        "source_page": raw.get("source_page") or "",
        "evidence_en": evidence_en,
        "evidence_zh_simp": evidence_zh,
        "variant_words": raw.get("variant_words") or "",
        "dictionary_guided_variants": raw.get("dictionary_guided_variants") or "",
        "previous_learning_review_reason": previous_reason,
    }


def csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] = FIELDNAMES) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fieldnames})


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    quality = payload["quality"]
    rows = payload["items"]
    lines = [
        "# Life-study Needs Review Adjudication V1",
        "",
        "本文件只处理 `lifestudy_dictionary_guided_review_v2_needs_manual_review.csv` 的 2,205 个不确定词。",
        "",
        "第一轮只采用同条 `evidence_en` / `evidence_zh_simp` 能支持的中文义；不使用普通词典作为最终答案，不写数据库，不进前台正式词典。",
        "",
        f"- Input rows: `{quality['input_rows']}`",
        f"- Output rows: `{quality['output_rows']}`",
        f"- Adjudicated this round: `{quality['adjudicated_count']}`",
        f"- Still needs manual review: `{quality['still_needs_manual_review_count']}`",
        f"- Database write performed: `{payload['database_write_performed']}`",
        "",
        "## Decision Counts",
        "",
    ]
    for decision, count in sorted(quality["decision_counts"].items()):
        lines.append(f"- `{decision}`: `{count}`")
    lines.extend(["", "## Reason Groups", ""])
    for group, count in sorted(quality["reason_group_counts"].items()):
        lines.append(f"- `{group}`: `{count}`")
    lines.extend(["", "## Samples", ""])
    for row in rows[:120]:
        lines.extend(
            [
                f"### {row['word']} -> {row['final_meaning_zh_simp'] or row['original_meaning_zh_simp']}",
                "",
                f"- Decision: `{row['adjudication_decision']}`",
                f"- Reason group: `{row['uncertainty_reason_group']}`",
                f"- Reason: {row['adjudication_reason']}",
                f"- Source: `{row['source_volume']} p{row['source_page']}`",
                f"- EN: {row['evidence_en']}",
                f"- ZH: {row['evidence_zh_simp']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rows = [adjudicate_row(row) for row in read_rows()]
    rows.sort(
        key=lambda row: (
            row["adjudication_decision"] == "still_needs_manual_review",
            row["adjudication_decision"] == "reject",
            -int(row["total_content_frequency"]),
            row["word"],
        )
    )
    corrected = [row for row in rows if row["adjudication_decision"] == "corrected_learning_candidate"]
    learning_only = [row for row in rows if row["adjudication_decision"] == "learning_only"]
    reject = [row for row in rows if row["adjudication_decision"] == "reject"]
    still = [row for row in rows if row["adjudication_decision"] == "still_needs_manual_review"]
    payload = {
        "schema": "sentence_reader.lifestudy_needs_review_adjudication_v1.v1",
        "generated_at": now_iso(),
        "source_csv": str(SOURCE_CSV),
        "database_write_performed": False,
        "policy": "same_record_bilingual_evidence_only_no_db_write_no_frontend_import",
        "quality": {
            "input_rows": EXPECTED_INPUT_ROWS,
            "output_rows": len(rows),
            "adjudicated_count": len(rows) - len(still),
            "corrected_learning_candidate_count": len(corrected),
            "learning_only_count": len(learning_only),
            "reject_count": len(reject),
            "still_needs_manual_review_count": len(still),
            "decision_counts": dict(Counter(row["adjudication_decision"] for row in rows)),
            "reason_group_counts": dict(Counter(row["uncertainty_reason_group"] for row in rows)),
            "front_end_import_ready_count": 0,
        },
        "items": rows,
    }

    json_path = REPORT_DIR / "lifestudy_needs_review_adjudication_v1.json"
    csv_path = REPORT_DIR / "lifestudy_needs_review_adjudication_v1.csv"
    md_path = REPORT_DIR / "lifestudy_needs_review_adjudication_v1.md"
    summary_path = REPORT_DIR / "lifestudy_needs_review_adjudication_v1_summary.json"
    corrected_path = REPORT_DIR / "lifestudy_needs_review_corrected_learning_candidate.csv"
    learning_path = REPORT_DIR / "lifestudy_needs_review_learning_only.csv"
    reject_path = REPORT_DIR / "lifestudy_needs_review_reject.csv"
    still_path = REPORT_DIR / "lifestudy_needs_review_still_needs_manual_review.csv"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, rows)
    write_csv(corrected_path, corrected)
    write_csv(learning_path, learning_only)
    write_csv(reject_path, reject)
    write_csv(still_path, still)
    write_markdown(md_path, payload)
    summary = {k: payload[k] for k in ("schema", "generated_at", "source_csv", "database_write_performed", "policy", "quality")}
    summary["outputs"] = {
        "json": str(json_path),
        "csv": str(csv_path),
        "markdown": str(md_path),
        "summary": str(summary_path),
        "corrected_learning_candidate_csv": str(corrected_path),
        "learning_only_csv": str(learning_path),
        "reject_csv": str(reject_path),
        "still_needs_manual_review_csv": str(still_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
