#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_PACK = ROOT / "reports" / "lifestudy_vocab_review" / "Genesis-review-pack.json"
DEFAULT_OVERRIDES = ROOT / "reports" / "lifestudy_vocab_review" / "Genesis-review-overrides.template.json"
DEFAULT_DATABASE_URL = "postgresql://localhost/sentence_reader"
VALID_DECISIONS = {"approve", "correct", "reject"}
REVIEWED_PRECISION_TARGET = 0.85


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_term(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _load_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise SystemExit("psycopg is required for review application") from exc
    return psycopg, dict_row, Jsonb


def load_review_pack(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_vocab_review_pack.v1":
        raise SystemExit(f"unexpected review pack schema: {payload.get('schema')}")
    if payload.get("database_write_performed") is not False:
        raise SystemExit("refusing review apply: review pack must be a no-write report")
    items = payload.get("items") or []
    if not items:
        raise SystemExit("review pack contains no items")
    return payload


def load_overrides(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_vocab_review_overrides.v1":
        raise SystemExit(f"unexpected override schema: {payload.get('schema')}")
    result: dict[str, dict[str, Any]] = {}
    for raw in payload.get("items") or []:
        term = normalize_term(str(raw.get("term") or ""))
        decision = str(raw.get("decision") or "pending").strip().lower()
        corrected = str(raw.get("corrected_meaning_zh") or "").strip()
        note = str(raw.get("note") or "").strip()
        if not term:
            raise SystemExit("override item missing term")
        if decision not in VALID_DECISIONS:
            raise SystemExit(f"review decision for {term} must be approve/correct/reject, got {decision}")
        if decision == "correct" and not corrected:
            raise SystemExit(f"correct decision requires corrected_meaning_zh for {term}")
        if decision == "reject" and not note:
            raise SystemExit(f"reject decision requires note for {term}")
        result[term] = {
            "term": term,
            "decision": decision,
            "corrected_meaning_zh": corrected,
            "note": note,
        }
    return result


def build_review_decisions(review_pack: dict[str, Any], overrides: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    items = review_pack.get("items") or []
    terms = {normalize_term(str(item.get("term") or "")) for item in items}
    unknown = sorted(set(overrides) - terms)
    if unknown:
        raise SystemExit(f"override contains unknown terms: {unknown[:8]}")
    missing = sorted(term for term in terms if term not in overrides)
    if missing:
        raise SystemExit(f"override missing review decisions for terms: {missing[:8]}")

    decisions: list[dict[str, Any]] = []
    for item in items:
        term = normalize_term(str(item.get("term") or ""))
        override = overrides[term]
        decision = str(override["decision"])
        final_meaning = (
            str(override["corrected_meaning_zh"]).strip()
            if decision == "correct"
            else str(item.get("current_meaning_zh") or "").strip()
        )
        if decision != "reject" and not final_meaning:
            raise SystemExit(f"approved/corrected item missing final meaning: {term}")
        decisions.append(
            {
                "term": term,
                "quality_grade": item.get("quality_grade"),
                "decision": decision,
                "current_meaning_zh": item.get("current_meaning_zh") or "",
                "final_meaning_zh": final_meaning,
                "review_note": override.get("note") or "",
                "source_page": item.get("source_page"),
                "evidence_en": item.get("evidence_en") or "",
                "evidence_zh_simp": item.get("evidence_zh_simp") or "",
            }
        )
    return decisions


def db_preflight(database_url: str, *, book_id: str, terms: list[str]) -> dict[str, Any]:
    psycopg, dict_row, _ = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        book = conn.execute("SELECT id, title FROM reader.books WHERE id = %s", (book_id,)).fetchone()
        if not book:
            raise SystemExit(f"book_id not found: {book_id}")
        book_glossary = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.book_glossary
            WHERE book_id = %s AND lower(term) = ANY(%s::text[])
            """,
            (book_id, terms),
        ).fetchone()["n"]
        book_vocab = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.book_vocab_items
            WHERE book_id = %s AND lower(surface) = ANY(%s::text[])
            """,
            (book_id, terms),
        ).fetchone()["n"]
        domain = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.domain_glossary_entries
            WHERE domain = 'lifestudy'
              AND volume = 'Genesis'
              AND lower(term) = ANY(%s::text[])
            """,
            (terms,),
        ).fetchone()["n"]
        dictionary_pollution = conn.execute(
            """
            SELECT count(*) AS n
            FROM reader.dictionary_entries
            WHERE lower(coalesce(source, '')) LIKE '%lifestudy%'
               OR lower(coalesce(source, '')) LIKE '%life-study%'
               OR lower(coalesce(source, '')) LIKE '%lifestudy_context%'
            """
        ).fetchone()["n"]
    return {
        "book": dict(book),
        "book_glossary_count": int(book_glossary),
        "book_vocab_count": int(book_vocab),
        "domain_count": int(domain),
        "dictionary_pollution_count": int(dictionary_pollution),
    }


def apply_decisions(database_url: str, *, book_id: str, decisions: list[dict[str, Any]], override_path: Path) -> dict[str, int]:
    psycopg, dict_row, Jsonb = _load_psycopg()
    counts = Counter()
    reviewed_at = now_iso()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        for item in decisions:
            term = str(item["term"])
            decision = str(item["decision"])
            final_meaning = str(item.get("final_meaning_zh") or "")
            review_metadata = {
                "lifestudy_review": {
                    "decision": decision,
                    "reviewed_at": reviewed_at,
                    "override_file": str(override_path),
                    "current_meaning_zh": item.get("current_meaning_zh") or "",
                    "final_meaning_zh": final_meaning,
                    "note": item.get("review_note") or "",
                    "source_page": item.get("source_page"),
                }
            }
            if decision == "reject":
                conn.execute(
                    """
                    UPDATE reader.domain_glossary_entries
                    SET status = 'hidden',
                        metadata = metadata || %s,
                        updated_at = now()
                    WHERE domain = 'lifestudy'
                      AND volume = 'Genesis'
                      AND lower(term) = %s
                    """,
                    (Jsonb(review_metadata), term),
                )
                conn.execute(
                    """
                    UPDATE reader.book_glossary
                    SET source = 'lifestudy_rejected',
                        confidence = 0,
                        updated_at = now()
                    WHERE book_id = %s
                      AND lower(term) = %s
                      AND source <> 'user'
                    """,
                    (book_id, term),
                )
                conn.execute(
                    """
                    UPDATE reader.book_vocab_items
                    SET status = 'ignored',
                        metadata = metadata || %s,
                        updated_at = now()
                    WHERE book_id = %s
                      AND lower(surface) = %s
                      AND COALESCE(meaning_source, '') <> 'user_glossary'
                    """,
                    (Jsonb(review_metadata), book_id, term),
                )
                counts["hidden"] += 1
                continue

            domain_status = conn.execute(
                """
                UPDATE reader.domain_glossary_entries
                SET meaning_zh = %s,
                    status = 'active',
                    metadata = metadata || %s,
                    updated_at = now()
                WHERE domain = 'lifestudy'
                  AND volume = 'Genesis'
                  AND lower(term) = %s
                """,
                (final_meaning, Jsonb(review_metadata), term),
            )
            counts["domain_reviewed"] += int(domain_status.rowcount or 0)

            if decision == "correct":
                conn.execute(
                    """
                    UPDATE reader.book_glossary
                    SET meaning_zh = %s,
                        source = 'user',
                        confidence = 1,
                        updated_at = now()
                    WHERE book_id = %s AND lower(term) = %s
                    """,
                    (final_meaning, book_id, term),
                )
                conn.execute(
                    """
                    UPDATE reader.book_vocab_items
                    SET context_meaning = %s,
                        meaning_source = 'user_glossary',
                        alignment_status = 'confirmed_context_meaning',
                        alignment_reason = 'Life-study 审校修正，优先于自动抽取结果。',
                        status = 'saved',
                        metadata = metadata || %s,
                        updated_at = now()
                    WHERE book_id = %s AND lower(surface) = %s
                    """,
                    (final_meaning, Jsonb(review_metadata), book_id, term),
                )
                counts["corrected"] += 1
            else:
                conn.execute(
                    """
                    UPDATE reader.book_glossary
                    SET meaning_zh = %s,
                        source = 'lifestudy_reviewed',
                        confidence = GREATEST(confidence, 0.95),
                        updated_at = now()
                    WHERE book_id = %s
                      AND lower(term) = %s
                      AND source <> 'user'
                    """,
                    (final_meaning, book_id, term),
                )
                conn.execute(
                    """
                    UPDATE reader.book_vocab_items
                    SET context_meaning = CASE
                            WHEN meaning_source = 'user_glossary' THEN context_meaning
                            ELSE %s
                        END,
                        meaning_source = CASE
                            WHEN meaning_source = 'user_glossary' THEN meaning_source
                            ELSE 'lifestudy_reviewed'
                        END,
                        alignment_status = CASE
                            WHEN meaning_source = 'user_glossary' THEN alignment_status
                            ELSE 'confirmed_context_meaning'
                        END,
                        status = CASE
                            WHEN status = 'ignored' THEN status
                            ELSE 'saved'
                        END,
                        metadata = metadata || %s,
                        updated_at = now()
                    WHERE book_id = %s AND lower(surface) = %s
                    """,
                    (final_meaning, Jsonb(review_metadata), book_id, term),
                )
                counts["approved"] += 1
        conn.commit()
    return dict(counts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply reviewed Genesis Life-study vocabulary decisions safely.")
    parser.add_argument("--review-pack", type=Path, default=DEFAULT_REVIEW_PACK)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--book-id", default="")
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--apply", action="store_true", help="Write reviewed decisions. Default is dry-run.")
    args = parser.parse_args()

    review_pack = load_review_pack(args.review_pack)
    overrides = load_overrides(args.overrides)
    decisions = build_review_decisions(review_pack, overrides)
    book_id = args.book_id or str(review_pack.get("target_book_id") or "")
    if not book_id:
        raise SystemExit("book_id is required")

    terms = [str(item["term"]) for item in decisions]
    preflight = db_preflight(args.database_url, book_id=book_id, terms=terms)
    decision_counts = Counter(str(item["decision"]) for item in decisions)
    accepted_count = decision_counts.get("approve", 0) + decision_counts.get("correct", 0)
    rejected_count = decision_counts.get("reject", 0)
    human_reviewed_precision = accepted_count / len(decisions) if decisions else 0.0
    missing_book_rows = max(0, len(terms) - int(preflight["book_glossary_count"])) + max(0, len(terms) - int(preflight["book_vocab_count"]))
    can_expand = (
        accepted_count + rejected_count == len(terms)
        and human_reviewed_precision >= REVIEWED_PRECISION_TARGET
        and missing_book_rows == 0
        and int(preflight["dictionary_pollution_count"]) == 0
    )
    result = {
        "ok": True,
        "schema": "sentence_reader.lifestudy_vocab_review_apply.v1",
        "mode": "apply" if args.apply else "dry_run",
        "database_write_performed": bool(args.apply),
        "review_pack": str(args.review_pack),
        "overrides": str(args.overrides),
        "book_id": book_id,
        "term_count": len(decisions),
        "decision_counts": {key: decision_counts.get(key, 0) for key in ["approve", "correct", "reject"]},
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "human_reviewed_precision": human_reviewed_precision,
        "reviewed_precision_target": REVIEWED_PRECISION_TARGET,
        "preflight": preflight,
        "missing_book_row_count": missing_book_rows,
        "can_expand_next_volume": can_expand,
        "can_expand_note": "true only when every Genesis item is reviewed, reviewed precision is >= 0.85, DB rows exist, and dictionary pollution is zero",
        "applied": {},
    }
    if args.apply:
        result["applied"] = apply_decisions(args.database_url, book_id=book_id, decisions=decisions, override_path=args.overrides)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
