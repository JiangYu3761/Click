#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_context_vocab_word_frequency.py"


def fail(message: str) -> int:
    print(f"lifestudy context vocab word frequency smoke FAIL: {message}")
    return 1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="lifestudy-word-frequency-smoke-") as tmp:
        output_dir = Path(tmp)
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--pages", "6", "--output-dir", str(output_dir)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            return fail(proc.stderr.strip() or proc.stdout.strip())
        report_path = output_dir / "Genesis-word-frequency.json"
        if not report_path.exists():
            return fail("word frequency JSON was not written")
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        if payload.get("schema") != "sentence_reader.lifestudy_word_frequency.v1":
            return fail(f"unexpected schema: {payload.get('schema')}")
        if payload.get("database_write_performed") is not False:
            return fail("word frequency report must not write database")
        quality = payload.get("quality") or {}
        if quality.get("raw_unique_word_count", 0) <= 0:
            return fail("raw word count should be positive")
        if quality.get("content_unique_word_count", 0) <= 0:
            return fail("content word count should be positive")
        items = {item.get("word"): item for item in payload.get("items") or []}
        if "god" not in items or items["god"].get("suggested_meaning_zh_simp") != "神":
            return fail("expected god => 神 in smoke report")
        if "life" not in items or items["life"].get("suggested_meaning_zh_simp") != "生命":
            return fail("expected life => 生命 in smoke report")
        if "lord" not in items or not str(items["lord"].get("meaning_source") or "").startswith("local_dictionary_fallback"):
            return fail("expected lord to use local dictionary fallback")
    print("lifestudy context vocab word frequency smoke PASS no_db_write=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
