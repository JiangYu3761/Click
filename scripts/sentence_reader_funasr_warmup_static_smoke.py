#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SWIFT = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"

MARKERS = [
    "funASRServerProcess",
    "funASRWarmupStarted",
    "funASRServerPort = 18081",
    "startFunASRWarmServiceIfAvailable",
    "stopFunASRWarmService",
    "applicationWillTerminate",
    "funasr_worker.py",
    "--server",
    "/health",
    "/transcribe",
    "transcribeWithFunASRServer",
    "FunASR 后台服务已就绪",
    "FunASRServer",
    "funasr_server.log",
]


def main() -> int:
    if not SWIFT.exists():
        print(f"funasr warmup static FAIL missing={SWIFT}")
        return 1
    text = SWIFT.read_text(encoding="utf-8")
    missing = [marker for marker in MARKERS if marker not in text]
    if missing:
        print(f"funasr warmup static FAIL missing_markers={missing}")
        return 1
    print("funasr warmup static PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
