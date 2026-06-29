#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PIPELINE = ROOT / "reports" / "lifestudy_vocab_pipeline" / "01_Genesis-120-pages-1-1255-pipeline.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "lifestudy_vocab_review"


WORD_MEANING_CANDIDATES: dict[str, list[str]] = {
    "bible": ["圣经"],
    "body": ["身体"],
    "calling": ["呼召"],
    "christ": ["基督"],
    "church": ["召会"],
    "created": ["创造"],
    "creation": ["创造"],
    "darkness": ["黑暗"],
    "death": ["死亡", "死"],
    "dispensing": ["分赐"],
    "divine": ["神圣"],
    "earth": ["地"],
    "economy": ["经纶"],
    "eternal": ["永远"],
    "fellowship": ["交通"],
    "god": ["神"],
    "heavens": ["诸天", "天"],
    "jehovah": ["耶和华"],
    "justification": ["称义"],
    "kingdom": ["国度"],
    "life": ["生命"],
    "light": ["光"],
    "mingled": ["调和", "调在一起"],
    "organic": ["生机"],
    "regeneration": ["重生"],
    "resurrection": ["复活"],
    "restoration": ["恢复", "复造"],
    "revelation": ["启示"],
    "sanctification": ["圣别"],
    "satan": ["撒但"],
    "serpent": ["蛇"],
    "spirit": ["灵"],
    "transformation": ["变化"],
    "word": ["话", "话语", "辞"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_pipeline(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_vocab_pipeline.v1":
        raise SystemExit(f"unexpected pipeline schema: {payload.get('schema')}")
    if payload.get("quality", {}).get("database_write_performed") is not False:
        raise SystemExit("refusing word review pack: pipeline source must be no-write")
    return payload


def meaning_for_word(term: str, evidence_zh: str) -> tuple[str, str, str]:
    candidates = WORD_MEANING_CANDIDATES.get(term, [])
    for candidate in candidates:
        if candidate and candidate in evidence_zh:
            return candidate, "exact_in_sample_evidence", "medium"
    if candidates:
        return candidates[0], "known_lifestudy_word_map_needs_review", "low"
    return "", "no_word_map", "low"


def build_items(pipeline: dict[str, Any]) -> list[dict[str, Any]]:
    words = [item for item in pipeline.get("candidates") or [] if item.get("kind") == "word"]
    result: list[dict[str, Any]] = []
    for item in sorted(words, key=lambda raw: (-int(raw.get("occurrence_count") or 0), str(raw.get("term") or ""))):
        term = str(item.get("term") or "").strip().lower()
        evidence_zh = str(item.get("evidence_zh_simp") or "")
        suggested, source, confidence = meaning_for_word(term, evidence_zh)
        result.append(
            {
                "term": term,
                "kind": "word",
                "occurrence_count": int(item.get("occurrence_count") or 0),
                "current_quality_grade": item.get("quality_grade"),
                "current_status": item.get("status"),
                "suggested_meaning_zh_simp": suggested,
                "suggestion_source": source,
                "suggestion_confidence": confidence,
                "review_decision": "pending",
                "import_ready": False,
                "reason": "single-word terms require separate review before they can become user-facing Life-study vocabulary",
                "source_page": item.get("source_page"),
                "evidence_en": item.get("evidence_en") or "",
                "evidence_zh_simp": evidence_zh,
            }
        )
    return result


def write_csv(path: Path, items: list[dict[str, Any]]) -> None:
    fields = [
        "term",
        "occurrence_count",
        "current_quality_grade",
        "suggested_meaning_zh_simp",
        "suggestion_source",
        "suggestion_confidence",
        "review_decision",
        "import_ready",
        "source_page",
        "evidence_en",
        "evidence_zh_simp",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow({field: item.get(field, "") for field in fields})


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Life-study Genesis Single Word Review Pack",
        "",
        "- Policy: `single_words_review_only_no_db_write`",
        f"- Words: `{payload['quality']['word_candidate_count']}`",
        f"- Suggested meanings: `{payload['quality']['suggested_meaning_count']}`",
        f"- Exact sample evidence: `{payload['quality']['exact_sample_evidence_count']}`",
        "",
        "These words were processed by the Genesis full pipeline, but they were not imported because the phrase-first gate intentionally kept single words out of the user-facing glossary.",
        "",
    ]
    for item in payload["items"]:
        lines.extend(
            [
                f"## {item['term']}",
                "",
                f"- Occurrences: `{item['occurrence_count']}`",
                f"- Suggested meaning: `{item['suggested_meaning_zh_simp']}`",
                f"- Source: `{item['suggestion_source']}`",
                f"- Confidence: `{item['suggestion_confidence']}`",
                f"- Import ready: `{item['import_ready']}`",
                f"- EN: {item['evidence_en']}",
                f"- ZH: {item['evidence_zh_simp']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_report(pipeline_path: Path, output_dir: Path) -> dict[str, Any]:
    pipeline = load_pipeline(pipeline_path)
    items = build_items(pipeline)
    counts = Counter(item["suggestion_source"] for item in items)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "Genesis-word-review-pack.json"
    csv_path = output_dir / "Genesis-word-review-pack.csv"
    md_path = output_dir / "Genesis-word-review-pack.md"
    payload = {
        "schema": "sentence_reader.lifestudy_single_word_review_pack.v1",
        "generated_at": now_iso(),
        "source_pipeline": str(pipeline_path),
        "database_write_performed": False,
        "policy": "single_words_review_only_no_db_write",
        "quality": {
            "word_candidate_count": len(items),
            "suggested_meaning_count": sum(1 for item in items if item["suggested_meaning_zh_simp"]),
            "exact_sample_evidence_count": counts.get("exact_in_sample_evidence", 0),
            "needs_review_count": len(items),
            "import_ready_count": sum(1 for item in items if item["import_ready"]),
            "source_counts": dict(counts),
        },
        "outputs": {
            "json": str(json_path),
            "csv": str(csv_path),
            "markdown": str(md_path),
        },
        "items": items,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, items)
    write_markdown(md_path, payload)
    return payload


def main() -> int:
    payload = build_report(DEFAULT_PIPELINE, DEFAULT_OUTPUT_DIR)
    print(json.dumps({k: payload[k] for k in ("schema", "policy", "quality", "outputs")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
