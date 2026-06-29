#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BILINGUAL_DIR = Path(
    "/Users/jiangyu/Documents/资料归档/夸克网盘/2026-06-13_夸克下载_综合资料包/"
    "01_属灵书报与诗歌/L-书报/约瑟/1.PDF 正版属灵书籍（全）/"
    "1.正版/pdf 12 生命读经/中英对照"
)
PIPELINE_DIR = ROOT / "reports" / "lifestudy_vocab_pipeline"
OUTPUT_DIR = ROOT / "reports" / "lifestudy_vocab_corpus"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def pipeline_stem(pdf: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", pdf.stem).strip("-") or "lifestudy"


def parse_volume(pdf: Path) -> dict[str, Any]:
    name = pdf.name
    match = re.match(r"(?P<index>\d+(?:-\d+)?)_(?P<title>[^()]+)(?:\((?P<count>\d+)\))?\.pdf$", name)
    if not match:
        return {
            "volume_index": "",
            "title_en": pdf.stem,
            "message_count_hint": None,
            "is_combined_volume": name.startswith("00_"),
        }
    count = match.group("count")
    return {
        "volume_index": match.group("index"),
        "title_en": match.group("title"),
        "message_count_hint": int(count) if count else None,
        "is_combined_volume": name.startswith("00_") or "-" in match.group("index"),
    }


def pipeline_status(pdf: Path) -> dict[str, Any]:
    stem = pipeline_stem(pdf)
    first50 = sorted(PIPELINE_DIR.glob(f"{stem}-pages-1-50-pipeline.json"))
    importable50 = sorted(PIPELINE_DIR.glob(f"{stem}-pages-1-50-importable.json"))
    full = sorted(PIPELINE_DIR.glob(f"{stem}-pages-1-*-pipeline.json"))
    full = [path for path in full if "-pages-1-50-" not in path.name]
    full_importable = sorted(PIPELINE_DIR.glob(f"{stem}-pages-1-*-importable.json"))
    full_importable = [path for path in full_importable if "-pages-1-50-" not in path.name]
    return {
        "pipeline_stem": stem,
        "first50_pipeline": str(first50[-1]) if first50 else "",
        "first50_importable": str(importable50[-1]) if importable50 else "",
        "full_pipeline": str(full[-1]) if full else "",
        "full_importable": str(full_importable[-1]) if full_importable else "",
        "first50_done": bool(first50 and importable50),
        "full_done": bool(full and full_importable),
    }


def build_inventory() -> dict[str, Any]:
    if not BILINGUAL_DIR.exists():
        raise SystemExit(f"bilingual PDF dir not found: {BILINGUAL_DIR}")
    rows: list[dict[str, Any]] = []
    for pdf in sorted(BILINGUAL_DIR.glob("*.pdf")):
        parsed = parse_volume(pdf)
        status = pipeline_status(pdf)
        if parsed["is_combined_volume"]:
            next_action = "skip_combined_reference"
        elif status["full_done"]:
            next_action = "skip_already_full_done"
        elif status["first50_done"]:
            next_action = "run_full_no_write_after_spot_check"
        else:
            next_action = "run_first50_no_write_probe"
        rows.append(
            {
                "pdf": str(pdf),
                "file_name": pdf.name,
                "file_size_mb": round(pdf.stat().st_size / 1024 / 1024, 2),
                **parsed,
                **status,
                "next_action": next_action,
            }
        )
    counts = {
        "total_pdf_count": len(rows),
        "combined_reference_count": sum(1 for row in rows if row["is_combined_volume"]),
        "processable_volume_count": sum(1 for row in rows if not row["is_combined_volume"]),
        "first50_done_count": sum(1 for row in rows if row["first50_done"]),
        "full_done_count": sum(1 for row in rows if row["full_done"]),
        "needs_first50_probe_count": sum(1 for row in rows if row["next_action"] == "run_first50_no_write_probe"),
        "needs_full_run_count": sum(1 for row in rows if row["next_action"] == "run_full_no_write_after_spot_check"),
    }
    return {
        "schema": "sentence_reader.lifestudy_corpus_inventory.v1",
        "generated_at": now_iso(),
        "database_write_performed": False,
        "bilingual_pdf_dir": str(BILINGUAL_DIR),
        "policy": "inventory_only_skip_existing_outputs",
        "counts": counts,
        "items": rows,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "volume_index",
        "title_en",
        "file_name",
        "message_count_hint",
        "file_size_mb",
        "is_combined_volume",
        "first50_done",
        "full_done",
        "next_action",
        "first50_pipeline",
        "full_pipeline",
        "pdf",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Life-study Corpus Inventory",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Policy: `{payload['policy']}`",
        f"- Processable volumes: `{payload['counts']['processable_volume_count']}`",
        f"- First-50 done: `{payload['counts']['first50_done_count']}`",
        f"- Full done: `{payload['counts']['full_done_count']}`",
        f"- Needs first-50 probe: `{payload['counts']['needs_first50_probe_count']}`",
        f"- Needs full run: `{payload['counts']['needs_full_run_count']}`",
        "",
        "| Volume | Title | First 50 | Full | Next action |",
        "|---|---|---:|---:|---|",
    ]
    for row in payload["items"]:
        lines.append(
            "| {volume_index} | {title_en} | {first50_done} | {full_done} | `{next_action}` |".format(**row)
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    payload = build_inventory()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "lifestudy_corpus_inventory.json"
    csv_path = OUTPUT_DIR / "lifestudy_corpus_inventory.csv"
    md_path = OUTPUT_DIR / "lifestudy_corpus_inventory.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, payload["items"])
    write_markdown(md_path, payload)
    print(json.dumps({"schema": payload["schema"], "counts": payload["counts"], "outputs": {"json": str(json_path), "csv": str(csv_path), "markdown": str(md_path)}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
