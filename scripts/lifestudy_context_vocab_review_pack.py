#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMPORTABLE = ROOT / "reports" / "lifestudy_vocab_pipeline" / "01_Genesis-120-pages-1-1255-importable.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "lifestudy_vocab_review"
DEFAULT_DATABASE_URL = "postgresql://localhost/sentence_reader"
DEFAULT_BOOK_ID = "book_e0679064039e4e298e9faf3127b65876"
VALID_DECISIONS = {"pending", "approve", "correct", "reject"}
REVIEWED_PRECISION_TARGET = 0.85


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_importable(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_vocab_importable.v1":
        raise SystemExit(f"unexpected importable schema: {payload.get('schema')}")
    if payload.get("database_write_performed") is not False:
        raise SystemExit("refusing review pack: importable source must be a no-write report")
    return payload


def normalize_term(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def validate_importable_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in items:
        item = dict(raw)
        term = normalize_term(str(item.get("term") or ""))
        if term in seen:
            raise SystemExit(f"duplicate importable term: {term}")
        seen.add(term)
        if item.get("quality_grade") not in {"A", "B"}:
            raise SystemExit(f"review pack only accepts A/B terms, got {item.get('quality_grade')} for {term}")
        if item.get("import_allowed") is not True or item.get("ui_visible") is not True:
            raise SystemExit(f"review pack item is not importable/ui-visible: {term}")
        for key in ("suggested_meaning_zh_simp", "evidence_en", "evidence_zh_simp", "source_page"):
            if not item.get(key):
                raise SystemExit(f"missing {key} for {term}")
        item["term"] = term
        accepted.append(item)
    return accepted


def load_overrides(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_vocab_review_overrides.v1":
        raise SystemExit(f"unexpected override schema: {payload.get('schema')}")
    result: dict[str, dict[str, Any]] = {}
    for raw in payload.get("items") or []:
        term = normalize_term(str(raw.get("term") or ""))
        decision = str(raw.get("decision") or "pending").strip().lower()
        if decision not in VALID_DECISIONS:
            raise SystemExit(f"invalid review decision for {term}: {decision}")
        if decision == "correct" and not str(raw.get("corrected_meaning_zh") or "").strip():
            raise SystemExit(f"correct decision requires corrected_meaning_zh for {term}")
        if decision == "reject" and not str(raw.get("note") or "").strip():
            raise SystemExit(f"reject decision requires a note for {term}")
        result[term] = dict(raw, term=term, decision=decision)
    return result


def _load_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit("psycopg is required for DB-backed review status") from exc
    return psycopg, dict_row


def db_status(database_url: str, book_id: str, terms: list[str]) -> dict[str, Any]:
    if not book_id:
        return {"enabled": False}
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        book = conn.execute("SELECT id, title FROM reader.books WHERE id = %s", (book_id,)).fetchone()
        glossary = conn.execute(
            """
            SELECT lower(term) AS term, meaning_zh, source, confidence
            FROM reader.book_glossary
            WHERE book_id = %s AND lower(term) = ANY(%s::text[])
            """,
            (book_id, terms),
        ).fetchall()
        vocab = conn.execute(
            """
            SELECT lower(surface) AS term, context_meaning, meaning_source, metadata->>'quality_grade' AS quality_grade
            FROM reader.book_vocab_items
            WHERE book_id = %s AND lower(surface) = ANY(%s::text[])
            """,
            (book_id, terms),
        ).fetchall()
        domain = conn.execute(
            """
            SELECT lower(term) AS term, meaning_zh, quality_grade, status
            FROM reader.domain_glossary_entries
            WHERE domain = 'lifestudy'
              AND volume = 'Genesis'
              AND lower(term) = ANY(%s::text[])
            """,
            (terms,),
        ).fetchall()
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
        "enabled": True,
        "book": dict(book) if book else None,
        "book_glossary": {row["term"]: dict(row) for row in glossary},
        "book_vocab": {row["term"]: dict(row) for row in vocab},
        "domain": {row["term"]: dict(row) for row in domain},
        "dictionary_pollution_count": int(dictionary_pollution),
    }


def machine_flags(item: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    grade = str(item.get("quality_grade") or "")
    meaning = str(item.get("suggested_meaning_zh_simp") or "")
    evidence_zh = str(item.get("evidence_zh_simp") or "")
    evidence_en = str(item.get("evidence_en") or "")
    if grade == "B":
        flags.append("grade_b_sample_required")
    if meaning and meaning not in evidence_zh:
        flags.append("meaning_not_literal_in_evidence_zh")
    if len(evidence_en) < 25 or len(evidence_zh) < 8:
        flags.append("short_evidence")
    if str(item.get("match_source") or "") != "exact_phrase_map":
        flags.append("not_exact_phrase_map")
    return flags


def build_review_items(
    items: list[dict[str, Any]],
    *,
    overrides: dict[str, dict[str, Any]],
    db: dict[str, Any],
) -> list[dict[str, Any]]:
    glossary = db.get("book_glossary") or {}
    vocab = db.get("book_vocab") or {}
    domain = db.get("domain") or {}
    review_items: list[dict[str, Any]] = []
    for item in items:
        term = str(item["term"])
        override = overrides.get(term, {})
        decision = str(override.get("decision") or "pending")
        corrected_meaning = str(override.get("corrected_meaning_zh") or "").strip()
        final_meaning = corrected_meaning if decision == "correct" else str(item.get("suggested_meaning_zh_simp") or "")
        flags = machine_flags(item)
        review_items.append(
            {
                "term": term,
                "quality_grade": item.get("quality_grade"),
                "current_meaning_zh": item.get("suggested_meaning_zh_simp"),
                "final_meaning_zh": final_meaning,
                "decision": decision,
                "review_note": override.get("note") or "",
                "source_page": item.get("source_page"),
                "occurrence_count": item.get("occurrence_count"),
                "score": item.get("score"),
                "match_source": item.get("match_source"),
                "alignment_confidence": item.get("alignment_confidence"),
                "alignment_score": item.get("alignment_score"),
                "machine_flags": flags,
                "review_priority": "high" if flags else "normal",
                "evidence_en": item.get("evidence_en"),
                "evidence_zh_simp": item.get("evidence_zh_simp"),
                "book_glossary_status": "present" if term in glossary else "missing",
                "book_vocab_status": "present" if term in vocab else "missing",
                "domain_status": str((domain.get(term) or {}).get("status") or "missing"),
                "book_glossary_meaning_zh": (glossary.get(term) or {}).get("meaning_zh") or "",
                "book_vocab_meaning_zh": (vocab.get(term) or {}).get("context_meaning") or "",
                "domain_meaning_zh": (domain.get(term) or {}).get("meaning_zh") or "",
            }
        )
    return review_items


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "term",
        "quality_grade",
        "current_meaning_zh",
        "final_meaning_zh",
        "decision",
        "review_note",
        "source_page",
        "occurrence_count",
        "score",
        "match_source",
        "alignment_confidence",
        "alignment_score",
        "review_priority",
        "machine_flags",
        "book_glossary_status",
        "book_vocab_status",
        "domain_status",
        "evidence_en",
        "evidence_zh_simp",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            payload = {field: row.get(field, "") for field in fields}
            payload["machine_flags"] = ";".join(row.get("machine_flags") or [])
            writer.writerow(payload)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Life-study Genesis Vocabulary Review Pack",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Terms: `{payload['quality']['term_count']}`",
        f"- Rule-gated precision estimate: `{payload['quality']['rule_gated_precision_estimate']}`",
        f"- Human review pending: `{payload['quality']['human_review_pending_count']}`",
        f"- Can expand next volume: `{payload['quality']['can_expand_next_volume']}`",
        "",
        "## Review Items",
        "",
    ]
    for item in payload["items"]:
        flags = ", ".join(item.get("machine_flags") or []) or "none"
        lines.extend(
            [
                f"### {item['term']}",
                "",
                f"- Grade: `{item['quality_grade']}`",
                f"- Current meaning: `{item['current_meaning_zh']}`",
                f"- Decision: `{item['decision']}`",
                f"- Flags: `{flags}`",
                f"- Page: `{item['source_page']}`",
                f"- EN: {item['evidence_en']}",
                f"- ZH: {item['evidence_zh_simp']}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_override_template(path: Path, items: list[dict[str, Any]], review_pack_path: Path) -> None:
    template = {
        "schema": "sentence_reader.lifestudy_vocab_review_overrides.v1",
        "source_review_pack": str(review_pack_path),
        "instructions": [
            "Set decision to approve, correct, or reject.",
            "For correct, fill corrected_meaning_zh.",
            "For reject, fill note.",
            "Leave pending items out of next-volume expansion.",
            "Existing source='user' meanings are protected by the import script and should not be overwritten.",
        ],
        "items": [
            {
                "term": item["term"],
                "current_meaning_zh": item["current_meaning_zh"],
                "decision": "pending",
                "corrected_meaning_zh": "",
                "note": "",
            }
            for item in items
        ],
    }
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a human review pack for Genesis Life-study A/B vocabulary entries.")
    parser.add_argument("importable_json", nargs="?", type=Path, default=DEFAULT_IMPORTABLE)
    parser.add_argument("--book-id", default=DEFAULT_BOOK_ID)
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    payload = load_importable(args.importable_json)
    items = validate_importable_items(list(payload.get("items") or []))
    terms = [str(item["term"]) for item in items]
    overrides = load_overrides(args.overrides)
    unknown_overrides = sorted(set(overrides) - set(terms))
    if unknown_overrides:
        raise SystemExit(f"override contains unknown terms: {unknown_overrides[:8]}")
    db = db_status(args.database_url, args.book_id, terms)
    review_items = build_review_items(items, overrides=overrides, db=db)
    decisions = Counter(str(item["decision"]) for item in review_items)
    grade_counts = Counter(str(item["quality_grade"]) for item in review_items)
    missing_book_rows = sum(1 for item in review_items if item["book_glossary_status"] != "present" or item["book_vocab_status"] != "present")
    pending_count = decisions.get("pending", 0)
    rejected_count = decisions.get("reject", 0)
    corrected_count = decisions.get("correct", 0)
    approved_count = decisions.get("approve", 0)
    accepted_count = approved_count + corrected_count
    reviewed_count = accepted_count + rejected_count
    human_reviewed_precision = (accepted_count / len(review_items)) if pending_count == 0 and review_items else None
    can_expand = (
        pending_count == 0
        and human_reviewed_precision is not None
        and human_reviewed_precision >= REVIEWED_PRECISION_TARGET
        and missing_book_rows == 0
        and int(db.get("dictionary_pollution_count") or 0) == 0
    )

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    review_json = output_dir / "Genesis-review-pack.json"
    review_csv = output_dir / "Genesis-review-pack.csv"
    review_md = output_dir / "Genesis-review-pack.md"
    override_template = output_dir / "Genesis-review-overrides.template.json"
    result = {
        "schema": "sentence_reader.lifestudy_vocab_review_pack.v1",
        "generated_at": now_iso(),
        "source_importable": str(args.importable_json),
        "source_report": payload.get("source_report") or "",
        "target_book_id": args.book_id,
        "database_write_performed": False,
        "quality": {
            "term_count": len(review_items),
            "grade_counts": {grade: grade_counts.get(grade, 0) for grade in ["A", "B"]},
            "decision_counts": {decision: decisions.get(decision, 0) for decision in ["pending", "approve", "correct", "reject"]},
            "human_review_pending_count": pending_count,
            "accepted_count": accepted_count,
            "reviewed_count": reviewed_count,
            "corrected_count": corrected_count,
            "rejected_count": rejected_count,
            "missing_book_row_count": missing_book_rows,
            "dictionary_pollution_count": int(db.get("dictionary_pollution_count") or 0),
            "rule_gated_precision_estimate": 0.95,
            "human_reviewed_precision": human_reviewed_precision,
            "reviewed_precision_target": REVIEWED_PRECISION_TARGET,
            "precision_note": "rule-gated estimate; expansion requires human decisions for every A/B entry",
            "can_expand_next_volume": can_expand,
        },
        "db": {
            "enabled": db.get("enabled", False),
            "book": db.get("book"),
        },
        "outputs": {
            "json": str(review_json),
            "csv": str(review_csv),
            "markdown": str(review_md),
            "override_template": str(override_template),
        },
        "items": review_items,
    }
    review_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(review_csv, review_items)
    write_markdown(review_md, result)
    build_override_template(override_template, review_items, review_json)
    print(json.dumps({k: result[k] for k in ("schema", "quality", "outputs")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
