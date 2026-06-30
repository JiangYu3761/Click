#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
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
from lifestudy_context_vocab_word_review_pack import WORD_MEANING_CANDIDATES  # noqa: E402


DEFAULT_PIPELINE = ROOT / "reports" / "lifestudy_vocab_pipeline" / "01_Genesis-120-pages-1-1255-pipeline.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "lifestudy_vocab_review"
DEFAULT_DATABASE_URL = "postgresql://localhost/sentence_reader"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_pipeline_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_vocab_pipeline.v1":
        raise SystemExit(f"unexpected pipeline schema: {payload.get('schema')}")
    return payload


def normalize_word(raw: str) -> str:
    word = pipeline.normalize_token(raw)
    if word.endswith("'s"):
        word = word[:-2]
    return word


def raw_words_for(text: str) -> list[str]:
    result: list[str] = []
    for match in pipeline.WORD_RE.finditer(text):
        word = normalize_word(match.group(0))
        if len(word) >= 2:
            result.append(word)
    return result


def content_words_for(text: str) -> list[str]:
    return [normalize_word(word) for word in pipeline.words_for(text)]


def load_dictionary_fallbacks(words: list[str], database_url: str) -> dict[str, dict[str, str]]:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        return {}
    if not words:
        return {}
    try:
        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT lower(term) AS word, definition_zh, source, priority
                FROM reader.dictionary_entries
                WHERE language = 'en'
                  AND lower(term) = ANY(%s::text[])
                ORDER BY priority DESC, length(definition_zh) ASC
                """,
                (words,),
            ).fetchall()
    except Exception:
        return {}
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        word = str(row["word"])
        if word in result:
            continue
        result[word] = {
            "definition_zh": str(row["definition_zh"]),
            "source": str(row["source"] or "local_dictionary"),
        }
    return result


def pick_suggestion(word: str, zh_texts: list[str], dictionary_fallbacks: dict[str, dict[str, str]]) -> tuple[str, str, str]:
    candidates = WORD_MEANING_CANDIDATES.get(word, [])
    for candidate in candidates:
        for zh in zh_texts:
            if candidate in zh:
                return candidate, "exact_in_aligned_chinese_context", "medium"
    if candidates:
        return candidates[0], "known_word_map_needs_context_review", "low"
    dictionary = dictionary_fallbacks.get(word)
    if dictionary and dictionary.get("definition_zh"):
        return dictionary["definition_zh"], f"local_dictionary_fallback:{dictionary.get('source')}", "low"
    return "", "no_word_meaning_candidate", "none"


def build_units(pdf_path: Path, pages: int) -> list[pipeline.TextUnit]:
    line_pairs: list[pipeline.LinePair] = []
    with pipeline.pdfplumber.open(str(pdf_path)) as pdf:
        page_count = min(max(pages, 1), len(pdf.pages))
        for idx in range(page_count):
            line_pairs.extend(pipeline.pair_lines_for_page(pdf.pages[idx], idx + 1))
    return pipeline.build_units(line_pairs)


def build_frequency_report(*, pipeline_report_path: Path, pages: int, output_dir: Path, limit: int, database_url: str) -> dict[str, Any]:
    source = load_pipeline_report(pipeline_report_path)
    pdf_path = Path(str(source.get("source_pdf") or ""))
    if not pdf_path.exists():
        raise SystemExit(f"source PDF not found: {pdf_path}")

    units = build_units(pdf_path, pages)
    raw_counter: Counter[str] = Counter()
    content_counter: Counter[str] = Counter()
    units_by_word: dict[str, list[pipeline.TextUnit]] = defaultdict(list)

    for unit in units:
        raw_counter.update(raw_words_for(unit.en))
        seen_content = set(content_words_for(unit.en))
        content_counter.update(content_words_for(unit.en))
        for word in seen_content:
            units_by_word[word].append(unit)

    rows: list[dict[str, Any]] = []
    ordered = content_counter.most_common(limit if limit > 0 else None)
    dictionary_fallbacks = load_dictionary_fallbacks([word for word, _ in ordered], database_url)
    for word, count in ordered:
        word_units = units_by_word.get(word) or []
        high_units = [item for item in word_units if item.confidence == "high"]
        sample_units = high_units[:3] or word_units[:3]
        zh_contexts = [item.zh_simp for item in sample_units]
        meaning, source_kind, confidence = pick_suggestion(word, zh_contexts, dictionary_fallbacks)
        rows.append(
            {
                "word": word,
                "content_frequency": count,
                "raw_frequency": raw_counter.get(word, count),
                "unit_count": len(word_units),
                "page_count": len({item.page for item in word_units}),
                "first_page": min((item.page for item in word_units), default=None),
                "suggested_meaning_zh_simp": meaning,
                "meaning_source": source_kind,
                "meaning_confidence": confidence,
                "review_status": "pending" if meaning else "needs_alignment",
                "import_ready": False,
                "sample_evidence": [
                    {
                        "page": item.page,
                        "confidence": item.confidence,
                        "en": item.en,
                        "zh_simp": item.zh_simp,
                    }
                    for item in sample_units
                ],
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "Genesis-word-frequency.json"
    csv_path = output_dir / "Genesis-word-frequency.csv"
    md_path = output_dir / "Genesis-word-frequency.md"
    raw_csv_path = output_dir / "Genesis-raw-word-frequency.csv"
    payload = {
        "schema": "sentence_reader.lifestudy_word_frequency.v1",
        "generated_at": now_iso(),
        "source_pipeline": str(pipeline_report_path),
        "source_pdf": str(pdf_path),
        "pages": pages,
        "database_write_performed": False,
        "policy": "frequency_and_context_report_only_no_db_write",
        "quality": {
            "text_unit_count": len(units),
            "raw_unique_word_count": len(raw_counter),
            "raw_word_token_count": sum(raw_counter.values()),
            "content_unique_word_count": len(content_counter),
            "content_word_token_count": sum(content_counter.values()),
            "reported_content_word_count": len(rows),
            "suggested_meaning_count": sum(1 for row in rows if row["suggested_meaning_zh_simp"]),
            "exact_context_meaning_count": sum(1 for row in rows if row["meaning_source"] == "exact_in_aligned_chinese_context"),
            "known_context_review_meaning_count": sum(1 for row in rows if row["meaning_source"] == "known_word_map_needs_context_review"),
            "local_dictionary_fallback_count": sum(1 for row in rows if str(row["meaning_source"]).startswith("local_dictionary_fallback")),
            "unmapped_word_count": sum(1 for row in rows if not row["suggested_meaning_zh_simp"]),
            "import_ready_count": 0,
        },
        "outputs": {
            "json": str(json_path),
            "csv": str(csv_path),
            "markdown": str(md_path),
            "raw_csv": str(raw_csv_path),
        },
        "items": rows,
    }

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_content_csv(csv_path, rows)
    write_raw_csv(raw_csv_path, raw_counter)
    write_markdown(md_path, payload)
    return payload


def write_content_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "word",
        "content_frequency",
        "raw_frequency",
        "unit_count",
        "page_count",
        "first_page",
        "suggested_meaning_zh_simp",
        "meaning_source",
        "meaning_confidence",
        "review_status",
        "import_ready",
        "sample_en",
        "sample_zh_simp",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            sample = (row.get("sample_evidence") or [{}])[0]
            payload = {field: row.get(field, "") for field in fields}
            payload["sample_en"] = sample.get("en", "")
            payload["sample_zh_simp"] = sample.get("zh_simp", "")
            writer.writerow(payload)


def write_raw_csv(path: Path, counter: Counter[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["word", "raw_frequency"])
        for word, count in counter.most_common():
            writer.writerow([word, count])


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Life-study Genesis Word Frequency",
        "",
        "- Policy: `frequency_and_context_report_only_no_db_write`",
        f"- Pages: `{payload['pages']}`",
        f"- Raw unique words: `{payload['quality']['raw_unique_word_count']}`",
        f"- Content unique words: `{payload['quality']['content_unique_word_count']}`",
        f"- Suggested meanings: `{payload['quality']['suggested_meaning_count']}`",
        f"- Context meanings: `{payload['quality']['exact_context_meaning_count']}`",
        f"- Local dictionary fallbacks: `{payload['quality']['local_dictionary_fallback_count']}`",
        f"- Unmapped words: `{payload['quality']['unmapped_word_count']}`",
        "",
        "The report is sorted by frequency. It is not a production import file. Words need review before they become user-facing lookup entries.",
        "",
        "## Top Words",
        "",
    ]
    for item in payload["items"][:120]:
        evidence = (item.get("sample_evidence") or [{}])[0]
        meaning = item.get("suggested_meaning_zh_simp") or "needs review"
        lines.extend(
            [
                f"### {item['word']}",
                "",
                f"- Frequency: `{item['content_frequency']}`",
                f"- Suggested meaning: `{meaning}`",
                f"- Meaning source: `{item['meaning_source']}`",
                f"- First page: `{item['first_page']}`",
                f"- EN: {evidence.get('en', '')}",
                f"- ZH: {evidence.get('zh_simp', '')}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Genesis full-word frequency and aligned Chinese context report.")
    parser.add_argument("--pipeline-report", type=Path, default=DEFAULT_PIPELINE)
    parser.add_argument("--pages", type=int, default=1255)
    parser.add_argument("--limit", type=int, default=0, help="Limit content words in the main report; 0 means all.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--database-url", default=os.getenv("READER_DATABASE_URL", DEFAULT_DATABASE_URL))
    args = parser.parse_args()

    payload = build_frequency_report(
        pipeline_report_path=args.pipeline_report,
        pages=args.pages,
        output_dir=args.output_dir,
        limit=args.limit,
        database_url=args.database_url,
    )
    print(json.dumps({k: payload[k] for k in ("schema", "policy", "quality", "outputs")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
