#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from sentence_reader_runtime_config import resolve_funasr_paths


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
APP_SUPPORT = Path.home() / "Library" / "Application Support" / "SentenceReader"
READER_API_URL = "http://127.0.0.1:18180/health"
PG_BIN = Path(os.getenv("POSTGRES_APP_BIN", "/Applications/Postgres.app/Contents/Versions/latest/bin"))
DATABASE_URL = os.getenv("READER_DATABASE_URL") or os.getenv("DATABASE_URL") or "postgresql://localhost/jiangyu_os"
HERMES_COGNITIVE_OS = Path(
    os.getenv(
        "SENTENCE_READER_COGNITIVE_OS_DIR",
        "/Users/jiangyu/Documents/Codex/2026-06-18/hermes-ai-q1-3-codernext-geminifour/outputs/hermes_cognitive_os",
    )
)


def app_bundle_path() -> Path:
    if ROOT.name == "ReaderRuntime" and ROOT.parent.name == "Resources":
        return ROOT.parents[2]
    return ROOT / "build" / "Sentence Reader.app"


APP_BUNDLE = app_bundle_path()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_json(command: list[str], timeout: int = 20) -> dict[str, Any]:
    env = os.environ.copy()
    if PG_BIN.exists():
        env["PATH"] = f"{PG_BIN}:{env.get('PATH', '')}"
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"raw_output": result.stdout}
    return {"ok": result.returncode == 0, "returncode": result.returncode, "payload": payload}


def http_health(url: str, timeout: float = 1.5) -> dict[str, Any]:
    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
        payload = json.loads(body)
        return {"ok": bool(payload.get("ok")), "url": url, "payload": payload}
    except Exception as exc:
        return {"ok": False, "url": url, "error": f"{exc.__class__.__name__}: {exc}"}


def check_tcp(host: str, port: int, timeout: float = 1.0) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "host": host, "port": port}
    except OSError as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc)}


def path_status(path: Path, create_dir: bool = False) -> dict[str, Any]:
    if create_dir:
        path.mkdir(parents=True, exist_ok=True)
    writable = False
    if path.exists() and path.is_dir():
        probe = path / ".sentence-reader-write-test"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            writable = True
        except OSError:
            writable = False
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir(),
        "is_file": path.is_file(),
        "writable": writable,
    }


def directory_inventory(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "files": 0, "bytes": 0}
    files = [item for item in path.rglob("*") if item.is_file()]
    total = sum(item.stat().st_size for item in files)
    return {"path": str(path), "exists": True, "files": len(files), "bytes": total}


def query_sync_events() -> dict[str, Any]:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT status, count(*) AS count
                FROM reader.sync_events
                GROUP BY status
                ORDER BY status
                """
            ).fetchall()
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
    return {"ok": True, "by_status": {row["status"]: row["count"] for row in rows}}


def app_bundle_status() -> dict[str, Any]:
    executable = APP_BUNDLE / "Contents" / "MacOS" / "SentenceReader"
    runtime = APP_BUNDLE / "Contents" / "Resources" / "ReaderRuntime"
    runtime_python = runtime / ".venv-reader-api" / "bin" / "python"
    deps = {"ok": False, "skipped": True}
    if runtime_python.exists():
        try:
            result = subprocess.run(
                [str(runtime_python), "-c", "import fastapi, uvicorn, psycopg, httpx; print('ok')"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=10,
            )
            deps = {"ok": result.returncode == 0, "returncode": result.returncode, "output": result.stdout.strip()}
        except Exception as exc:
            deps = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
    return {
        "bundle": str(APP_BUNDLE),
        "exists": APP_BUNDLE.exists(),
        "executable": str(executable),
        "executable_exists": executable.exists(),
        "runtime": str(runtime),
        "runtime_exists": runtime.exists(),
        "runtime_python": str(runtime_python),
        "runtime_python_exists": runtime_python.exists(),
        "runtime_python_deps": deps,
        "runtime_run_script_exists": (runtime / "scripts" / "run_reader_api.sh").exists(),
    }


def runtime_portability_status() -> dict[str, Any]:
    script = ROOT / "scripts" / "sentence_reader_runtime_portability.py"
    if not script.exists():
        return {"ok": False, "skipped": True, "error": "runtime_portability_script_missing"}
    output = REPORTS / "sentence_reader_runtime_portability_report.json"
    markdown = REPORTS / "sentence_reader_runtime_portability_report.md"
    return run_json(
        [
            sys.executable,
            str(script),
            "--output",
            str(output),
            "--markdown",
            str(markdown),
            "--require-current-machine-ready",
            "--require-clean-mac-decision",
        ],
        timeout=30,
    )


def runtime_bootstrap_status() -> dict[str, Any]:
    script = ROOT / "scripts" / "sentence_reader_runtime_bootstrap.py"
    if not script.exists():
        return {"ok": False, "skipped": True, "error": "runtime_bootstrap_script_missing"}
    output = REPORTS / "sentence_reader_runtime_bootstrap_report.json"
    markdown = REPORTS / "sentence_reader_runtime_bootstrap_report.md"
    return run_json(
        [
            sys.executable,
            str(script),
            "--output",
            str(output),
            "--markdown",
            str(markdown),
            "--require-startup-ready",
            "--require-postgres-decision",
        ],
        timeout=30,
    )


def first_run_preflight_status() -> dict[str, Any]:
    script = ROOT / "scripts" / "sentence_reader_first_run_preflight.py"
    if not script.exists():
        return {"ok": False, "skipped": True, "error": "first_run_preflight_script_missing"}
    output = REPORTS / "sentence_reader_first_run_preflight_report.json"
    markdown = REPORTS / "sentence_reader_first_run_preflight_report.md"
    return run_json(
        [
            sys.executable,
            str(script),
            "--output",
            str(output),
            "--markdown",
            str(markdown),
            "--require-postgres-decision",
            "--require-runtime-bootstrap",
            "--require-first-run-ready",
            "--require-funasr-configurable",
        ],
        timeout=45,
    )


def build_report() -> dict[str, Any]:
    app_support = {
        "root": path_status(APP_SUPPORT, create_dir=True),
        "books": directory_inventory(APP_SUPPORT / "Books"),
        "audio_notes": directory_inventory(APP_SUPPORT / "AudioNotes"),
        "exports": directory_inventory(APP_SUPPORT / "Exports"),
        "hermes_sync": directory_inventory(APP_SUPPORT / "HermesSync"),
        "backups": directory_inventory(APP_SUPPORT / "Backups"),
    }
    return {
        "schema": "sentence_reader.product_diagnostics.v1",
        "generated_at": now_iso(),
        "project_root": str(ROOT),
        "system": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.executable,
            "python_version": sys.version,
        },
        "binaries": {
            "psql": shutil.which("psql"),
            "pg_dump": shutil.which("pg_dump"),
            "postgres_app_bin": str(PG_BIN),
            "xcodebuild": shutil.which("xcodebuild"),
            "swiftc": shutil.which("swiftc"),
        },
        "postgres": run_json([sys.executable, str(ROOT / "scripts" / "reader_pg_status.py"), "--json"], timeout=20),
        "reader_api": http_health(READER_API_URL),
        "reader_api_tcp": check_tcp("127.0.0.1", 18180),
        "app_bundle": app_bundle_status(),
        "runtime_portability": runtime_portability_status(),
        "runtime_bootstrap": runtime_bootstrap_status(),
        "first_run_preflight": first_run_preflight_status(),
        "app_support": app_support,
        "funasr": resolve_funasr_paths(app_support=APP_SUPPORT),
        "hermes_cognitive_os": {
            "root": directory_inventory(HERMES_COGNITIVE_OS),
            "sentence_reader_incoming": directory_inventory(HERMES_COGNITIVE_OS / "incoming" / "sentence_reader"),
            "sentence_reader_intake_drafts": directory_inventory(HERMES_COGNITIVE_OS / "incoming" / "sentence_reader_drafts"),
            "sentence_reader_review_queue": directory_inventory(HERMES_COGNITIVE_OS / "incoming" / "sentence_reader_drafts" / "review_queue"),
            "sentence_reader_intake_promotions": directory_inventory(HERMES_COGNITIVE_OS / "incoming" / "sentence_reader_drafts" / "promotions"),
            "sentence_reader_operator_runs": directory_inventory(HERMES_COGNITIVE_OS / "incoming" / "sentence_reader_drafts" / "operator_runs"),
            "formal_intakes": directory_inventory(HERMES_COGNITIVE_OS / "intakes"),
        },
        "sync_events": query_sync_events(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a product diagnostics report for Sentence Reader.")
    parser.add_argument("--output", default=str(REPORTS / "sentence_reader_product_diagnostics_report.json"))
    parser.add_argument("--require-api", action="store_true")
    parser.add_argument("--require-postgres", action="store_true")
    parser.add_argument("--require-package", action="store_true")
    args = parser.parse_args()

    report = build_report()
    failures: list[str] = []
    if args.require_api and not report["reader_api"]["ok"]:
        failures.append("reader_api")
    if args.require_postgres and not report["postgres"]["ok"]:
        failures.append("postgres")
    if args.require_package and not (
        report["app_bundle"]["exists"]
        and report["app_bundle"]["executable_exists"]
        and report["app_bundle"]["runtime_run_script_exists"]
        and report["app_bundle"]["runtime_python_exists"]
        and report["app_bundle"]["runtime_python_deps"]["ok"]
        and report["runtime_portability"]["ok"]
        and report["runtime_bootstrap"]["ok"]
        and report["first_run_preflight"]["ok"]
    ):
        failures.append("app_package")
    if not report["app_support"]["root"]["writable"]:
        failures.append("app_support_writable")

    report["ok"] = not failures
    report["failures"] = failures

    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"diagnostics_report={output}")
    print(f"ok={report['ok']} failures={failures}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
