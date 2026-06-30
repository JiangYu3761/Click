#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sentence_reader_runtime_bootstrap.py"
RUNTIME = ROOT / "build" / "Click.app" / "Contents" / "Resources" / "ReaderRuntime"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)


def main() -> int:
    if not SCRIPT.exists():
        print(f"runtime bootstrap smoke FAIL missing={SCRIPT}")
        return 1
    if not RUNTIME.exists():
        print(f"runtime bootstrap smoke FAIL missing_runtime={RUNTIME}")
        return 1

    with tempfile.TemporaryDirectory(prefix="sentence-reader-bootstrap-smoke.") as tmp:
        tmp_path = Path(tmp)
        report_path = tmp_path / "bootstrap.json"
        markdown_path = tmp_path / "bootstrap.md"
        result = run(
            [
                sys.executable,
                str(SCRIPT),
                "--runtime",
                str(RUNTIME),
                "--app-support",
                str(tmp_path / "AppSupport"),
                "--repair-python",
                "--require-startup-ready",
                "--require-postgres-decision",
                "--output",
                str(report_path),
                "--markdown",
                str(markdown_path),
            ]
        )
        if result.returncode != 0:
            print(f"runtime bootstrap smoke FAIL preflight output={result.stdout}")
            return 1
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("schema") != "sentence_reader.runtime_bootstrap_report.v1":
            print(f"runtime bootstrap smoke FAIL schema={report.get('schema')}")
            return 1
        if not report.get("startup_ready"):
            print(f"runtime bootstrap smoke FAIL not_ready={report.get('blocked_reasons')}")
            return 1
        if not (tmp_path / "AppSupport" / "Runtime" / ".venv-reader-api" / "bin" / "python").exists():
            print("runtime bootstrap smoke FAIL user venv was not created")
            return 1
        selected = report.get("selected_python") or {}
        if not selected.get("path"):
            print("runtime bootstrap smoke FAIL no selected python")
            return 1

        print_python = run(
            [
                sys.executable,
                str(SCRIPT),
                "--runtime",
                str(RUNTIME),
                "--app-support",
                str(tmp_path / "AppSupport"),
                "--print-python",
            ]
        )
        if print_python.returncode != 0 or not print_python.stdout.strip():
            print(f"runtime bootstrap smoke FAIL print_python={print_python.stdout}")
            return 1

    print("runtime bootstrap smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
