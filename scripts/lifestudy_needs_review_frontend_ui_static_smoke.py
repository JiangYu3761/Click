#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "reader_api" / "app.py"
SWIFT = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"

REQUIRED = {
    API: [
        "item.meaning_source === 'lifestudy_domain_glossary'",
        "生命读经词库",
        "metadata.source_page",
        "metadata.volume",
        "lookupCopy",
        "reviewable = item.reviewable !== false && !!item.id",
    ],
    SWIFT: [
        "let sourceTitle = Self.lookupText(metadata?[\"source_title\"])",
        "let sourceVolume = Self.lookupText(metadata?[\"volume\"])",
        "let sourcePage = Self.lookupText(metadata?[\"source_page\"])",
        "批次：",
        "出处：",
        "case \"lifestudy_domain_glossary\": return \"生命读经词库\"",
    ],
}


def main() -> int:
    missing: dict[str, list[str]] = {}
    for path, markers in REQUIRED.items():
        text = path.read_text(encoding="utf-8")
        miss = [marker for marker in markers if marker not in text]
        if miss:
            missing[str(path)] = miss
    if missing:
        print(f"lifestudy needs-review frontend ui static smoke FAIL {missing}")
        return 1
    print("lifestudy needs-review frontend ui static smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
