#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "reader_api" / "app.py"
REVIEW_PACK = ROOT / "reports" / "lifestudy_vocab_review" / "Genesis-review-pack.json"


def fail(message: str) -> int:
    print(f"lifestudy context vocab review ui smoke FAIL: {message}")
    return 1


def main() -> int:
    if not APP.exists():
        return fail(f"missing app: {APP}")
    if not REVIEW_PACK.exists():
        return fail(f"missing review pack: {REVIEW_PACK}")
    source = APP.read_text(encoding="utf-8")
    markers = [
        "def lifestudy_vocab_review_page_html",
        "/lifestudy/vocab/review",
        "/api/lifestudy/vocab/review",
        "sentence_reader.lifestudy_vocab_review_api.v1",
        "sentence_reader.lifestudy_vocab_review_dry_run.v1",
        "Genesis-review-overrides.reviewed.json",
        "database_write_performed",
        "只保存审校文件，不直接写数据库。",
    ]
    missing = [marker for marker in markers if marker not in source]
    if missing:
        return fail(f"missing static markers: {missing}")

    sys.path.insert(0, str(ROOT))
    import reader_api.app as app_module

    client = TestClient(app_module.app)
    page = client.get("/lifestudy/vocab/review")
    if page.status_code != 200:
        return fail(f"review page status={page.status_code}")
    page_text = page.text
    for marker in ("生命读经词库审校", "Dry-run", "/api/lifestudy/vocab/review/decision"):
        if marker not in page_text:
            return fail(f"review page missing marker: {marker}")

    payload = client.get("/api/lifestudy/vocab/review")
    if payload.status_code != 200:
        return fail(f"review api status={payload.status_code} body={payload.text[:200]}")
    data = payload.json()
    if data.get("schema") != "sentence_reader.lifestudy_vocab_review_api.v1":
        return fail(f"unexpected schema: {data.get('schema')}")
    if data.get("database_write_performed") is not False:
        return fail("review api must not write database")
    if len(data.get("items") or []) != 25:
        return fail(f"expected 25 review items, got {len(data.get('items') or [])}")
    if data.get("decision_counts", {}).get("pending") != 25:
        return fail(f"expected 25 pending decisions, got {data.get('decision_counts')}")
    if data.get("can_expand_next_volume") is not False:
        return fail("pending review api must block next-volume expansion")
    if data.get("reviewed_precision_target") != 0.85:
        return fail(f"unexpected reviewed precision target: {data.get('reviewed_precision_target')}")

    dry_run = client.post("/api/lifestudy/vocab/review/dry-run")
    if dry_run.status_code != 200:
        return fail(f"dry-run api status={dry_run.status_code} body={dry_run.text[:200]}")
    dry_run_data = dry_run.json()
    if dry_run_data.get("schema") != "sentence_reader.lifestudy_vocab_review_dry_run.v1":
        return fail(f"unexpected dry-run schema: {dry_run_data.get('schema')}")
    if dry_run_data.get("database_write_performed") is not False:
        return fail("dry-run endpoint must not write database")
    if dry_run_data.get("ok") is not False:
        return fail("pending dry-run must fail until every item is reviewed")
    if "pending" not in str(dry_run_data.get("stderr") or ""):
        return fail("pending dry-run should explain pending decisions")

    print("lifestudy context vocab review ui smoke PASS items=25 pending=25 no_db_write=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
