#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"
DEFAULT_REVIEW_PACK = REPORT_DIR / "lifestudy_vocab_v1_review_pack.json"


def csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def readable_row(row: dict[str, Any]) -> dict[str, Any]:
    candidate = str(row.get("candidate_meaning_zh_simp") or "").strip()
    source = str(row.get("context_meaning_source") or "").strip()
    decision = str(row.get("review_decision") or "").strip()
    evidence_en = str(row.get("evidence_en") or "").strip()
    evidence_zh = str(row.get("evidence_zh_simp") or "").strip()

    if candidate:
        display_meaning = candidate
        blank_reason = ""
        next_action = "已自动审核，可进入 Life-study 语境词库"
    elif evidence_en and evidence_zh:
        display_meaning = "待审：有中英上下文，但未自动抽出可入库中文短义"
        blank_reason = "没有命中已知 Life-study 术语映射；为了避免凭空编释义，candidate 字段保持空白"
        next_action = "人工或规则二审：从 evidence_zh_simp 里抽出中文短义，确认后再 approve/correct"
    else:
        display_meaning = "待审：缺少可用中英证据"
        blank_reason = "没有足够上下文证据"
        next_action = "回到对齐语料补证据；没有证据则 reject"

    return {
        "term": row.get("term") or row.get("\ufeffterm") or "",
        "lemma": row.get("lemma") or "",
        "display_meaning_zh_simp": display_meaning,
        "candidate_meaning_zh_simp": candidate,
        "blank_reason_zh_simp": blank_reason,
        "review_decision": decision,
        "review_status": row.get("review_status") or "",
        "import_ready": row.get("import_ready") is True,
        "quality_grade": row.get("quality_grade") or "",
        "context_meaning_source": source,
        "context_meaning_confidence": row.get("context_meaning_confidence") or "",
        "next_action_zh_simp": next_action,
        "total_content_frequency": row.get("total_content_frequency") or 0,
        "volume_count": row.get("volume_count") or 0,
        "source_volume": row.get("source_volume") or "",
        "source_page": row.get("source_page") or "",
        "evidence_en": evidence_en,
        "evidence_zh_simp": evidence_zh,
        "meaning_variants": row.get("meaning_variants") or [],
        "variant_words": row.get("variant_words") or [],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def write_markdown(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    focus = [row for row in rows if not row["import_ready"]][:80]
    lines = [
        "# Life-study Vocabulary V1 Readable Review",
        "",
        "这个文件用于看全量审核进度，不是入库文件。",
        "",
        f"- Total review rows: `{summary['total_rows']}`",
        f"- Import-ready rows: `{summary['import_ready_count']}`",
        f"- Needs-review rows: `{summary['needs_review_count']}`",
        f"- Blank candidate rows: `{summary['blank_candidate_count']}`",
        "",
        "## Why Candidate Meaning Is Blank",
        "",
        "`candidate_meaning_zh_simp` 只放可以作为 Life-study 语境义入库的中文短义。",
        "如果只有中英文上下文、但程序没有可靠抽出短义，就保持空白，避免把猜测写成词典释义。",
        "",
    ]
    for row in focus:
        lines.extend(
            [
                f"## {row['term']}",
                "",
                f"- Display meaning: {row['display_meaning_zh_simp']}",
                f"- Blank reason: {row['blank_reason_zh_simp']}",
                f"- Frequency: `{row['total_content_frequency']}`",
                f"- Source: `{row['source_volume']} p{row['source_page']}`",
                f"- Next action: {row['next_action_zh_simp']}",
                f"- EN: {row['evidence_en']}",
                f"- ZH: {row['evidence_zh_simp']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    review = read_json(DEFAULT_REVIEW_PACK)
    if review.get("database_write_performed") is not False:
        raise SystemExit("refusing to build readable review from a DB-writing report")
    items = review.get("items") or []
    rows = [readable_row(item) for item in items]
    summary = {
        "schema": "sentence_reader.lifestudy_context_vocab_v1_readable_review.v1",
        "source_review_pack": str(DEFAULT_REVIEW_PACK),
        "database_write_performed": False,
        "total_rows": len(rows),
        "import_ready_count": sum(1 for row in rows if row["import_ready"]),
        "needs_review_count": sum(1 for row in rows if row["review_decision"] == "needs_review"),
        "blank_candidate_count": sum(1 for row in rows if not row["candidate_meaning_zh_simp"]),
        "review_decision_counts": dict(Counter(row["review_decision"] for row in rows)),
        "context_meaning_source_counts": dict(Counter(row["context_meaning_source"] for row in rows)),
    }

    csv_path = REPORT_DIR / "lifestudy_vocab_v1_review_pack_readable.csv"
    md_path = REPORT_DIR / "lifestudy_vocab_v1_review_pack_readable.md"
    json_path = REPORT_DIR / "lifestudy_vocab_v1_review_pack_readable_summary.json"
    write_csv(csv_path, rows)
    write_markdown(md_path, rows, summary)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "outputs": {"csv": str(csv_path), "markdown": str(md_path), "summary": str(json_path)}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
