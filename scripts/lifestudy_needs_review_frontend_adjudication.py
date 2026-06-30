#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"
QUEUE_SCRIPT = ROOT / "scripts" / "lifestudy_needs_review_frontend_queue.py"
QUEUE_CSV = REPORT_DIR / "lifestudy_needs_review_frontend_queue_top300.csv"

READY_AS_IS = {
    "building": {"meaning": "建筑", "reason": "同条证据中 God's building 对应神的建筑；前台短义稳定。"},
    "function": {"meaning": "功能", "reason": "同条证据中 salting function 对应盐的功能；短义稳定。"},
    "holy": {"meaning": "神圣的", "reason": "同条证据中 divine/holy 语境清楚，中文证据直接支持神圣的。"},
    "local": {"meaning": "地方性的", "reason": "同条证据中 local name 对应地方性的名称；短义稳定。"},
    "peace": {"meaning": "和平", "reason": "同条证据中 no peace 对应没有和平；短义稳定。"},
    "pray": {"meaning": "祈祷", "reason": "同条证据中 prayed/pray 对应祈祷；短义稳定。"},
    "prayer": {"meaning": "祈祷", "reason": "同条证据中 prayer by fasting 对应禁食祈祷；短义稳定。"},
    "preach": {"meaning": "讲道", "reason": "同条证据中 preach to people 对应对人讲道；短义稳定。"},
    "riches": {"meaning": "财富", "reason": "同条证据中 riches 对应财富；短义稳定。"},
    "sermon": {"meaning": "讲道", "reason": "二审已纠正；同条证据中 sermons 对应讲道。"},
    "testify": {"meaning": "作证", "reason": "同条证据中 testify against him 对应作证某人；短义稳定。"},
}

CORRECTED_FOR_FRONTEND = {
    "ascension": {"meaning": "升天", "reason": "原候选“耶稣升天”过窄；同条中文证据中“在耶稣升天以后”支持 ascension -> 升天。"},
    "authority": {"meaning": "权柄", "reason": "原候选“权力”只覆盖 power；同条证据中 power and authority 对应权力和权柄，authority 应为权柄。"},
    "misused": {"meaning": "误用", "reason": "二审已纠正；同条中文证据中 misused 对应误用。"},
    "parable": {"meaning": "比喻", "reason": "原候选“寓言”对应 allegory；同条证据中 parable or allegory 对应比喻或寓言，parable 应为比喻。"},
    "vision": {"meaning": "异象", "reason": "原候选“眼光”只对应 view；同条证据中 view, his vision 对应眼光，他的异象，vision 应为异象。"},
}

HOLD_FOR_MORE_EVIDENCE = {
    "inheritance": "圣经语境中可能对应基业、产业、遗产；当前证据只支持遗产，先不作为前台优先义。",
    "minister": "当前证据支持牧师，但 Life-study 语境中 minister/ministry 常有服事者、供应者等义项；先不进前台。",
    "truth": "当前证据是 tell you the truth -> 事实，不是 Life-study 常用的真理；不作为领域优先义。",
}

REJECT_FOR_FRONTEND = {
    "heart": "当前候选中心来自叙述结构，不适合把 heart 前台显示为中心。",
    "desire": "当前候选要求与 desire 的常用 Life-study 语境不稳，不能前台化。",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_queue() -> None:
    if QUEUE_CSV.exists():
        return
    proc = subprocess.run([sys.executable, str(QUEUE_SCRIPT)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip())


def load_queue() -> list[dict[str, str]]:
    ensure_queue()
    rows = list(csv.DictReader(QUEUE_CSV.open(encoding="utf-8-sig")))
    if len(rows) != 300:
        raise SystemExit(f"expected Top300 queue rows, got {len(rows)}")
    if any(row.get("database_write_performed") != "false" for row in rows):
        raise SystemExit("queue rows must be no-write")
    if any(row.get("front_end_import_ready") != "false" for row in rows):
        raise SystemExit("queue rows must not already be import-ready")
    return rows


def meaning_supported(meaning: str, evidence_zh: str) -> bool:
    parts = [part.strip() for part in re.split(r"[；;/]", meaning or "") if part.strip()]
    return bool(parts) and all(part in (evidence_zh or "") for part in parts)


def english_supported(word: str, evidence_en: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", evidence_en or "", re.IGNORECASE))


def adjudicate(row: dict[str, str]) -> dict[str, Any]:
    word = str(row.get("word") or "").strip().lower()
    original = str(row.get("candidate_meaning_zh_simp") or "").strip()
    evidence_en = row.get("evidence_en") or ""
    evidence_zh = row.get("evidence_zh_simp") or ""
    if word in READY_AS_IS:
        final = READY_AS_IS[word]["meaning"]
        decision = "frontend_ready"
        reason = READY_AS_IS[word]["reason"]
    elif word in CORRECTED_FOR_FRONTEND:
        final = CORRECTED_FOR_FRONTEND[word]["meaning"]
        decision = "frontend_corrected"
        reason = CORRECTED_FOR_FRONTEND[word]["reason"]
    elif word in REJECT_FOR_FRONTEND:
        final = ""
        decision = "reject"
        reason = REJECT_FOR_FRONTEND[word]
    elif word in HOLD_FOR_MORE_EVIDENCE:
        final = ""
        decision = "needs_more_evidence"
        reason = HOLD_FOR_MORE_EVIDENCE[word]
    elif row.get("frontend_queue_bucket") == "frontend_candidate":
        final = ""
        decision = "needs_more_evidence"
        reason = "优先级进入队列，但还没有足够规则证明可作为前台优先义。"
    else:
        final = original
        decision = "learning_only_keep"
        reason = "保留学习用途，不进入前台优先词典。"

    if decision in {"frontend_ready", "frontend_corrected"}:
        if not english_supported(word, evidence_en):
            raise SystemExit(f"front-end row missing English evidence hit: {word}")
        if not meaning_supported(final, evidence_zh):
            raise SystemExit(f"front-end row meaning not found in Chinese evidence: {word} -> {final}")

    return {
        "word": word,
        "original_meaning_zh_simp": original,
        "final_meaning_zh_simp": final,
        "frontend_adjudication": decision,
        "frontend_adjudication_reason": reason,
        "chinese_evidence_supports_final_meaning": decision in {"frontend_ready", "frontend_corrected"},
        "front_end_candidate_ready": decision in {"frontend_ready", "frontend_corrected"},
        "front_end_import_ready": False,
        "database_write_performed": False,
        "source_batch": "lifestudy_needs_review_frontend_v1",
        "quality_grade": "B" if decision in {"frontend_ready", "frontend_corrected"} else "",
        "confidence": "0.9" if decision in {"frontend_ready", "frontend_corrected"} else "",
        "source_split": row.get("source_split") or "",
        "source_volume": row.get("source_volume") or "",
        "source_page": row.get("source_page") or "",
        "total_content_frequency": int(float(row.get("total_content_frequency") or 0)),
        "volume_count": int(float(row.get("volume_count") or 0)),
        "frontend_priority_score": row.get("frontend_priority_score") or "",
        "frontend_priority_reasons": row.get("frontend_priority_reasons") or "",
        "evidence_en": evidence_en,
        "evidence_zh_simp": evidence_zh,
    }


def csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fieldnames})


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Life-study Needs-review Frontend Adjudication",
        "",
        "本文件只对 2,205 needs_manual_review 二审结果派生出来的 Top300 队列做前台级裁定；它不写数据库。",
        "",
        f"- Reviewed rows: `{payload['quality']['reviewed_rows']}`",
        f"- Frontend ready: `{payload['quality']['frontend_ready_count']}`",
        f"- Frontend corrected: `{payload['quality']['frontend_corrected_count']}`",
        f"- Import ready now: `{payload['quality']['front_end_import_ready_count']}`",
        f"- Database write performed: `{payload['database_write_performed']}`",
        "",
        "## Decision Counts",
        "",
    ]
    for decision, count in sorted(payload["quality"]["decision_counts"].items()):
        lines.append(f"- `{decision}`: `{count}`")
    lines.append("")
    for row in payload["items"][:100]:
        lines.extend(
            [
                f"## {row['word']} -> {row['final_meaning_zh_simp'] or row['original_meaning_zh_simp']}",
                "",
                f"- Decision: `{row['frontend_adjudication']}`",
                f"- Reason: {row['frontend_adjudication_reason']}",
                f"- Ready for dry-run/apply: `{row['front_end_candidate_ready']}`",
                f"- Source: `{row['source_volume']} p{row['source_page']}`",
                f"- EN: {row['evidence_en']}",
                f"- ZH: {row['evidence_zh_simp']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rows = [adjudicate(row) for row in load_queue()]
    rows.sort(
        key=lambda row: (
            not row["front_end_candidate_ready"],
            row["frontend_adjudication"],
            -int(row["total_content_frequency"]),
            row["word"],
        )
    )
    ready_rows = [row for row in rows if row["front_end_candidate_ready"]]
    payload = {
        "schema": "sentence_reader.lifestudy_needs_review_frontend_adjudication.v1",
        "generated_at": now_iso(),
        "source_csv": str(QUEUE_CSV),
        "database_write_performed": False,
        "policy": "frontend_grade_adjudication_from_needs_review_top300_no_db_write",
        "quality": {
            "reviewed_rows": len(rows),
            "frontend_ready_count": sum(1 for row in rows if row["frontend_adjudication"] == "frontend_ready"),
            "frontend_corrected_count": sum(1 for row in rows if row["frontend_adjudication"] == "frontend_corrected"),
            "learning_only_keep_count": sum(1 for row in rows if row["frontend_adjudication"] == "learning_only_keep"),
            "reject_count": sum(1 for row in rows if row["frontend_adjudication"] == "reject"),
            "needs_more_evidence_count": sum(1 for row in rows if row["frontend_adjudication"] == "needs_more_evidence"),
            "front_end_candidate_ready_count": len(ready_rows),
            "front_end_import_ready_count": 0,
            "decision_counts": dict(Counter(row["frontend_adjudication"] for row in rows)),
        },
        "items": rows,
    }
    json_path = REPORT_DIR / "lifestudy_needs_review_frontend_adjudication.json"
    csv_path = REPORT_DIR / "lifestudy_needs_review_frontend_adjudication.csv"
    ready_csv_path = REPORT_DIR / "lifestudy_needs_review_frontend_ready_for_dry_run.csv"
    md_path = REPORT_DIR / "lifestudy_needs_review_frontend_adjudication.md"
    summary_path = REPORT_DIR / "lifestudy_needs_review_frontend_adjudication_summary.json"
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
