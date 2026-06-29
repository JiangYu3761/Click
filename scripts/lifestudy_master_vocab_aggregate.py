#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_corpus_inventory.json"
REVIEW_DIR = ROOT / "reports" / "lifestudy_vocab_review"
OUTPUT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"


GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def reviewed_status(volume_title: str) -> str:
    if volume_title != "Genesis":
        return "candidate_no_write"
    pack_path = REVIEW_DIR / "Genesis-review-pack.json"
    if not pack_path.exists():
        return "candidate_no_write"
    pack = load_json(pack_path)
    quality = pack.get("quality") or {}
    if quality.get("decision_counts", {}).get("pending") == 0 and quality.get("can_expand_next_volume") is True:
        return "reviewed_applied"
    return "review_pending"


def source_rows_from_inventory(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in inventory.get("items") or []:
        if item.get("is_combined_volume"):
            continue
        full_importable = str(item.get("full_importable") or "")
        if not full_importable:
            continue
        path = Path(full_importable)
        if not path.exists():
            continue
        rows.append(item)
    return rows


def aggregate() -> dict[str, Any]:
    if not INVENTORY.exists():
        raise SystemExit(f"inventory not found; run scripts/lifestudy_corpus_inventory.py first: {INVENTORY}")
    inventory = load_json(INVENTORY)
    source_rows = source_rows_from_inventory(inventory)
    grouped: dict[str, dict[str, Any]] = {}
    source_file_count = 0
    source_entry_count = 0

    for row in source_rows:
        importable_path = Path(str(row["full_importable"]))
        payload = load_json(importable_path)
        if payload.get("schema") != "sentence_reader.lifestudy_vocab_importable.v1":
            raise SystemExit(f"unexpected schema for {importable_path}: {payload.get('schema')}")
        volume_index = str(row.get("volume_index") or "")
        volume_title = str(row.get("title_en") or "")
        status = reviewed_status(volume_title)
        source_file_count += 1
        for raw in payload.get("items") or []:
            term = str(raw.get("term") or "").strip().lower()
            if not term:
                continue
            source_entry_count += 1
            meaning = str(raw.get("suggested_meaning_zh_simp") or "").strip()
            grade = str(raw.get("quality_grade") or "")
            record = grouped.setdefault(
                term,
                {
                    "term": term,
                    "primary_meaning_zh_simp": meaning,
                    "meaning_variants": set(),
                    "best_quality_grade": grade,
                    "total_occurrence_count": 0,
                    "volume_count": 0,
                    "review_statuses": set(),
                    "sources": [],
                },
            )
            if meaning:
                record["meaning_variants"].add(meaning)
            if GRADE_RANK.get(grade, 9) < GRADE_RANK.get(str(record["best_quality_grade"]), 9):
                record["best_quality_grade"] = grade
                record["primary_meaning_zh_simp"] = meaning
            occurrence_count = int(raw.get("occurrence_count") or 0)
            record["total_occurrence_count"] += occurrence_count
            record["review_statuses"].add(status)
            record["sources"].append(
                {
                    "volume_index": volume_index,
                    "volume_title": volume_title,
                    "source_status": status,
                    "quality_grade": grade,
                    "occurrence_count": occurrence_count,
                    "source_page": raw.get("source_page"),
                    "match_source": raw.get("match_source") or "",
                    "alignment_confidence": raw.get("alignment_confidence") or "",
                    "alignment_score": raw.get("alignment_score"),
                    "meaning_zh_simp": meaning,
                    "evidence_en": raw.get("evidence_en") or "",
                    "evidence_zh_simp": raw.get("evidence_zh_simp") or "",
                    "source_importable": str(importable_path),
                }
            )

    items: list[dict[str, Any]] = []
    for record in grouped.values():
        volume_keys = {(source["volume_index"], source["volume_title"]) for source in record["sources"]}
        record["volume_count"] = len(volume_keys)
        variants = sorted(record.pop("meaning_variants"))
        statuses = sorted(record.pop("review_statuses"))
        record["meaning_variants"] = variants
        record["review_statuses"] = statuses
        record["has_meaning_conflict"] = len(variants) > 1
        record["is_fully_reviewed"] = statuses == ["reviewed_applied"]
        record["sources"].sort(key=lambda item: (str(item["volume_index"]), -int(item["occurrence_count"]), int(item.get("source_page") or 0)))
        items.append(record)

    items.sort(
        key=lambda item: (
            GRADE_RANK.get(str(item["best_quality_grade"]), 9),
            -int(item["volume_count"]),
            -int(item["total_occurrence_count"]),
            str(item["term"]),
        )
    )
    conflict_count = sum(1 for item in items if item["has_meaning_conflict"])
    reviewed_count = sum(1 for item in items if item["is_fully_reviewed"])
    term_status_counts = Counter(status for item in items for status in item["review_statuses"])
    source_status_counts = Counter(
        source["source_status"]
        for item in items
        for source in item["sources"]
    )
    return {
        "schema": "sentence_reader.lifestudy_master_vocab.v1",
        "generated_at": now_iso(),
        "database_write_performed": False,
        "policy": "aggregate_full_no_write_importable_candidates_with_sources",
        "inventory": str(INVENTORY),
        "quality": {
            "source_volume_count": source_file_count,
            "source_entry_count": source_entry_count,
            "unique_term_count": len(items),
            "reviewed_term_count": reviewed_count,
            "meaning_conflict_count": conflict_count,
            "status_counts": dict(term_status_counts),
            "term_status_counts": dict(term_status_counts),
            "source_status_counts": dict(source_status_counts),
        },
        "items": items,
    }


def write_csv(path: Path, items: list[dict[str, Any]]) -> None:
    fields = [
        "term",
        "primary_meaning_zh_simp",
        "meaning_variants",
        "best_quality_grade",
        "total_occurrence_count",
        "volume_count",
        "review_statuses",
        "has_meaning_conflict",
        "source_summary",
        "first_evidence_en",
        "first_evidence_zh_simp",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            sources = item.get("sources") or []
            source_summary = "; ".join(
                f"{source['volume_index']} {source['volume_title']} p{source.get('source_page')} x{source.get('occurrence_count')} {source.get('source_status')}"
                for source in sources
            )
            first = sources[0] if sources else {}
            writer.writerow(
                {
                    "term": item.get("term") or "",
                    "primary_meaning_zh_simp": item.get("primary_meaning_zh_simp") or "",
                    "meaning_variants": " | ".join(item.get("meaning_variants") or []),
                    "best_quality_grade": item.get("best_quality_grade") or "",
                    "total_occurrence_count": item.get("total_occurrence_count") or 0,
                    "volume_count": item.get("volume_count") or 0,
                    "review_statuses": " | ".join(item.get("review_statuses") or []),
                    "has_meaning_conflict": bool(item.get("has_meaning_conflict")),
                    "source_summary": source_summary,
                    "first_evidence_en": first.get("evidence_en") or "",
                    "first_evidence_zh_simp": first.get("evidence_zh_simp") or "",
                }
            )


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Life-study Master Vocabulary",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Source volumes: `{payload['quality']['source_volume_count']}`",
        f"- Unique terms: `{payload['quality']['unique_term_count']}`",
        f"- Reviewed terms: `{payload['quality']['reviewed_term_count']}`",
        f"- Meaning conflicts: `{payload['quality']['meaning_conflict_count']}`",
        "",
    ]
    for item in payload["items"][:200]:
        lines.extend(
            [
                f"## {item['term']}",
                "",
                f"- Chinese: `{item['primary_meaning_zh_simp']}`",
                f"- Grade: `{item['best_quality_grade']}`",
                f"- Volumes: `{item['volume_count']}`",
                f"- Total occurrences: `{item['total_occurrence_count']}`",
                f"- Status: `{', '.join(item['review_statuses'])}`",
                f"- Meaning conflict: `{item['has_meaning_conflict']}`",
                "",
            ]
        )
        for source in item["sources"][:5]:
            lines.extend(
                [
                    f"  - `{source['volume_index']} {source['volume_title']}` p{source.get('source_page')} x{source.get('occurrence_count')} "
                    f"`{source.get('source_status')}`: {source.get('meaning_zh_simp')}",
                ]
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    payload = aggregate()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "lifestudy_master_vocab.json"
    csv_path = OUTPUT_DIR / "lifestudy_master_vocab.csv"
    md_path = OUTPUT_DIR / "lifestudy_master_vocab.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, payload["items"])
    write_markdown(md_path, payload)
    print(json.dumps({"schema": payload["schema"], "quality": payload["quality"], "outputs": {"json": str(json_path), "csv": str(csv_path), "markdown": str(md_path)}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
