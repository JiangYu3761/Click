#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SWIFT = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"

MARKERS = [
    "RuntimeEnvironmentWindowController",
    "runtimeEnvironmentWindowController",
    "runtimeEnvironmentButton",
    "showRuntimeEnvironment",
    "运行环境",
    "重新检查",
    "语音识别",
    "SpeechTranscriptionProvider",
    "SentenceReader.speechTranscriptionProvider.v1",
    "打开预检报告",
    "runFirstRunPreflightForApp",
    "firstRunPreflightScriptCandidates",
    "sentence_reader_first_run_preflight.py",
    "--require-first-run-ready",
    "saveFunASRRuntimePaths",
    "restartFunASRWarmServiceAfterConfigurationChange",
    "startFunASRWarmServiceIfAvailable",
    "runtimeConfigURLForApp",
    "sentence_reader.runtime_config.v1",
    "SentenceReader.funASRPythonPath.v1",
    "SentenceReader.funASRWorkerPath.v1",
    "SENTENCE_READER_RUNTIME_CONFIG",
    "SENTENCE_READER_FUNASR_PYTHON",
    "SENTENCE_READER_FUNASR_WORKER",
    "sentence_reader_first_run_preflight_report.json",
    "sentence_reader_first_run_preflight_report.md",
]


def main() -> int:
    if not SWIFT.exists():
        print(f"runtime settings static FAIL missing={SWIFT}")
        return 1
    text = SWIFT.read_text(encoding="utf-8")
    missing = [marker for marker in MARKERS if marker not in text]
    if missing:
        print(f"runtime settings static FAIL missing_markers={missing}")
        return 1
    print("runtime settings static PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
