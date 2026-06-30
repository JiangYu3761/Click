#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCRIPT = ROOT / "scripts" / "sentence_reader_runtime_config.py"
PREFLIGHT_SCRIPT = ROOT / "scripts" / "sentence_reader_first_run_preflight.py"
RUNTIME = ROOT / "build" / "Sentence Reader.app" / "Contents" / "Resources" / "ReaderRuntime"


def run(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(command, cwd=ROOT, env=merged_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)


def main() -> int:
    if not CONFIG_SCRIPT.exists() or not PREFLIGHT_SCRIPT.exists():
        print("first-run preflight smoke FAIL missing scripts")
        return 1
    if not RUNTIME.exists():
        print(f"first-run preflight smoke FAIL missing runtime={RUNTIME}")
        return 1

    with tempfile.TemporaryDirectory(prefix="sentence-reader-first-run.") as tmp:
        tmp_path = Path(tmp)
        app_support = tmp_path / "AppSupport"
        fake_worker = tmp_path / "funasr_worker.py"
        fake_worker.write_text("print('fake funasr worker')\n", encoding="utf-8")
        fake_worker.chmod(fake_worker.stat().st_mode | stat.S_IXUSR)

        config_result = run(
            [
                sys.executable,
                str(CONFIG_SCRIPT),
                "--app-support",
                str(app_support),
                "--write",
                "--funasr-python",
                sys.executable,
                "--funasr-worker",
                str(fake_worker),
            ]
        )
        if config_result.returncode != 0:
            print(f"first-run preflight smoke FAIL config={config_result.stdout}")
            return 1

        report_path = tmp_path / "first_run.json"
        markdown_path = tmp_path / "first_run.md"
        preflight = run(
            [
                sys.executable,
                str(PREFLIGHT_SCRIPT),
                "--runtime",
                str(RUNTIME),
                "--app-support",
                str(app_support),
                "--output",
                str(report_path),
                "--markdown",
                str(markdown_path),
                "--require-postgres-decision",
                "--require-runtime-bootstrap",
                "--require-first-run-ready",
                "--require-funasr-configurable",
            ]
        )
        if preflight.returncode != 0:
            print(f"first-run preflight smoke FAIL preflight={preflight.stdout}")
            return 1
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("schema") != "sentence_reader.first_run_preflight_report.v1":
            print(f"first-run preflight smoke FAIL schema={report.get('schema')}")
            return 1
        if not report.get("runtime_config", {}).get("exists"):
            print("first-run preflight smoke FAIL runtime config not detected")
            return 1
        funasr = report.get("funasr") or {}
        if not funasr.get("ready") or funasr.get("python_source") != "runtime_config":
            print(f"first-run preflight smoke FAIL funasr={funasr}")
            return 1
        if "auto_install_postgresql" not in report.get("policy", {}):
            print("first-run preflight smoke FAIL policy missing")
            return 1
        if not markdown_path.exists() or "Sentence Reader First-Run Preflight" not in markdown_path.read_text(encoding="utf-8"):
            print("first-run preflight smoke FAIL markdown missing")
            return 1

    print("first-run preflight smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
