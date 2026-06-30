#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reader_api.config import database_url


def stable_id(term: str, source: str) -> str:
    digest = hashlib.sha1(f"{source}\0{term}".encode("utf-8")).hexdigest()[:24]
    return f"dict_{digest}"


def short_translation(value: str) -> str:
    text = " ".join(str(value or "").replace("\\n", "; ").split())
    if not text:
        return ""
    first = text.split(";")[0].strip()
    return first[:120]


def import_ecdict(path: Path, *, limit: int, source: str) -> dict[str, int]:
    inserted = 0
    skipped = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle, psycopg.connect(database_url()) as conn:
        reader = csv.DictReader(handle)
        for row in reader:
            term = str(row.get("word") or row.get("term") or "").strip().lower()
            definition_zh = short_translation(str(row.get("translation") or row.get("definition_zh") or ""))
            if not term or not definition_zh:
                skipped += 1
                continue
            phonetic = str(row.get("phonetic") or "").strip() or None
            part_of_speech = str(row.get("pos") or "").strip() or None
            definition_en = str(row.get("definition") or "").strip() or None
            conn.execute(
                """
                INSERT INTO reader.dictionary_entries (
                    id, language, term, lemma, phonetic, part_of_speech, definition_zh,
                    definition_en, source, priority, metadata, created_at, updated_at
                )
                VALUES (%s, 'en', %s, %s, %s, %s, %s, %s, %s, 80, %s, now(), now())
                ON CONFLICT (language, term, source) DO UPDATE
                SET phonetic = EXCLUDED.phonetic,
                    part_of_speech = EXCLUDED.part_of_speech,
                    definition_zh = EXCLUDED.definition_zh,
                    definition_en = EXCLUDED.definition_en,
                    updated_at = now()
                """,
                (
                    stable_id(term, source),
                    term,
                    term,
                    phonetic,
                    part_of_speech,
                    definition_zh,
                    definition_en,
                    source,
                    Jsonb({"import": "ecdict_csv", "csv": str(path)}),
                ),
            )
            inserted += 1
            if limit and inserted >= limit:
                break
    return {"inserted": inserted, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a compact ECDICT-compatible CSV into Sentence Reader.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--source", default="ecdict")
    args = parser.parse_args()
    result = import_ecdict(args.csv_path, limit=max(0, args.limit), source=args.source)
    print(result)


if __name__ == "__main__":
    main()
