#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from sentence_reader_runtime_config import default_config_path, resolve_funasr_paths


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "sentence_reader.first_run_preflight_report.v1"
DEFAULT_APP_SUPPORT = Path(
    os.getenv(
        "SENTENCE_READER_APP_SUPPORT",
        str(Path.home() / "Library" / "Application Support" / "SentenceReader"),
    )
)
REPORTS = Path(os.getenv("SENTENCE_READER_REPORTS", str(DEFAULT_APP_SUPPORT / "Reports")))
DEFAULT_RUNTIME = ROOT if ROOT.name == "ReaderRuntime" else ROOT / "build" / "Sentence Reader.app" / "Contents" / "Resources" / "ReaderRuntime"
DEFAULT_PG_BIN = Path(os.getenv("POSTGRES_APP_BIN", "/Applications/Postgres.app/Contents/Versions/latest/bin"))
DEFAULT_DATABASE_URL = os.getenv("READER_DATABASE_URL") or os.getenv("DATABASE_URL") or "postgresql://localhost/jiangyu_os"
READER_API_URL = os.getenv("READER_API_HEALTH_URL", "http://127.0.0.1:18180/health")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_status(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "executable": os.access(path, os.X_OK),
        "realpath": str(path.resolve(strict=False)),
    }


def check_tcp(host: str, port: int, timeout: float = 0.8) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "host": host, "port": port}
    except OSError as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc)}


def http_health(url: str, timeout: float = 1.2) -> dict[str, Any]:
    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
        payload = json.loads(body)
        return {"ok": bool(payload.get("ok")), "url": url, "payload": payload}
    except Exception as exc:
        return {"ok": False, "url": url, "error": f"{exc.__class__.__name__}: {exc}"}


def postgres_status(pg_bin: Path) -> dict[str, Any]:
    binaries = {name: pg_bin / name for name in ("postgres", "pg_ctl", "initdb", "psql", "pg_dump")}
    binary_status = {name: file_status(path) for name, path in binaries.items()}
    tools_ready = all(binary_status[name]["exists"] for name in ("postgres", "pg_ctl", "initdb", "psql"))
    server = check_tcp("127.0.0.1", 5432)
    decision = "ready" if server["ok"] else "can_start_with_postgres_app" if tools_ready else "blocked_missing_postgresql"
    return {
        "strategy": "external_postgres_app_or_existing_server",
        "pg_bin": str(pg_bin),
        "tools_ready": tools_ready,
        "server_ready": server["ok"],
        "tcp_5432": server,
        "binaries": binary_status,
        "decision": decision,
        "repair_hint": "Install Postgres.app or set POSTGRES_APP_BIN to a bin directory containing postgres, pg_ctl, initdb, and psql.",
    }


def run_runtime_bootstrap(runtime: Path, app_support: Path, pg_bin: Path) -> dict[str, Any]:
    script = ROOT / "scripts" / "sentence_reader_runtime_bootstrap.py"
    if not script.exists():
        return {"ok": False, "skipped": True, "error": "runtime_bootstrap_script_missing"}
    output = REPORTS / "sentence_reader_runtime_bootstrap_report.json"
    markdown = REPORTS / "sentence_reader_runtime_bootstrap_report.md"
    command = [
        sys.executable,
        str(script),
        "--runtime",
        str(runtime),
        "--app-support",
        str(app_support),
        "--pg-bin",
        str(pg_bin),
        "--output",
        str(output),
        "--markdown",
        str(markdown),
    ]
    try:
        result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
    payload: dict[str, Any]
    if output.exists():
        try:
            payload = json.loads(output.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"raw_output": output.read_text(encoding="utf-8", errors="replace")}
    else:
        payload = {"raw_output": result.stdout}
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "report": str(output),
        "markdown": str(markdown),
        "payload": payload,
        "stdout": result.stdout[-2000:],
    }


def reader_api_status(runtime: Path) -> dict[str, Any]:
    startup_script = runtime / "scripts" / "run_reader_api.sh"
    if not startup_script.exists():
        startup_script = ROOT / "scripts" / "run_reader_api.sh"
    migration_script = runtime / "scripts" / "reader_pg_migrate.py"
    if not migration_script.exists():
        migration_script = ROOT / "scripts" / "reader_pg_migrate.py"
    return {
        "database_url": DEFAULT_DATABASE_URL,
        "startup_script": file_status(startup_script),
        "migration_script": file_status(migration_script),
        "health": http_health(READER_API_URL),
        "policy": {
            "create_database_requires_startup_script_or_manual_command": True,
            "destructive_migration_allowed": False,
        },
    }


def funasr_status(app_support: Path) -> dict[str, Any]:
    resolution = resolve_funasr_paths(app_support=app_support)
    decision = "ready" if resolution["ready"] else "apple_speech_fallback_until_configured"
    return {
        **resolution,
        "decision": decision,
        "fallback_provider": "apple_speech",
        "repair_hint": (
            "Run scripts/sentence_reader_runtime_config.py --write "
            "--funasr-python /path/to/python --funasr-worker /path/to/funasr_worker.py"
        ),
    }


def build_report(runtime: Path, app_support: Path, pg_bin: Path) -> dict[str, Any]:
    runtime = runtime.expanduser()
    app_support = app_support.expanduser()
    pg_bin = pg_bin.expanduser()
    postgres = postgres_status(pg_bin)
    funasr = funasr_status(app_support)
    bootstrap = run_runtime_bootstrap(runtime, app_support, pg_bin)
    reader_api = reader_api_status(runtime)
    first_run_ready = bool(
        (postgres["tools_ready"] or postgres["server_ready"])
        and (bootstrap.get("payload") or {}).get("python_ready", False)
    )
    return {
        "schema": SCHEMA,
        "generated_at": now_iso(),
        "project_root": str(ROOT),
        "runtime": str(runtime),
        "app_support": str(app_support),
        "runtime_config": {
            "path": str(default_config_path(app_support)),
            "exists": default_config_path(app_support).exists(),
            "schema": "sentence_reader.runtime_config.v1",
        },
        "postgres": postgres,
        "reader_api": reader_api,
        "runtime_bootstrap": bootstrap,
        "funasr": funasr,
        "first_run_ready": first_run_ready,
        "policy": {
            "auto_install_python_dependencies": False,
            "auto_install_postgresql": False,
            "destructive_database_actions": False,
            "funasr_missing_does_not_block_reading": True,
        },
        "next_actions": next_actions(postgres, funasr, bootstrap),
    }


def next_actions(postgres: dict[str, Any], funasr: dict[str, Any], bootstrap: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    if not (postgres["tools_ready"] or postgres["server_ready"]):
        actions.append("Install Postgres.app or set POSTGRES_APP_BIN before first launch.")
    payload = bootstrap.get("payload") if isinstance(bootstrap.get("payload"), dict) else {}
    if not payload.get("python_ready"):
        actions.append("Run runtime bootstrap with SENTENCE_READER_BOOTSTRAP_REPAIR=1, and install deps explicitly if needed.")
    if not funasr.get("ready"):
        actions.append("Configure FunASR paths or accept Apple Speech fallback for voice notes.")
    return actions or ["Open Sentence Reader; first-run dependencies are ready on this machine."]


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Sentence Reader First-Run Preflight",
        "",
        f"- Generated at: `{report.get('generated_at')}`",
        f"- First-run ready: `{report.get('first_run_ready')}`",
        f"- PostgreSQL decision: `{(report.get('postgres') or {}).get('decision')}`",
        f"- Runtime bootstrap ok: `{(report.get('runtime_bootstrap') or {}).get('ok')}`",
        f"- FunASR decision: `{(report.get('funasr') or {}).get('decision')}`",
        f"- Runtime config: `{(report.get('runtime_config') or {}).get('path')}`",
        "",
        "## Next Actions",
        "",
    ]
    lines.extend(f"- {action}" for action in (report.get("next_actions") or []))
    lines.extend(["", "## Policy", ""])
    for key, value in (report.get("policy") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a visible first-run preflight report for Sentence Reader.")
    parser.add_argument("--runtime", default=str(DEFAULT_RUNTIME))
    parser.add_argument("--app-support", default=str(DEFAULT_APP_SUPPORT))
    parser.add_argument("--pg-bin", default=str(DEFAULT_PG_BIN))
    parser.add_argument("--output", default=str(REPORTS / "sentence_reader_first_run_preflight_report.json"))
    parser.add_argument("--markdown", default=str(REPORTS / "sentence_reader_first_run_preflight_report.md"))
    parser.add_argument("--require-postgres-decision", action="store_true")
    parser.add_argument("--require-runtime-bootstrap", action="store_true")
    parser.add_argument("--require-first-run-ready", action="store_true")
    parser.add_argument("--require-funasr-configurable", action="store_true")
    parser.add_argument("--require-funasr-ready", action="store_true")
    args = parser.parse_args()

    report = build_report(
        runtime=Path(args.runtime),
        app_support=Path(args.app_support),
        pg_bin=Path(args.pg_bin),
    )
    failures: list[str] = []
    if args.require_postgres_decision and not (report["postgres"]["tools_ready"] or report["postgres"]["server_ready"]):
        failures.append("postgres_decision")
    if args.require_runtime_bootstrap and not report["runtime_bootstrap"]["ok"]:
        failures.append("runtime_bootstrap")
    if args.require_first_run_ready and not report["first_run_ready"]:
        failures.append("first_run_ready")
    if args.require_funasr_configurable and not report["funasr"]["configurable"]:
        failures.append("funasr_configurable")
    if args.require_funasr_ready and not report["funasr"]["ready"]:
        failures.append("funasr_ready")
    report["ok"] = not failures
    report["failures"] = failures

    output = Path(args.output).expanduser()
    markdown = Path(args.markdown).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown.write_text(render_markdown(report), encoding="utf-8")
    print(f"first_run_preflight_report={output}")
    print(f"first_run_preflight_markdown={markdown}")
    print(f"first_run_ready={report['first_run_ready']} failures={failures}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
