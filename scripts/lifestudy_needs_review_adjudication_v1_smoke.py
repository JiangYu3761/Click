#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_needs_review_adjudication_v1.py"
BASE = ROOT / "reports" / "lifestudy_vocab_corpus"
SOURCE = BASE / "lifestudy_dictionary_guided_review_v2_needs_manual_review.csv"
SUMMARY = BASE / "lifestudy_needs_review_adjudication_v1_summary.json"
CSV = BASE / "lifestudy_needs_review_adjudication_v1.csv"
CORRECTED = BASE / "lifestudy_needs_review_corrected_learning_candidate.csv"
LEARNING = BASE / "lifestudy_needs_review_learning_only.csv"
REJECT = BASE / "lifestudy_needs_review_reject.csv"
STILL = BASE / "lifestudy_needs_review_still_needs_manual_review.csv"


def fail(message: str) -> int:
    print(f"lifestudy needs-review adjudication v1 smoke FAIL: {message}", file=sys.stderr)
    return 1


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def ensure_report() -> int:
    if SUMMARY.exists() and CSV.exists() and LEARNING.exists() and REJECT.exists() and STILL.exists():
        return 0
    code, stdout, stderr = run([sys.executable, str(SCRIPT)])
    if code != 0:
        return fail(stderr.strip() or stdout.strip())
    return 0


def clean_zh(text: str) -> str:
    import re

    chinese_book_titles = (
        "创世记",
        "出埃及记",
        "利未记",
        "民数记",
        "申命记",
        "约书亚记",
        "士师记",
        "路得记",
        "撒母耳记",
        "列王纪",
        "历代志",
        "以斯拉记",
        "尼希米记",
        "以斯帖记",
        "约伯记",
        "诗篇",
        "箴言",
        "传道书",
        "雅歌",
        "以赛亚书",
        "耶利米书",
        "耶利米哀歌",
        "以西结书",
        "但以理书",
        "马太福音",
        "马可福音",
        "路加福音",
        "约翰福音",
        "使徒行传",
        "罗马书",
        "哥林多前书",
        "哥林多后书",
        "加拉太书",
        "以弗所书",
        "腓立比书",
        "歌罗西书",
        "帖撒罗尼迦前书",
        "帖撒罗尼迦后书",
        "提摩太前书",
        "提摩太后书",
        "提多书",
        "腓利门书",
        "希伯来书",
        "雅各书",
        "彼得前书",
        "彼得后书",
        "约翰一书",
        "约翰二书",
        "约翰三书",
        "犹大书",
        "启示录",
    )
    chinese_book_title_re = "|".join(re.escape(title) for title in sorted(chinese_book_titles, key=len, reverse=True))
    cleaned = text or ""
    cleaned = re.sub(rf"(?:{chinese_book_title_re})生命读经第篇第页", "", cleaned)
    cleaned = cleaned.replace("生命读经第篇第页", "")
    cleaned = cleaned.replace("启示录", "")
    return cleaned


def main() -> int:
    if not SOURCE.exists():
        return fail(f"missing source: {SOURCE}")
    source_rows = list(csv.DictReader(SOURCE.open(encoding="utf-8-sig")))
    if len(source_rows) != 2205:
        return fail(f"expected source rows=2205, got {len(source_rows)}")
    if any(row.get("learning_review_decision") != "needs_manual_review" for row in source_rows):
        return fail("source contains non-needs_manual_review rows")

    rc = ensure_report()
    if rc:
        return rc

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if summary.get("database_write_performed") is not False:
        return fail("adjudication must be no-write")
    quality = summary.get("quality") or {}
    if quality.get("input_rows") != 2205 or quality.get("output_rows") != 2205:
        return fail(f"input/output row count mismatch: {quality}")
    if quality.get("front_end_import_ready_count") != 0:
        return fail("needs-review adjudication must not mark rows front-end import-ready")
    still = int(quality.get("still_needs_manual_review_count") or 0)
    if still >= 2205:
        return fail("still_needs_manual_review did not decrease")

    rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig")))
    if len(rows) != 2205:
        return fail(f"expected 2205 output rows, got {len(rows)}")
    split_total = sum(
        len(list(csv.DictReader(path.open(encoding="utf-8-sig"))))
        for path in (CORRECTED, LEARNING, REJECT, STILL)
    )
    if split_total != 2205:
        return fail(f"split CSV total mismatch: {split_total}")

    for row in rows:
        if row.get("database_write_performed") != "false":
            return fail(f"database write flag not false for {row.get('word')}")
        if row.get("front_end_import_ready") != "false":
            return fail(f"front-end import flag not false for {row.get('word')}")
        decision = row.get("adjudication_decision")
        reason = row.get("adjudication_reason")
        if decision in {"corrected_learning_candidate", "learning_only", "reject"} and not reason:
            return fail(f"missing adjudication reason for {row.get('word')}")
        if decision in {"corrected_learning_candidate", "learning_only"}:
            meaning = row.get("final_meaning_zh_simp") or ""
            if not meaning:
                return fail(f"missing final meaning for {row.get('word')}")
            if meaning not in clean_zh(row.get("evidence_zh_simp") or ""):
                return fail(f"final meaning not found in same Chinese evidence for {row.get('word')} -> {meaning}")
            if not row.get("evidence_en") or not row.get("source_volume") or not row.get("source_page"):
                return fail(f"missing evidence/source for {row.get('word')}")
        if decision == "still_needs_manual_review" and row.get("final_meaning_zh_simp"):
            return fail(f"still-needs row must not have final meaning: {row.get('word')}")

    print(
        "lifestudy needs-review adjudication v1 smoke PASS "
        f"rows=2205 adjudicated={quality.get('adjudicated_count')} still={still}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
