#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"
REVIEW_DIR = ROOT / "reports" / "lifestudy_vocab_review"
DEFAULT_MASTER = REPORT_DIR / "lifestudy_all_words_master.json"

import sys

SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import lifestudy_context_vocab_pipeline as pipeline  # noqa: E402
from lifestudy_context_vocab_word_review_pack import WORD_MEANING_CANDIDATES  # noqa: E402


REQUIRED_TOP_WORDS = {
    "economy",
    "dispensing",
    "mingled",
    "transformation",
    "regeneration",
    "sanctification",
    "justification",
    "divine",
    "spirit",
    "life",
    "christ",
}

DOMAIN_HINT_WORDS = set(WORD_MEANING_CANDIDATES) | REQUIRED_TOP_WORDS | {
    "anointing",
    "apostle",
    "body",
    "calling",
    "church",
    "consecration",
    "dispensation",
    "fellowship",
    "grace",
    "kingdom",
    "organic",
    "revelation",
    "resurrection",
    "righteousness",
    "salvation",
    "testament",
}

CONFUSION_PRONE = {
    "economy",
    "dispensing",
    "mingled",
    "organic",
    "body",
    "church",
    "calling",
    "fellowship",
    "transformation",
    "regeneration",
    "sanctification",
    "justification",
    "righteousness",
    "dispensation",
}

STOPWORDS = set(pipeline.STOPWORDS)
GENERIC_WORDS = set(pipeline.GENERIC_WORDS)
VALID_WORD_RE = re.compile(r"^[a-z][a-z'-]*[a-z]$|^[a-z]$")
VOWEL_RE = re.compile(r"[aeiouy]")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def singular_candidate(word: str, vocabulary: set[str]) -> str:
    if word.endswith("ies") and len(word) > 4:
        candidate = word[:-3] + "y"
        if candidate in vocabulary:
            return candidate
    if word.endswith(("ches", "shes", "xes", "ses")) and len(word) > 5:
        candidate = word[:-2]
        if candidate in vocabulary:
            return candidate
    if word.endswith("s") and not word.endswith(("ss", "us", "is")) and len(word) > 3:
        candidate = word[:-1]
        if candidate in vocabulary:
            return candidate
    return word


def clean_decision(word: str, item: dict[str, Any], vocabulary: set[str]) -> tuple[bool, str, str]:
    if not word:
        return False, word, "empty_word"
    if word in STOPWORDS:
        return False, word, "stopword"
    if not item.get("is_content_word"):
        return False, word, "not_content_word"
    if not VALID_WORD_RE.match(word):
        return False, word, "malformed_word"
    if len(word) < 3 and word not in {"us"}:
        return False, word, "too_short"
    if len(word) > 30:
        return False, word, "too_long_possible_ocr"
    if not VOWEL_RE.search(word) and word not in {"myrrh"}:
        return False, word, "no_vowel_possible_ocr"
    if re.search(r"([a-z])\1{3,}", word):
        return False, word, "repeated_character_possible_ocr"
    lemma = singular_candidate(word, vocabulary)
    return True, lemma, "kept"


def best_context_meaning(item: dict[str, Any]) -> tuple[str, str, str, list[dict[str, Any]], list[str]]:
    word = str(item.get("word") or "")
    candidates = WORD_MEANING_CANDIDATES.get(word, [])
    matched: Counter[str] = Counter()
    evidence: list[dict[str, Any]] = []
    for source in item.get("sources") or []:
        for sample in source.get("sample_evidence") or []:
            zh = str(sample.get("zh_simp") or "")
            for candidate in candidates:
                if candidate and candidate in zh:
                    matched[candidate] += 1
                    if len(evidence) < 3:
                        evidence.append(
                            {
                                "volume_index": source.get("volume_index"),
                                "volume_title": source.get("volume_title"),
                                "source_page": sample.get("page") or source.get("first_page"),
                                "confidence": sample.get("confidence") or "",
                                "alignment_score": sample.get("alignment_score"),
                                "meaning_zh_simp": candidate,
                                "evidence_en": sample.get("en") or "",
                                "evidence_zh_simp": zh,
                            }
                        )
    if matched:
        meaning, count = matched.most_common(1)[0]
        variants = [item[0] for item in matched.most_common()]
        confidence = "high" if count >= 2 else "medium"
        return meaning, "exact_in_aligned_chinese_context", confidence, evidence, variants
    if candidates:
        return candidates[0], "known_lifestudy_word_map_without_local_evidence", "low", [], candidates
    return "", "no_context_meaning_candidate", "none", [], []


def priority_for(item: dict[str, Any], meaning_source: str) -> float:
    word = str(item.get("word") or "")
    freq = int(item.get("total_content_frequency") or item.get("total_raw_frequency") or 0)
    score = math.log10(freq + 10) * 10
    score += min(int(item.get("volume_count") or 0), 51) / 4
    if word in DOMAIN_HINT_WORDS:
        score += 80
    if word in CONFUSION_PRONE:
        score += 60
    if meaning_source == "exact_in_aligned_chinese_context":
        score += 45
    if word in REQUIRED_TOP_WORDS:
        score += 200
    return round(score, 3)


def representative_evidence(item: dict[str, Any], context_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    if context_evidence:
        return context_evidence[0]
    for source in item.get("sources") or []:
        for sample in source.get("sample_evidence") or []:
            return {
                "volume_index": source.get("volume_index"),
                "volume_title": source.get("volume_title"),
                "source_page": sample.get("page") or source.get("first_page"),
                "confidence": sample.get("confidence") or "",
                "alignment_score": sample.get("alignment_score"),
                "meaning_zh_simp": "",
                "evidence_en": sample.get("en") or "",
                "evidence_zh_simp": sample.get("zh_simp") or "",
            }
    return {}


def build(master_path: Path, *, top_n: int, reserve_n: int) -> dict[str, Any]:
    master = load_json(master_path)
    if master.get("schema") != "sentence_reader.lifestudy_all_words_master.v1":
        raise SystemExit(f"unexpected all-word master schema: {master.get('schema')}")
    if master.get("database_write_performed") is not False:
        raise SystemExit("refusing to build from a master report that wrote the database")

    raw_items = master.get("items") or []
    vocabulary = {str(item.get("word") or "") for item in raw_items}
    clean_items: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    lemma_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in raw_items:
        word = str(item.get("word") or "").strip().lower()
        keep, lemma, reason = clean_decision(word, item, vocabulary)
        if not keep:
            rejected.append(
                {
                    "word": word,
                    "reason": reason,
                    "total_raw_frequency": item.get("total_raw_frequency") or 0,
                    "total_content_frequency": item.get("total_content_frequency") or 0,
                }
            )
            continue
        normalized = dict(item)
        normalized["lemma"] = lemma
        normalized["original_word"] = word
        normalized["clean_status"] = "kept"
        lemma_groups[lemma].append(normalized)

    for lemma, group in lemma_groups.items():
        group.sort(key=lambda item: (-int(item.get("total_content_frequency") or 0), str(item.get("word") or "")))
        base = dict(group[0])
        if len(group) > 1:
            base["variant_words"] = [item["word"] for item in group]
            base["total_raw_frequency"] = sum(int(item.get("total_raw_frequency") or 0) for item in group)
            base["total_content_frequency"] = sum(int(item.get("total_content_frequency") or 0) for item in group)
            base["volume_count"] = len({source.get("volume_index") for item in group for source in item.get("sources") or []})
            base["sources"] = [
                source
                for item in group
                for source in item.get("sources") or []
            ][:80]
        else:
            base["variant_words"] = [base["word"]]
        meaning, source, confidence, context_evidence, variants = best_context_meaning(base)
        rep = representative_evidence(base, context_evidence)
        base["candidate_meaning_zh_simp"] = meaning
        base["context_meaning_source"] = source
        base["context_meaning_confidence"] = confidence
        base["meaning_variants"] = variants
        base["context_evidence"] = context_evidence
        base["representative_evidence"] = rep
        base["priority_score"] = priority_for(base, source)
        base["quality_grade"] = "A" if source == "exact_in_aligned_chinese_context" and confidence == "high" else (
            "B" if source == "exact_in_aligned_chinese_context" else "C"
        )
        if source == "exact_in_aligned_chinese_context":
            base["review_decision"] = "approve"
            base["review_status"] = "auto_reviewed_context_evidence"
            base["import_ready"] = True
        else:
            base["review_decision"] = "needs_review"
            base["review_status"] = "needs_human_review"
            base["import_ready"] = False
        clean_items.append(base)

    clean_items.sort(key=lambda item: (-float(item.get("priority_score") or 0), -int(item.get("total_content_frequency") or 0), str(item.get("word") or "")))
    top500 = clean_items[:top_n]
    top2000 = clean_items[:reserve_n]
    importable = [item for item in top500 if item.get("import_ready") is True and item.get("quality_grade") in {"A", "B"}]
    human_focus = [
        item for item in top500
        if item.get("import_ready") is not True and (
            item.get("word") in DOMAIN_HINT_WORDS
            or item.get("word") in CONFUSION_PRONE
            or int(item.get("total_content_frequency") or 0) >= 500
        )
    ][:80]

    return {
        "schema": "sentence_reader.lifestudy_context_vocab_v1_build.v1",
        "generated_at": now_iso(),
        "source_master": str(master_path),
        "database_write_performed": False,
        "policy": "clean_prioritize_extract_review_no_db_write",
        "quality": {
            "raw_unique_word_count": len(raw_items),
            "raw_kept_word_count": sum(len(group) for group in lemma_groups.values()),
            "clean_word_count": len(clean_items),
            "rejected_word_count": len(rejected),
            "merged_variant_count": sum(max(0, len(group) - 1) for group in lemma_groups.values()),
            "lemma_group_count": len(lemma_groups),
            "top_queue_count": len(top500),
            "reserve_queue_count": len(top2000),
            "auto_reviewed_import_ready_count": len(importable),
            "needs_review_count": sum(1 for item in top500 if item.get("import_ready") is not True),
            "human_focus_count": len(human_focus),
            "required_top_words_present": sorted(word for word in REQUIRED_TOP_WORDS if any(item.get("word") == word for item in top500)),
            "required_top_words_missing": sorted(word for word in REQUIRED_TOP_WORDS if not any(item.get("word") == word for item in top500)),
        },
        "items": {
            "clean": clean_items,
            "rejected": rejected,
            "top500": top500,
            "top2000": top2000,
            "review_pack": top500,
            "importable": importable,
            "human_focus": human_focus,
        },
    }


def csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


def write_rows_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    evidence = item.get("representative_evidence") or {}
    return {
        "term": item.get("word") or "",
        "lemma": item.get("lemma") or item.get("word") or "",
        "variant_words": item.get("variant_words") or [],
        "total_content_frequency": item.get("total_content_frequency") or 0,
        "total_raw_frequency": item.get("total_raw_frequency") or 0,
        "volume_count": item.get("volume_count") or 0,
        "priority_score": item.get("priority_score") or 0,
        "candidate_meaning_zh_simp": item.get("candidate_meaning_zh_simp") or "",
        "meaning_variants": item.get("meaning_variants") or [],
        "context_meaning_source": item.get("context_meaning_source") or "",
        "context_meaning_confidence": item.get("context_meaning_confidence") or "",
        "quality_grade": item.get("quality_grade") or "",
        "review_decision": item.get("review_decision") or "",
        "review_status": item.get("review_status") or "",
        "import_ready": bool(item.get("import_ready")),
        "source_page": evidence.get("source_page"),
        "source_volume": f"{evidence.get('volume_index') or ''} {evidence.get('volume_title') or ''}".strip(),
        "evidence_en": evidence.get("evidence_en") or "",
        "evidence_zh_simp": evidence.get("evidence_zh_simp") or "",
    }


def write_outputs(payload: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "clean_json": output_dir / "lifestudy_clean_all_words_master.json",
        "clean_csv": output_dir / "lifestudy_clean_all_words_master.csv",
        "rejected_csv": output_dir / "lifestudy_clean_rejected_words.csv",
        "top500_json": output_dir / "lifestudy_vocab_top500_queue.json",
        "top500_csv": output_dir / "lifestudy_vocab_top500_queue.csv",
        "top2000_json": output_dir / "lifestudy_vocab_top2000_queue.json",
        "review_pack_json": output_dir / "lifestudy_vocab_v1_review_pack.json",
        "review_pack_csv": output_dir / "lifestudy_vocab_v1_review_pack.csv",
        "importable_json": output_dir / "lifestudy_vocab_v1_importable.json",
        "importable_csv": output_dir / "lifestudy_vocab_v1_importable.csv",
        "human_focus_md": output_dir / "lifestudy_vocab_v1_human_focus.md",
    }

    clean_payload = {k: payload[k] for k in ("schema", "generated_at", "source_master", "database_write_performed", "policy", "quality")}
    clean_payload["items"] = payload["items"]["clean"]
    outputs["clean_json"].write_text(json.dumps(clean_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    compact_top500 = [compact_item(item) for item in payload["items"]["top500"]]
    compact_top2000 = [compact_item(item) for item in payload["items"]["top2000"]]
    compact_importable = [compact_item(item) for item in payload["items"]["importable"]]
    review_payload = {
        "schema": "sentence_reader.lifestudy_context_vocab_v1_review_pack.v1",
        "generated_at": payload["generated_at"],
        "source_master": payload["source_master"],
        "database_write_performed": False,
        "policy": "top500_review_pack_auto_initial_review_no_db_write",
        "quality": payload["quality"],
        "items": compact_top500,
    }
    importable_payload = {
        "schema": "sentence_reader.lifestudy_context_vocab_v1_importable.v1",
        "generated_at": payload["generated_at"],
        "source_review_pack": str(outputs["review_pack_json"]),
        "database_write_performed": False,
        "policy": "reviewed_import_ready_only_no_db_write",
        "quality": {
            "candidate_count": len(compact_importable),
            "quality_grade_counts": dict(Counter(item["quality_grade"] for item in compact_importable)),
            "review_decision_counts": dict(Counter(item["review_decision"] for item in compact_importable)),
        },
        "items": compact_importable,
    }

    outputs["top500_json"].write_text(json.dumps({"schema": "sentence_reader.lifestudy_vocab_top_queue.v1", "quality": payload["quality"], "items": compact_top500}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    outputs["top2000_json"].write_text(json.dumps({"schema": "sentence_reader.lifestudy_vocab_reserve_queue.v1", "quality": payload["quality"], "items": compact_top2000}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    outputs["review_pack_json"].write_text(json.dumps(review_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    outputs["importable_json"].write_text(json.dumps(importable_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fields = list(compact_top500[0].keys()) if compact_top500 else []
    if fields:
        write_rows_csv(outputs["top500_csv"], compact_top500, fields)
        write_rows_csv(outputs["review_pack_csv"], compact_top500, fields)
        write_rows_csv(outputs["importable_csv"], compact_importable, fields)
        write_rows_csv(outputs["clean_csv"], [compact_item(item) for item in payload["items"]["clean"]], fields)
        write_rows_csv(outputs["rejected_csv"], payload["items"]["rejected"], ["word", "reason", "total_raw_frequency", "total_content_frequency"])

    lines = [
        "# Life-study Vocabulary V1 Human Focus",
        "",
        f"- Top queue: `{payload['quality']['top_queue_count']}`",
        f"- Auto reviewed import-ready: `{payload['quality']['auto_reviewed_import_ready_count']}`",
        f"- Needs review in top queue: `{payload['quality']['needs_review_count']}`",
        f"- Human focus items: `{payload['quality']['human_focus_count']}`",
        "",
    ]
    for item in payload["items"]["human_focus"]:
        compact = compact_item(item)
        lines.extend(
            [
                f"## {compact['term']}",
                "",
                f"- Frequency: `{compact['total_content_frequency']}`",
                f"- Candidate meaning: `{compact['candidate_meaning_zh_simp'] or 'needs evidence'}`",
                f"- Reason: `{compact['context_meaning_source']}`",
                f"- Source: `{compact['source_volume']} p{compact['source_page']}`",
                f"- EN: {compact['evidence_en']}",
                f"- ZH: {compact['evidence_zh_simp']}",
                "",
            ]
        )
    outputs["human_focus_md"].write_text("\n".join(lines), encoding="utf-8")
    return {key: str(path) for key, path in outputs.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--top", type=int, default=500)
    parser.add_argument("--reserve", type=int, default=2000)
    args = parser.parse_args()

    payload = build(args.master, top_n=args.top, reserve_n=args.reserve)
    outputs = write_outputs(payload, args.output_dir)
    print(json.dumps({"schema": payload["schema"], "quality": payload["quality"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
