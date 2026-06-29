#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import lifestudy_context_vocab_pipeline as pipeline  # noqa: E402
from lifestudy_context_vocab_word_frequency import (  # noqa: E402
    content_words_for,
    load_dictionary_fallbacks,
    pick_suggestion,
    raw_words_for,
)


INVENTORY_SCRIPT = SCRIPTS / "lifestudy_corpus_inventory.py"
INVENTORY = ROOT / "reports" / "lifestudy_vocab_corpus" / "lifestudy_corpus_inventory.json"
OUTPUT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"
CACHE_DIR = OUTPUT_DIR / "all_word_volume_caches"
DEFAULT_DATABASE_URL = "postgresql://localhost/jiangyu_os"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_inventory() -> dict[str, Any]:
    if not INVENTORY.exists():
        proc = subprocess.run(
            [sys.executable, str(INVENTORY_SCRIPT)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stderr.strip() or proc.stdout.strip())
    payload = load_json(INVENTORY)
    if payload.get("schema") != "sentence_reader.lifestudy_corpus_inventory.v1":
        raise SystemExit(f"unexpected inventory schema: {payload.get('schema')}")
    return payload


def volume_rows(inventory: dict[str, Any], requested: set[str], max_volumes: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in inventory.get("items") or []:
        if item.get("is_combined_volume"):
            continue
        volume_index = str(item.get("volume_index") or "")
        if requested and volume_index not in requested:
            continue
        if not item.get("pdf"):
            continue
        rows.append(item)
    rows.sort(key=lambda item: str(item.get("volume_index") or ""))
    if max_volumes > 0:
        rows = rows[:max_volumes]
    return rows


def cache_path_for(row: dict[str, Any]) -> Path:
    stem = str(row.get("pipeline_stem") or Path(str(row["pdf"])).stem)
    return CACHE_DIR / f"{stem}-all-words-cache.json"


def first_evidence(existing: list[dict[str, Any]], unit: pipeline.TextUnit) -> list[dict[str, Any]]:
    if len(existing) >= 3:
        return existing
    if unit.confidence != "high" and existing:
        return existing
    existing.append(
        {
            "page": unit.page,
            "confidence": unit.confidence,
            "alignment_score": unit.alignment_score,
            "en": unit.en,
            "zh_simp": unit.zh_simp,
        }
    )
    return existing


def build_volume_cache(row: dict[str, Any], *, refresh: bool) -> dict[str, Any]:
    path = cache_path_for(row)
    if path.exists() and not refresh:
        return load_json(path)

    pdf_path = Path(str(row["pdf"]))
    if not pdf_path.exists():
        raise SystemExit(f"missing PDF: {pdf_path}")

    line_pairs: list[pipeline.LinePair] = []
    with pipeline.pdfplumber.open(str(pdf_path)) as pdf:
        page_count = len(pdf.pages)
        for idx, page in enumerate(pdf.pages, start=1):
            line_pairs.extend(pipeline.pair_lines_for_page(page, idx))
    units = pipeline.build_units(line_pairs)

    raw_counter: Counter[str] = Counter()
    content_counter: Counter[str] = Counter()
    pages_by_word: dict[str, set[int]] = defaultdict(set)
    content_pages_by_word: dict[str, set[int]] = defaultdict(set)
    evidence_by_word: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for unit in units:
        raw_words = raw_words_for(unit.en)
        content_words = content_words_for(unit.en)
        raw_counter.update(raw_words)
        content_counter.update(content_words)

        for word in set(raw_words):
            pages_by_word[word].add(unit.page)
            evidence_by_word[word] = first_evidence(evidence_by_word[word], unit)
        for word in set(content_words):
            content_pages_by_word[word].add(unit.page)

    items: list[dict[str, Any]] = []
    for word, raw_count in raw_counter.most_common():
        content_count = content_counter.get(word, 0)
        pages = sorted(pages_by_word.get(word) or [])
        content_pages = sorted(content_pages_by_word.get(word) or [])
        items.append(
            {
                "word": word,
                "raw_frequency": raw_count,
                "content_frequency": content_count,
                "is_content_word": content_count > 0,
                "page_count": len(pages),
                "content_page_count": len(content_pages),
                "first_page": pages[0] if pages else None,
                "top_pages": pages[:12],
                "sample_evidence": evidence_by_word.get(word, [])[:3],
            }
        )

    payload = {
        "schema": "sentence_reader.lifestudy_volume_all_words.v1",
        "generated_at": now_iso(),
        "database_write_performed": False,
        "policy": "all_english_words_frequency_context_cache_no_db_write",
        "volume": {
            "volume_index": str(row.get("volume_index") or ""),
            "title_en": str(row.get("title_en") or ""),
            "file_name": str(row.get("file_name") or pdf_path.name),
            "pdf": str(pdf_path),
            "page_count": page_count,
        },
        "quality": {
            "line_pair_count": len(line_pairs),
            "text_unit_count": len(units),
            "raw_unique_word_count": len(raw_counter),
            "raw_word_token_count": sum(raw_counter.values()),
            "content_unique_word_count": len(content_counter),
            "content_word_token_count": sum(content_counter.values()),
        },
        "items": items,
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def aggregate(caches: list[dict[str, Any]], *, database_url: str) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    source_word_row_count = 0
    for cache in caches:
        volume = cache.get("volume") or {}
        volume_index = str(volume.get("volume_index") or "")
        volume_title = str(volume.get("title_en") or "")
        file_name = str(volume.get("file_name") or "")
        for item in cache.get("items") or []:
            word = str(item.get("word") or "").strip().lower()
            if not word:
                continue
            source_word_row_count += 1
            record = grouped.setdefault(
                word,
                {
                    "word": word,
                    "total_raw_frequency": 0,
                    "total_content_frequency": 0,
                    "is_content_word": False,
                    "volume_count": 0,
                    "page_count_total": 0,
                    "first_source": "",
                    "suggested_meaning_zh_simp": "",
                    "meaning_source": "",
                    "meaning_confidence": "",
                    "review_status": "",
                    "import_ready": False,
                    "sources": [],
                    "sample_zh_contexts": [],
                },
            )
            record["total_raw_frequency"] += int(item.get("raw_frequency") or 0)
            record["total_content_frequency"] += int(item.get("content_frequency") or 0)
            record["is_content_word"] = bool(record["is_content_word"] or item.get("is_content_word"))
            record["page_count_total"] += int(item.get("page_count") or 0)
            evidence = item.get("sample_evidence") or []
            for sample in evidence[:2]:
                zh = str(sample.get("zh_simp") or "")
                if zh:
                    record["sample_zh_contexts"].append(zh)
            record["sources"].append(
                {
                    "volume_index": volume_index,
                    "volume_title": volume_title,
                    "file_name": file_name,
                    "raw_frequency": int(item.get("raw_frequency") or 0),
                    "content_frequency": int(item.get("content_frequency") or 0),
                    "page_count": int(item.get("page_count") or 0),
                    "first_page": item.get("first_page"),
                    "top_pages": item.get("top_pages") or [],
                    "sample_evidence": evidence[:2],
                }
            )

    dictionary_fallbacks = load_dictionary_fallbacks(list(grouped), database_url)
    rows: list[dict[str, Any]] = []
    for record in grouped.values():
        record["sources"].sort(
            key=lambda item: (
                str(item.get("volume_index") or ""),
                -int(item.get("raw_frequency") or 0),
            )
        )
        record["volume_count"] = len({source["volume_index"] for source in record["sources"]})
        first = record["sources"][0] if record["sources"] else {}
        if first:
            record["first_source"] = f"{first.get('volume_index')} {first.get('volume_title')} p{first.get('first_page')}"
        zh_contexts = record.pop("sample_zh_contexts")[:20]
        meaning, source_kind, confidence = pick_suggestion(record["word"], zh_contexts, dictionary_fallbacks)
        record["suggested_meaning_zh_simp"] = meaning
        record["meaning_source"] = source_kind
        record["meaning_confidence"] = confidence
        if source_kind == "exact_in_aligned_chinese_context":
            record["review_status"] = "context_meaning_needs_review"
        elif source_kind.startswith("local_dictionary_fallback"):
            record["review_status"] = "dictionary_fallback_not_context_specific"
        elif meaning:
            record["review_status"] = "meaning_candidate_needs_context_review"
        else:
            record["review_status"] = "meaning_missing_needs_review"
        rows.append(record)

    rows.sort(
        key=lambda item: (
            -int(item["total_raw_frequency"]),
            -int(item["total_content_frequency"]),
            str(item["word"]),
        )
    )
    quality = {
        "source_volume_count": len(caches),
        "source_word_row_count": source_word_row_count,
        "unique_word_count": len(rows),
        "content_unique_word_count": sum(1 for row in rows if row["is_content_word"]),
        "raw_word_token_count": sum(int(row["total_raw_frequency"]) for row in rows),
        "content_word_token_count": sum(int(row["total_content_frequency"]) for row in rows),
        "context_meaning_count": sum(1 for row in rows if row["meaning_source"] == "exact_in_aligned_chinese_context"),
        "dictionary_fallback_count": sum(1 for row in rows if str(row["meaning_source"]).startswith("local_dictionary_fallback")),
        "unmapped_word_count": sum(1 for row in rows if not row["suggested_meaning_zh_simp"]),
        "import_ready_count": 0,
    }
    return {
        "schema": "sentence_reader.lifestudy_all_words_master.v1",
        "generated_at": now_iso(),
        "database_write_performed": False,
        "policy": "single_table_all_lifestudy_english_words_with_sources_no_db_write",
        "quality": quality,
        "items": rows,
    }


def write_csv(path: Path, items: list[dict[str, Any]]) -> None:
    fields = [
        "word",
        "total_raw_frequency",
        "total_content_frequency",
        "is_content_word",
        "volume_count",
        "page_count_total",
        "first_source",
        "suggested_meaning_zh_simp",
        "meaning_source",
        "meaning_confidence",
        "review_status",
        "import_ready",
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
                f"{source.get('volume_index')} {source.get('volume_title')} "
                f"x{source.get('raw_frequency')} p{source.get('first_page')}"
                for source in sources
            )
            first_source = sources[0] if sources else {}
            first_evidence = (first_source.get("sample_evidence") or [{}])[0]
            writer.writerow(
                {
                    "word": item.get("word") or "",
                    "total_raw_frequency": item.get("total_raw_frequency") or 0,
                    "total_content_frequency": item.get("total_content_frequency") or 0,
                    "is_content_word": bool(item.get("is_content_word")),
                    "volume_count": item.get("volume_count") or 0,
                    "page_count_total": item.get("page_count_total") or 0,
                    "first_source": item.get("first_source") or "",
                    "suggested_meaning_zh_simp": item.get("suggested_meaning_zh_simp") or "",
                    "meaning_source": item.get("meaning_source") or "",
                    "meaning_confidence": item.get("meaning_confidence") or "",
                    "review_status": item.get("review_status") or "",
                    "import_ready": bool(item.get("import_ready")),
                    "source_summary": source_summary,
                    "first_evidence_en": first_evidence.get("en") or "",
                    "first_evidence_zh_simp": first_evidence.get("zh_simp") or "",
                }
            )


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    quality = payload["quality"]
    lines = [
        "# Life-study All Words Master",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Source volumes: `{quality['source_volume_count']}`",
        f"- Unique words: `{quality['unique_word_count']}`",
        f"- Content unique words: `{quality['content_unique_word_count']}`",
        f"- Raw word tokens: `{quality['raw_word_token_count']}`",
        f"- Content word tokens: `{quality['content_word_token_count']}`",
        f"- Context meanings: `{quality['context_meaning_count']}`",
        f"- Dictionary fallbacks: `{quality['dictionary_fallback_count']}`",
        f"- Unmapped words: `{quality['unmapped_word_count']}`",
        "",
        "This is the single all-word table for Life-study. It is report-only and does not write PostgreSQL.",
        "",
    ]
    for item in payload["items"][:200]:
        sources = item.get("sources") or []
        first = sources[0] if sources else {}
        first_evidence = (first.get("sample_evidence") or [{}])[0]
        lines.extend(
            [
                f"## {item['word']}",
                "",
                f"- Raw frequency: `{item['total_raw_frequency']}`",
                f"- Content frequency: `{item['total_content_frequency']}`",
                f"- Volumes: `{item['volume_count']}`",
                f"- Meaning: `{item['suggested_meaning_zh_simp'] or 'needs review'}`",
                f"- Meaning source: `{item['meaning_source']}`",
                f"- Review status: `{item['review_status']}`",
                f"- First source: `{item['first_source']}`",
                f"- EN: {first_evidence.get('en', '')}",
                f"- ZH: {first_evidence.get('zh_simp', '')}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--volumes", default="", help="comma-separated volume indexes, e.g. 01,02,03")
    parser.add_argument("--max-volumes", type=int, default=0)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--output-stem", default="lifestudy_all_words_master")
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    args = parser.parse_args()

    requested = {item.strip() for item in args.volumes.split(",") if item.strip()}
    inventory = ensure_inventory()
    rows = volume_rows(inventory, requested, args.max_volumes)
    if not rows:
        raise SystemExit("no Life-study volume rows selected")

    caches = [build_volume_cache(row, refresh=args.refresh) for row in rows]
    payload = aggregate(caches, database_url=args.database_url)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_stem = args.output_stem.strip() or "lifestudy_all_words_master"
    json_path = OUTPUT_DIR / f"{output_stem}.json"
    csv_path = OUTPUT_DIR / f"{output_stem}.csv"
    md_path = OUTPUT_DIR / f"{output_stem}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, payload["items"])
    write_markdown(md_path, payload)
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "quality": payload["quality"],
                "outputs": {
                    "json": str(json_path),
                    "csv": str(csv_path),
                    "markdown": str(md_path),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
