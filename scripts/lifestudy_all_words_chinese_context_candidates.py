#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"
DEFAULT_CLEAN_MASTER = REPORT_DIR / "lifestudy_clean_all_words_master.json"

import sys

SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lifestudy_context_vocab_word_review_pack import WORD_MEANING_CANDIDATES  # noqa: E402
from lifestudy_context_vocab_word_frequency import load_dictionary_fallbacks  # noqa: E402


ZH_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")
DEFAULT_DATABASE_URL = "postgresql://localhost/jiangyu_os"
ZH_STOP_TERMS = {
    "一个",
    "一些",
    "一样",
    "一切",
    "不是",
    "不能",
    "不要",
    "也是",
    "就是",
    "这个",
    "这些",
    "那是",
    "那个",
    "那些",
    "我们",
    "你们",
    "他们",
    "她们",
    "它们",
    "自己",
    "里面",
    "外面",
    "时候",
    "所以",
    "因为",
    "但是",
    "这样",
    "那里",
    "这里",
    "什么",
    "甚么",
    "已经",
    "可以",
    "没有",
    "乃是",
    "并且",
    "以及",
    "或者",
    "成为",
    "就是",
    "这种",
    "那种",
    "的人",
    "的是",
    "一面",
    "方面",
    "这事",
    "这件",
    "那件",
    "圣经",
}
ZH_SINGLE_ALLOWED = {"神", "灵", "爱", "光", "地", "天", "义", "罪", "血", "水", "火", "人", "话", "国", "王", "蛇"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def zh_ngrams(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for run in ZH_RUN_RE.findall(text):
        if len(run) > 120:
            run = run[:120]
        for n in (1, 2, 3, 4):
            if len(run) < n:
                continue
            for idx in range(0, len(run) - n + 1):
                token = run[idx : idx + n]
                if n == 1 and token not in ZH_SINGLE_ALLOWED:
                    continue
                if token in ZH_STOP_TERMS:
                    continue
                if any(stop in token for stop in ("我们", "你们", "他们", "这些", "那些", "这个", "那个")):
                    continue
                counts[token] += 1
    return counts


def evidence_samples(item: dict[str, Any], limit: int = 24) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for source in item.get("sources") or []:
        for sample in source.get("sample_evidence") or []:
            en = str(sample.get("en") or "").strip()
            zh = str(sample.get("zh_simp") or "").strip()
            if not en or not zh:
                continue
            key = (str(source.get("volume_index") or ""), str(sample.get("page") or source.get("first_page") or ""), zh[:80])
            if key in seen:
                continue
            seen.add(key)
            samples.append(
                {
                    "volume_index": source.get("volume_index"),
                    "volume_title": source.get("volume_title"),
                    "source_page": sample.get("page") or source.get("first_page"),
                    "confidence": sample.get("confidence") or "",
                    "alignment_score": sample.get("alignment_score"),
                    "evidence_en": en,
                    "evidence_zh_simp": zh,
                }
            )
            if len(samples) >= limit:
                return samples
    return samples


def global_background(items: list[dict[str, Any]]) -> Counter[str]:
    background: Counter[str] = Counter()
    for item in items:
        local: Counter[str] = Counter()
        for sample in evidence_samples(item, limit=8):
            local.update(zh_ngrams(sample["evidence_zh_simp"]))
        background.update(local)
    return background


def known_context_candidate(word: str, zh_texts: list[str]) -> tuple[str, list[str]]:
    matched: Counter[str] = Counter()
    for candidate in WORD_MEANING_CANDIDATES.get(word, []):
        for zh in zh_texts:
            if candidate and candidate in zh:
                matched[candidate] += 1
    if not matched:
        return "", []
    return matched.most_common(1)[0][0], [item for item, _ in matched.most_common(3)]


def dictionary_terms(definition: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[\u4e00-\u9fff]{1,8}", definition):
        if token in ZH_STOP_TERMS:
            continue
        if len(token) == 1 and token not in ZH_SINGLE_ALLOWED:
            continue
        if token not in seen:
            seen.add(token)
            terms.append(token)
    return terms[:10]


def dictionary_guided_context_candidate(
    word: str,
    zh_texts: list[str],
    dictionary_fallbacks: dict[str, dict[str, str]],
) -> tuple[str, list[str], int]:
    dictionary = dictionary_fallbacks.get(word) or {}
    definition = str(dictionary.get("definition_zh") or "")
    candidates = dictionary_terms(definition)
    if not candidates:
        return "", [], 0
    matched: Counter[str] = Counter()
    for candidate in candidates:
        for zh in zh_texts:
            if candidate in zh:
                matched[candidate] += 1
    if not matched:
        return "", candidates, 0
    return matched.most_common(1)[0][0], [item for item, _ in matched.most_common(5)], matched.most_common(1)[0][1]


def statistical_candidates(samples: list[dict[str, Any]], background: Counter[str], total_items: int) -> list[dict[str, Any]]:
    local: Counter[str] = Counter()
    token_evidence: dict[str, dict[str, Any]] = {}
    for sample in samples:
        sample_counts = zh_ngrams(sample["evidence_zh_simp"])
        local.update(sample_counts)
        for token in sample_counts:
            token_evidence.setdefault(token, sample)

    candidates: list[dict[str, Any]] = []
    for token, count in local.items():
        bg = background.get(token, 0)
        if len(token) == 1 and count < 2:
            continue
        if len(token) == 2 and count < 2 and bg > 100:
            continue
        idf = math.log((total_items + 10) / (bg + 1))
        length_bonus = {1: 0.65, 2: 1.0, 3: 1.16, 4: 1.22}.get(len(token), 1.0)
        score = round(count * max(idf, 0.05) * length_bonus, 4)
        candidates.append(
            {
                "candidate": token,
                "count_in_word_context": count,
                "background_count": bg,
                "score": score,
                "evidence": token_evidence[token],
            }
        )
    candidates.sort(key=lambda row: (-float(row["score"]), -int(row["count_in_word_context"]), len(row["candidate"]), row["candidate"]))
    return candidates[:5]


def build_rows(clean_master: Path) -> dict[str, Any]:
    payload = load_json(clean_master)
    if payload.get("database_write_performed") is not False:
        raise SystemExit("refusing DB-writing source")
    items = payload.get("items") or []
    background = global_background(items)
    dictionary_fallbacks = load_dictionary_fallbacks([str(item.get("word") or "") for item in items], DEFAULT_DATABASE_URL)
    rows: list[dict[str, Any]] = []

    for item in items:
        word = str(item.get("word") or "")
        samples = evidence_samples(item)
        zh_texts = [sample["evidence_zh_simp"] for sample in samples]
        exact, exact_variants = known_context_candidate(word, zh_texts)
        dictionary_guided, dictionary_variants, dictionary_hit_count = dictionary_guided_context_candidate(word, zh_texts, dictionary_fallbacks)
        stats = statistical_candidates(samples, background, len(items)) if samples else []
        if exact:
            draft = exact
            source = "known_term_found_in_chinese_context"
            confidence = "high"
            evidence = next((sample for sample in samples if exact in sample["evidence_zh_simp"]), samples[0] if samples else {})
        elif dictionary_guided:
            draft = dictionary_guided
            source = "dictionary_guided_term_found_in_chinese_context"
            confidence = "medium" if dictionary_hit_count >= 2 else "low"
            evidence = next((sample for sample in samples if dictionary_guided in sample["evidence_zh_simp"]), samples[0] if samples else {})
        elif stats:
            draft = "；".join(row["candidate"] for row in stats[:3])
            source = "statistical_chinese_context_candidate"
            top = stats[0]
            confidence = "medium" if top["count_in_word_context"] >= 3 and top["score"] >= 4 else "low"
            evidence = top["evidence"]
        else:
            draft = ""
            source = "no_chinese_context_candidate"
            confidence = "none"
            evidence = samples[0] if samples else {}

        rows.append(
            {
                "word": word,
                "lemma": item.get("lemma") or word,
                "variant_words": item.get("variant_words") or [],
                "total_content_frequency": item.get("total_content_frequency") or 0,
                "total_raw_frequency": item.get("total_raw_frequency") or 0,
                "volume_count": item.get("volume_count") or 0,
                "draft_meaning_zh_from_chinese_context": draft,
                "candidate_source": source,
                "candidate_confidence": confidence,
                "known_term_variants": exact_variants,
                "dictionary_guided_variants": dictionary_variants,
                "statistical_candidates": [
                    {
                        "candidate": row["candidate"],
                        "count_in_word_context": row["count_in_word_context"],
                        "background_count": row["background_count"],
                        "score": row["score"],
                    }
                    for row in stats
                ],
                "review_decision": "approve" if source == "known_term_found_in_chinese_context" else "needs_review",
                "import_ready": source == "known_term_found_in_chinese_context",
                "front_end_policy": "do_not_import_unless_reviewed",
                "source_volume": f"{evidence.get('volume_index') or ''} {evidence.get('volume_title') or ''}".strip(),
                "source_page": evidence.get("source_page") or "",
                "evidence_en": evidence.get("evidence_en") or "",
                "evidence_zh_simp": evidence.get("evidence_zh_simp") or "",
            }
        )

    rows.sort(
        key=lambda row: (
            -int(row["total_content_frequency"] or 0),
            str(row["word"]),
        )
    )
    return {
        "schema": "sentence_reader.lifestudy_all_words_chinese_context_candidates.v1",
        "generated_at": now_iso(),
        "source_clean_master": str(clean_master),
        "database_write_performed": False,
        "policy": "all_words_chinese_context_candidates_report_only_no_db_write",
        "quality": {
            "row_count": len(rows),
            "known_context_candidate_count": sum(1 for row in rows if row["candidate_source"] == "known_term_found_in_chinese_context"),
            "dictionary_guided_context_candidate_count": sum(1 for row in rows if row["candidate_source"] == "dictionary_guided_term_found_in_chinese_context"),
            "statistical_candidate_count": sum(1 for row in rows if row["candidate_source"] == "statistical_chinese_context_candidate"),
            "no_candidate_count": sum(1 for row in rows if row["candidate_source"] == "no_chinese_context_candidate"),
            "medium_or_high_candidate_count": sum(1 for row in rows if row["candidate_confidence"] in {"medium", "high"}),
            "import_ready_count": sum(1 for row in rows if row["import_ready"]),
        },
        "items": rows,
    }


def csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


def write_outputs(payload: dict[str, Any]) -> dict[str, str]:
    json_path = REPORT_DIR / "lifestudy_all_words_chinese_context_candidates.json"
    csv_path = REPORT_DIR / "lifestudy_all_words_chinese_context_candidates.csv"
    md_path = REPORT_DIR / "lifestudy_all_words_chinese_context_candidates.md"
    summary_path = REPORT_DIR / "lifestudy_all_words_chinese_context_candidates_summary.json"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = [
        "word",
        "lemma",
        "variant_words",
        "total_content_frequency",
        "total_raw_frequency",
        "volume_count",
        "draft_meaning_zh_from_chinese_context",
        "candidate_source",
        "candidate_confidence",
        "known_term_variants",
        "dictionary_guided_variants",
        "statistical_candidates",
        "review_decision",
        "import_ready",
        "front_end_policy",
        "source_volume",
        "source_page",
        "evidence_en",
        "evidence_zh_simp",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in payload["items"]:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})

    lines = [
        "# Life-study All Words Chinese Context Candidates",
        "",
        "这张表是 51 卷全量英文词的中文文档候选义表，不是入库文件。",
        "",
        f"- Rows: `{payload['quality']['row_count']}`",
        f"- Known context candidates: `{payload['quality']['known_context_candidate_count']}`",
        f"- Dictionary-guided context candidates: `{payload['quality']['dictionary_guided_context_candidate_count']}`",
        f"- Statistical context candidates: `{payload['quality']['statistical_candidate_count']}`",
        f"- No candidate: `{payload['quality']['no_candidate_count']}`",
        f"- Medium/high candidates: `{payload['quality']['medium_or_high_candidate_count']}`",
        "",
        "`draft_meaning_zh_from_chinese_context` 来自中文证据句；统计候选必须人工审核后才可入库。",
        "",
    ]
    for row in payload["items"][:200]:
        lines.extend(
            [
                f"## {row['word']}",
                "",
                f"- Draft meaning: `{row['draft_meaning_zh_from_chinese_context'] or 'needs review'}`",
                f"- Source: `{row['candidate_source']}`",
                f"- Confidence: `{row['candidate_confidence']}`",
                f"- Frequency: `{row['total_content_frequency']}`",
                f"- Evidence: `{row['source_volume']} p{row['source_page']}`",
                f"- EN: {row['evidence_en']}",
                f"- ZH: {row['evidence_zh_simp']}",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    summary = {k: payload[k] for k in ("schema", "generated_at", "source_clean_master", "database_write_performed", "policy", "quality")}
    summary["outputs"] = {"json": str(json_path), "csv": str(csv_path), "markdown": str(md_path), "summary": str(summary_path)}
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary["outputs"]


def main() -> int:
    payload = build_rows(DEFAULT_CLEAN_MASTER)
    outputs = write_outputs(payload)
    print(json.dumps({k: payload[k] for k in ("schema", "policy", "quality")} | {"outputs": outputs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
