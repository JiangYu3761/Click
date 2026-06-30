#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SWIFT = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"

MARKERS = [
    "首启修复引导",
    "复制修复指引",
    "打开配置目录",
    "formatFirstRunGuide",
    "showFirstRunGuideIfNeeded",
    "didShowFirstRunGuide",
    "reportBool",
    "first_run_ready",
    "运行环境需要处理，已打开首启引导",
    "SENTENCE_READER_BOOTSTRAP_REPAIR=1",
    "SENTENCE_READER_BOOTSTRAP_INSTALL_DEPS=1",
    "缺 FunASR 不阻止阅读",
    "Postgres.app",
    "NSPasteboard.general",
]


def main() -> int:
    if not SWIFT.exists():
        print(f"first-run guide static FAIL missing={SWIFT}")
        return 1
    text = SWIFT.read_text(encoding="utf-8")
    missing = [marker for marker in MARKERS if marker not in text]
    if missing:
        print(f"first-run guide static FAIL missing_markers={missing}")
        return 1
    print("first-run guide static PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
