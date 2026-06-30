#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_context_vocab_phrase_uncommon_pack.py"
REPORT = ROOT / "reports" / "lifestudy_vocab_review" / "Genesis-phrase-uncommon-pack.json"


def fail(message: str) -> int:
    print(f"lifestudy context vocab phrase uncommon pack smoke FAIL: {message}")
    return 1


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        return fail(proc.stderr.strip() or proc.stdout.strip())
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.lifestudy_phrase_uncommon_pack.v1":
        return fail(f"unexpected schema: {payload.get('schema')}")
    if payload.get("database_write_performed") is not False:
        return fail("phrase/uncommon pack must not write database")
    quality = payload.get("quality") or {}
    if quality.get("active_high_confidence_phrase_count") != 25:
        return fail(f"expected 25 active phrases, got {quality.get('active_high_confidence_phrase_count')}")
    if quality.get("uncommon_context_word_count") != 34:
        return fail(f"expected 34 uncommon words, got {quality.get('uncommon_context_word_count')}")
    if quality.get("high_frequency_phrase_candidate_count", 0) <= 0:
        return fail("expected high-frequency phrase candidates")
    rows = payload.get("items") or []
    review_phrases = [item for item in rows if item.get("group") == "high_frequency_phrase_candidates"]
    blank_review_phrases = [item.get("term") for item in review_phrases if not item.get("suggested_meaning_zh_simp")]
    if blank_review_phrases:
        return fail(f"review phrases missing meanings: {blank_review_phrases[:5]}")
    mechanical_review_phrases = [
        item.get("term")
        for item in review_phrases
        if "/" in str(item.get("suggested_meaning_zh_simp") or "")
    ]
    if mechanical_review_phrases:
        return fail(f"review phrases still look mechanically joined: {mechanical_review_phrases[:5]}")
    bad_meanings = {"神的亚伯拉罕", "神的雅各", "神的父"}
    bad_rows = [
        f"{item.get('term')}={item.get('suggested_meaning_zh_simp')}"
        for item in review_phrases
        if item.get("suggested_meaning_zh_simp") in bad_meanings
    ]
    if bad_rows:
        return fail(f"known bad meanings returned: {bad_rows[:5]}")
    generic_god_rows = [
        item.get("term")
        for item in review_phrases
        if item.get("suggested_meaning_zh_simp") == "神"
    ]
    if generic_god_rows:
        return fail(f"review phrases collapsed to generic god meaning: {generic_god_rows[:5]}")
    items = {item.get("term"): item for item in rows}
    for term in ["tree of life", "economy", "dispensing"]:
        if term not in items:
            return fail(f"missing expected term: {term}")
    expected_meanings = {
        "god abraham": "亚伯拉罕的神",
        "god father": "父神",
        "created man": "创造人",
        "christ seed": "基督作后裔",
        "god desire": "神的心愿",
        "god expression": "神的彰显",
        "god goal": "神的目标",
        "god heart": "神的心意",
        "life tree": "生命树",
    }
    for term, expected_meaning in expected_meanings.items():
        actual = items.get(term, {}).get("suggested_meaning_zh_simp")
        if actual != expected_meaning:
            return fail(f"unexpected meaning for {term}: {actual!r}")
    print(
        "lifestudy context vocab phrase uncommon pack smoke PASS "
        f"total={quality.get('total_item_count')} no_db_write=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
