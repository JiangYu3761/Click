#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"
SOURCE_CSV = REPORT_DIR / "lifestudy_frontend_candidate_review_v2_approve_after_human_check.csv"


DECISIONS: dict[str, dict[str, Any]] = {
    "living": {
        "decision": "learning_only",
        "final": "生活",
        "ready": False,
        "reason": "中文证据能支持学习义，但 living 多义，当前证据不足以作为前台优先释义。",
    },
    "saints": {"decision": "approve", "final": "圣徒", "ready": True, "reason": "中文证据直接对应。"},
    "expression": {"decision": "approve", "final": "表现", "ready": True, "reason": "中文证据直接对应；彰显可作为后续多义项另审。"},
    "apostles": {"decision": "approve", "final": "使徒", "ready": True, "reason": "中文证据直接对应，复数归并到中文单数词条。"},
    "experience": {"decision": "approve", "final": "经历", "ready": True, "reason": "中文证据直接对应。"},
    "salvation": {"decision": "approve", "final": "拯救", "ready": True, "reason": "当前证据句中 salvation 对应拯救；救恩义项留给后续多义审核。"},
    "principle": {"decision": "approve", "final": "原则", "ready": True, "reason": "中文证据直接对应。"},
    "element": {"decision": "approve", "final": "元素", "ready": True, "reason": "中文证据直接对应。"},
    "recovery": {"decision": "approve", "final": "恢复", "ready": True, "reason": "中文证据直接对应。"},
    "enjoyment": {"decision": "approve", "final": "享受", "ready": True, "reason": "中文证据直接对应。"},
    "gospel": {"decision": "approve", "final": "福音", "ready": True, "reason": "中文证据直接对应。"},
    "blessing": {"decision": "approve", "final": "祝福", "ready": True, "reason": "中文证据直接出现祝福，虽句子截断但对应关系清楚。"},
    "redemption": {"decision": "correct", "final": "救赎", "ready": True, "reason": "原候选拯救过宽；英文 redemption 在同句证据中对应救赎。"},
    "knowledge": {"decision": "approve", "final": "知识", "ready": True, "reason": "中文证据直接对应。"},
    "righteousness": {"decision": "correct", "final": "公义", "ready": True, "reason": "原候选公正对应 justice；righteousness 在证据中对应公义。"},
    "reality": {"decision": "correct", "final": "实际", "ready": True, "reason": "原候选事实来自 In fact；reality 在证据中对应实际。"},
    "heavenly": {"decision": "approve", "final": "天上的", "ready": True, "reason": "中文证据直接对应。"},
    "praise": {"decision": "approve", "final": "赞美", "ready": True, "reason": "中文证据直接对应。"},
    "sin": {"decision": "approve", "final": "罪", "ready": True, "reason": "中文证据直接对应。"},
    "grace": {"decision": "approve", "final": "恩典", "ready": True, "reason": "中文证据直接对应。"},
    "faith": {"decision": "approve", "final": "信心", "ready": True, "reason": "中文证据直接对应。"},
    "glory": {"decision": "approve", "final": "荣耀", "ready": True, "reason": "中文证据直接对应。"},
    "altar": {"decision": "approve", "final": "祭坛", "ready": True, "reason": "中文证据直接对应。"},
    "sacrifice": {
        "decision": "needs_more_evidence",
        "final": "牺牲",
        "ready": False,
        "reason": "当前证据支持牺牲，但 Life-study/圣经语境中还可能对应祭牲、祭物、祭；先不进前台。",
    },
    "anointing": {
        "decision": "correct",
        "final": "受膏；膏油的涂抹",
        "ready": True,
        "reason": "证据同时出现受膏和膏油的涂抹；单写受膏会漏掉名词用法。",
    },
    "priesthood": {"decision": "correct", "final": "祭司职分", "ready": True, "reason": "原候选被截短；中文证据完整表达为祭司职分。"},
    "sanctuary": {"decision": "approve", "final": "圣所", "ready": True, "reason": "中文证据直接对应。"},
    "consecration": {"decision": "approve", "final": "奉献", "ready": True, "reason": "中文证据直接对应。"},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_rows() -> list[dict[str, str]]:
    if not SOURCE_CSV.exists():
        raise SystemExit(f"missing source CSV: {SOURCE_CSV}")
    rows = list(csv.DictReader(SOURCE_CSV.open(encoding="utf-8-sig")))
    words = {str(row.get("word") or "").lower() for row in rows}
    missing = set(DECISIONS) - words
    extra = words - set(DECISIONS)
    if missing or extra:
        raise SystemExit(f"decision/source mismatch missing={sorted(missing)} extra={sorted(extra)}")
    return rows


def csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def evidence_supports(final_meaning: str, evidence_zh: str) -> bool:
    if not final_meaning:
        return False
    parts = [part.strip() for part in final_meaning.replace("/", "；").split("；") if part.strip()]
    return all(part in evidence_zh for part in parts)


def adjudicate_row(row: dict[str, str]) -> dict[str, Any]:
    word = str(row.get("word") or "").lower()
    decision = DECISIONS[word]
    final_meaning = str(decision["final"])
    evidence_zh = row.get("evidence_zh_simp") or ""
    ready = bool(decision["ready"])
    supported = evidence_supports(final_meaning, evidence_zh)
    if ready and not supported:
        raise SystemExit(f"ready row is not supported by Chinese evidence: {word} -> {final_meaning}")
    return {
        "word": word,
        "original_reviewed_meaning_zh_simp": row.get("reviewed_meaning_zh_simp") or "",
        "final_meaning_zh_simp": final_meaning,
        "codex_adjudication": decision["decision"],
        "codex_adjudication_reason": decision["reason"],
        "chinese_evidence_supports_final_meaning": supported,
        "front_end_candidate_ready": ready,
        "front_end_import_ready": False,
        "database_write_performed": False,
        "source_volume": row.get("source_volume") or "",
        "source_page": row.get("source_page") or "",
        "total_content_frequency": int(row.get("total_content_frequency") or 0),
        "volume_count": int(row.get("volume_count") or 0),
        "evidence_en": row.get("evidence_en") or "",
        "evidence_zh_simp": evidence_zh,
        "previous_suggested_frontend_decision": row.get("suggested_frontend_decision") or "",
        "learning_review_decision": row.get("learning_review_decision") or "",
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Life-study Frontend Candidate Adjudication V2",
        "",
        "这个文件是 Codex 代理审核结果，不写数据库。它把 28 个前台候选分成确定、修正、学习用、暂缓四类。",
        "",
        f"- Source rows: `{payload['quality']['source_rows']}`",
        f"- Codex reviewed rows: `{payload['quality']['codex_reviewed_rows']}`",
        f"- Front-end candidate ready: `{payload['quality']['front_end_candidate_ready_count']}`",
        f"- Front-end import ready: `{payload['quality']['front_end_import_ready_count']}`",
        f"- Database write performed: `{payload['database_write_performed']}`",
        "",
        "## Decision Counts",
        "",
    ]
    for decision, count in sorted(payload["quality"]["decision_counts"].items()):
        lines.append(f"- `{decision}`: `{count}`")
    lines.append("")
    lines.append("## Items")
    lines.append("")
    for row in payload["items"]:
        lines.extend(
            [
                f"### {row['word']} -> {row['final_meaning_zh_simp']}",
                "",
                f"- Decision: `{row['codex_adjudication']}`",
                f"- Ready for next dry-run candidate pack: `{row['front_end_candidate_ready']}`",
                f"- Reason: {row['codex_adjudication_reason']}",
                f"- Source: `{row['source_volume']} p{row['source_page']}`",
                f"- EN: {row['evidence_en']}",
                f"- ZH: {row['evidence_zh_simp']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rows = [adjudicate_row(row) for row in read_rows()]
    rows.sort(key=lambda row: (-int(row["front_end_candidate_ready"]), row["codex_adjudication"], row["word"]))
    ready_rows = [row for row in rows if row["front_end_candidate_ready"]]
    payload = {
        "schema": "sentence_reader.lifestudy_frontend_candidate_adjudication_v2.v1",
        "generated_at": now_iso(),
        "source_csv": str(SOURCE_CSV),
        "database_write_performed": False,
        "policy": "operator_delegated_codex_adjudication_no_db_write",
        "quality": {
            "source_rows": len(rows),
            "codex_reviewed_rows": len(rows),
            "front_end_candidate_ready_count": len(ready_rows),
            "front_end_import_ready_count": 0,
            "decision_counts": dict(Counter(row["codex_adjudication"] for row in rows)),
        },
        "items": rows,
    }

    json_path = REPORT_DIR / "lifestudy_frontend_candidate_adjudication_v2.json"
    csv_path = REPORT_DIR / "lifestudy_frontend_candidate_adjudication_v2.csv"
    ready_csv_path = REPORT_DIR / "lifestudy_frontend_candidate_adjudication_v2_ready_for_dry_run.csv"
    md_path = REPORT_DIR / "lifestudy_frontend_candidate_adjudication_v2.md"
    summary_path = REPORT_DIR / "lifestudy_frontend_candidate_adjudication_v2_summary.json"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, rows)
    write_csv(ready_csv_path, ready_rows)
    write_markdown(md_path, payload)
    summary = {k: payload[k] for k in ("schema", "generated_at", "source_csv", "database_write_performed", "policy", "quality")}
    summary["outputs"] = {
        "json": str(json_path),
        "csv": str(csv_path),
        "ready_for_dry_run_csv": str(ready_csv_path),
        "markdown": str(md_path),
        "summary": str(summary_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
