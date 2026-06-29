#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SWIFT = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"

REQUIRED_MARKERS = [
    "CognitiveDashboardDraftRow",
    "CognitiveDashboardHistoryRow",
    "CognitiveDashboardWindowController",
    "NSTableViewDataSource",
    "statusFilterControl",
    '["全部", "可批准", "待审", "阻塞", "已入库"]',
    "approvalHistoryTextView",
    "showCognitiveDashboardWindow",
    "sentence_reader.cognitive_dashboard.v1",
    "打开仪表盘",
    "打开Markdown仪表盘",
    "打开所选草稿",
    "ready_to_approve",
    "needs_review",
    "blocked",
    "already_promoted",
]


def main() -> int:
    if not SWIFT.exists():
        print(f"native cognitive dashboard smoke FAIL missing={SWIFT}")
        return 1
    text = SWIFT.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_MARKERS if marker not in text]
    if missing:
        print(f"native cognitive dashboard smoke FAIL missing_markers={missing}")
        return 1
    print("native cognitive dashboard smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
