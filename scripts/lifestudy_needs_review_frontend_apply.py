#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"
ADJUDICATION_SCRIPT = ROOT / "scripts" / "lifestudy_needs_review_frontend_adjudication.py"
DEFAULT_READY = REPORT_DIR / "lifestudy_needs_review_frontend_ready_for_dry_run.csv"
DEFAULT_DATABASE_URL = "postgresql://localhost/sentence_reader"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, *parts: Any) -> str:
    raw = "\0".join(str(part or "") for part in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def normalize_term(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _load_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise SystemExit("psycopg is required for Life-study needs-review frontend apply") from exc
    return psycopg, dict_row, Jsonb


def ensure_ready_csv() -> None:
    if DEFAULT_READY.exists():
        return
    proc = subprocess.run([sys.executable, str(ADJUDICATION_SCRIPT)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip())


def meaning_supported(meaning: str, evidence_zh: str) -> bool:
    parts = [part.strip() for part in meaning.replace("/", "；").split("；") if part.strip()]
    return bool(parts) and all(part in (evidence_zh or "") for part in parts)


def load_ready_items(path: Path) -> list[dict[str, Any]]:
    if path == DEFAULT_READY:
        ensure_ready_csv()
    if not path.exists():
        raise SystemExit(f"missing ready CSV: {path}")
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in rows:
        term = normalize_term(raw.get("word") or "")
        meaning = str(raw.get("final_meaning_zh_simp") or "").strip()
        decision = str(raw.get("frontend_adjudication") or "")
        if not term:
            rejected.append({"term": term, "reason": "missing term"})
            continue
        if term in seen:
            rejected.append({"term": term, "reason": "duplicate term"})
            continue
        seen.add(term)
        if raw.get("front_end_candidate_ready") != "true":
            rejected.append({"term": term, "reason": "not front_end_candidate_ready"})
            continue
        if raw.get("front_end_import_ready") != "false":
            rejected.append({"term": term, "reason": "source must not already be import-ready"})
            continue
        if decision not in {"frontend_ready", "frontend_corrected"}:
            rejected.append({"term": term, "reason": f"invalid adjudication {decision}"})
            continue
        if not meaning:
            rejected.append({"term": term, "reason": "missing final meaning"})
            continue
        if not raw.get("evidence_en") or not raw.get("evidence_zh_simp") or not raw.get("source_page"):
            rejected.append({"term": term, "reason": "missing evidence"})
            continue
        if not meaning_supported(meaning, raw.get("evidence_zh_simp") or ""):
            rejected.append({"term": term, "reason": "final meaning not found in Chinese evidence"})
            continue
        item = dict(raw)
        item["term"] = term
        item["meaning_zh"] = meaning
        item["quality_grade"] = str(item.get("quality_grade") or "B")
        item["confidence"] = float(item.get("confidence") or 0.9)
        accepted.append(item)
    if rejected:
        raise SystemExit(f"refusing apply: invalid ready items found: {rejected[:8]}")
    if not accepted:
        raise SystemExit("no ready items found")
    return accepted


def preflight(database_url: str, *, domain: str, volume: str, terms: list[str]) -> dict[str, Any]:
    psycopg, dict_row, _ = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        existing = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.domain_glossary_entries
            WHERE domain = %s
              AND volume = %s
              AND language = 'en'
              AND lower(term) = ANY(%s::text[])
            """,
            (domain, volume, terms),
        ).fetchone()["n"]
        active_lifestudy = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.domain_glossary_entries
            WHERE domain = %s
              AND language = 'en'
              AND status = 'active'
            """,
            (domain,),
        ).fetchone()["n"]
        dictionary_pollution = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.dictionary_entries
            WHERE lower(coalesce(source, '')) LIKE '%lifestudy%'
               OR lower(coalesce(source, '')) LIKE '%life-study%'
               OR lower(coalesce(source, '')) LIKE '%lifestudy_context%'
               OR lower(coalesce(source, '')) LIKE '%lifestudy_needs_review_frontend%'
            """
        ).fetchone()["n"]
    return {
        "existing_target_terms": int(existing),
        "active_lifestudy_domain_terms_before": int(active_lifestudy),
        "dictionary_pollution_count": int(dictionary_pollution),
    }


def apply_items(
    database_url: str,
    *,
    domain: str,
    volume: str,
    source_title: str,
    ready_csv: Path,
    items: list[dict[str, Any]],
) -> dict[str, int]:
    psycopg, dict_row, Jsonb = _load_psycopg()
    counts = Counter()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        for item in items:
            term = str(item["term"])
            metadata = {
                "source": "lifestudy_needs_review_frontend_v1",
                "source_ready_csv": str(ready_csv),
                "frontend_adjudication": item.get("frontend_adjudication"),
                "frontend_adjudication_reason": item.get("frontend_adjudication_reason"),
                "source_batch": item.get("source_batch"),
                "source_split": item.get("source_split"),
                "source_volume": item.get("source_volume"),
                "volume_count": item.get("volume_count"),
                "frontend_priority_score": item.get("frontend_priority_score"),
                "applied_at": now_iso(),
            }
            conn.execute(
                """
                INSERT INTO reader.domain_glossary_entries (
                    id, domain, volume, language, term, lemma, meaning_zh,
                    quality_grade, confidence, source_title, source_pdf, source_page,
                    evidence_en, evidence_zh, occurrence_count, score, status,
                    metadata, created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, 'en', %s, %s, %s,
                    %s, %s, %s, '', %s,
                    %s, %s, %s, %s, 'active',
                    %s, now(), now()
                )
                ON CONFLICT (domain, volume, language, term) DO UPDATE
                SET lemma = EXCLUDED.lemma,
                    meaning_zh = CASE
                        WHEN reader.domain_glossary_entries.metadata ->> 'user_corrected' = 'true'
                        THEN reader.domain_glossary_entries.meaning_zh
                        ELSE EXCLUDED.meaning_zh
                    END,
                    quality_grade = EXCLUDED.quality_grade,
                    confidence = GREATEST(reader.domain_glossary_entries.confidence, EXCLUDED.confidence),
                    source_title = EXCLUDED.source_title,
                    source_page = EXCLUDED.source_page,
                    evidence_en = EXCLUDED.evidence_en,
                    evidence_zh = EXCLUDED.evidence_zh,
                    occurrence_count = EXCLUDED.occurrence_count,
                    score = GREATEST(reader.domain_glossary_entries.score, EXCLUDED.score),
                    status = 'active',
                    metadata = reader.domain_glossary_entries.metadata || EXCLUDED.metadata,
                    updated_at = now()
                """,
                (
                    stable_id("dgloss", domain, volume, term),
                    domain,
                    volume,
                    term,
                    term,
                    item.get("meaning_zh"),
                    item.get("quality_grade"),
                    float(item.get("confidence") or 0.9),
                    source_title,
                    int(float(item.get("source_page") or 0)),
                    item.get("evidence_en") or "",
                    item.get("evidence_zh_simp") or "",
                    int(float(item.get("total_content_frequency") or 0)),
                    float(item.get("frontend_priority_score") or 0),
                    Jsonb(metadata),
                ),
            )
            counts["domain_glossary_entries"] += 1
        conn.commit()
    return dict(counts)


def hide_items(database_url: str, *, domain: str, volume: str, terms: list[str]) -> dict[str, int]:
    psycopg, dict_row, Jsonb = _load_psycopg()
    metadata = {"hidden_by": "lifestudy_needs_review_frontend_apply", "hidden_at": now_iso()}
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        row = conn.execute(
            """
            UPDATE reader.domain_glossary_entries
            SET status = 'hidden',
                metadata = metadata || %s,
                updated_at = now()
            WHERE domain = %s
              AND volume = %s
              AND language = 'en'
              AND lower(term) = ANY(%s::text[])
            """,
            (Jsonb(metadata), domain, volume, terms),
        )
        conn.commit()
    return {"hidden_domain_glossary_entries": int(row.rowcount or 0)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-csv", type=Path, default=DEFAULT_READY)
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--domain", default="lifestudy")
    parser.add_argument("--volume", default="All")
    parser.add_argument("--source-title", default="Life-study Needs-review Frontend V1")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--hide", action="store_true")
    args = parser.parse_args()

    if args.apply and args.hide:
        raise SystemExit("--apply and --hide are mutually exclusive")

    items = load_ready_items(args.ready_csv)
    terms = [str(item["term"]) for item in items]
    before = preflight(args.database_url, domain=args.domain, volume=args.volume, terms=terms)
    result: dict[str, Any] = {
        "ok": True,
        "schema": "sentence_reader.lifestudy_needs_review_frontend_apply.v1",
        "mode": "apply" if args.apply else ("hide" if args.hide else "dry_run"),
        "database_write_performed": False,
        "target": "reader.domain_glossary_entries",
        "domain": args.domain,
        "volume": args.volume,
        "source_title": args.source_title,
        "candidate_count": len(items),
        "adjudication_counts": dict(Counter(str(item.get("frontend_adjudication") or "") for item in items)),
        "quality_grade_counts": dict(Counter(str(item.get("quality_grade") or "") for item in items)),
        "terms": terms,
        "preflight": before,
    }
    if args.apply:
        result["written"] = apply_items(
            args.database_url,
            domain=args.domain,
            volume=args.volume,
            source_title=args.source_title,
            ready_csv=args.ready_csv,
            items=items,
        )
        result["database_write_performed"] = True
    elif args.hide:
        result["hidden"] = hide_items(args.database_url, domain=args.domain, volume=args.volume, terms=terms)
        result["database_write_performed"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
