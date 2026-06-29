#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DEFAULT_APP = ROOT / "build" / "Sentence Reader.app"
DEFAULT_RUNTIME = (
    ROOT
    if ROOT.name == "ReaderRuntime"
    else DEFAULT_APP / "Contents" / "Resources" / "ReaderRuntime"
)
DEFAULT_PG_BIN = Path(os.getenv("POSTGRES_APP_BIN", "/Applications/Postgres.app/Contents/Versions/latest/bin"))
DEFAULT_PGDATA = Path(
    os.getenv(
        "SENTENCE_READER_PGDATA",
        str(Path.home() / "Library" / "Application Support" / "SentenceReader" / "Postgres" / "data-18"),
    )
)
NATIVE_SWIFT = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path, limit: int = 12000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[:limit]


def file_status(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "is_symlink": path.is_symlink(),
        "executable": os.access(path, os.X_OK),
        "realpath": str(path.resolve(strict=False)),
    }


def symlink_chain(path: Path, max_depth: int = 8) -> list[dict[str, str]]:
    chain: list[dict[str, str]] = []
    current = path
    for _ in range(max_depth):
        if not current.is_symlink():
            break
        target = os.readlink(current)
        chain.append({"path": str(current), "target": target})
        target_path = Path(target)
        current = target_path if target_path.is_absolute() else current.parent / target_path
    return chain


def run_python_deps(python: Path) -> dict[str, Any]:
    if not python.exists():
        return {"ok": False, "skipped": True, "error": "python_missing"}
    try:
        result = subprocess.run(
            [str(python), "-c", "import fastapi, uvicorn, psycopg, httpx; print('deps ok')"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "output": result.stdout.strip(),
        }
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}


def tcp_status(host: str = "127.0.0.1", port: int = 5432, timeout: float = 0.8) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "host": host, "port": port}
    except OSError as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc)}


def postgres_status(pg_bin: Path) -> dict[str, Any]:
    binaries = {name: pg_bin / name for name in ("postgres", "pg_ctl", "initdb", "psql", "pg_dump")}
    return {
        "strategy": "external_postgres_app_or_POSTGRES_APP_BIN",
        "bundled": False,
        "default_bin": str(pg_bin),
        "binaries": {name: file_status(path) for name, path in binaries.items()},
        "path_lookup": {name: shutil.which(name) for name in ("postgres", "pg_ctl", "initdb", "psql", "pg_dump")},
        "pgdata": str(DEFAULT_PGDATA),
        "tcp_5432": tcp_status(),
    }


def python_status(runtime: Path) -> dict[str, Any]:
    python = runtime / ".venv-reader-api" / "bin" / "python"
    pyvenv = runtime / ".venv-reader-api" / "pyvenv.cfg"
    status = file_status(python)
    status["symlink_chain"] = symlink_chain(python)
    status["pyvenv_cfg"] = read_text(pyvenv)
    status["deps"] = run_python_deps(python)
    status["points_to_xcode"] = "/Applications/Xcode.app/" in status["realpath"] or "/Applications/Xcode.app/" in status["pyvenv_cfg"]
    status["points_outside_runtime"] = python.exists() and not str(Path(status["realpath"])).startswith(str(runtime))
    return status


def clean_mac_decision(runtime: Path, python: dict[str, Any], postgres: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    blockers: list[str] = []
    risks: list[str] = []
    if python.get("points_to_xcode"):
        blockers.append("runtime_python_points_to_xcode")
    if python.get("points_outside_runtime"):
        blockers.append("runtime_python_points_outside_ReaderRuntime")
    if not postgres.get("bundled"):
        blockers.append("postgres_not_bundled")
    if not (runtime / "scripts" / "run_reader_api.sh").exists():
        blockers.append("runtime_start_script_missing")
    if not (runtime / "migrations" / "reader" / "001_reader_schema.sql").exists():
        blockers.append("runtime_migration_missing")

    native_text = read_text(NATIVE_SWIFT)
    if "/Users/jiangyu/Documents/New project/.venv-funasr/bin/python" in native_text:
        risks.append("funasr_path_is_user_specific")

    clean_ready = not blockers
    return clean_ready, blockers, risks


def build_report(runtime: Path, app: Path, pg_bin: Path) -> dict[str, Any]:
    runtime = runtime.expanduser()
    app = app.expanduser()
    pg_bin = pg_bin.expanduser()
    required_files = {
        "runtime": file_status(runtime),
        "app_bundle": file_status(app),
        "run_script": file_status(runtime / "scripts" / "run_reader_api.sh"),
        "bootstrap_script": file_status(runtime / "scripts" / "sentence_reader_runtime_bootstrap.py"),
        "reader_api_app": file_status(runtime / "reader_api" / "app.py"),
        "migration": file_status(runtime / "migrations" / "reader" / "001_reader_schema.sql"),
        "requirements": file_status(runtime / "requirements-reader-api.txt"),
        "runtime_manifest": file_status(runtime / "runtime_manifest.json"),
    }
    python = python_status(runtime)
    postgres = postgres_status(pg_bin)
    manifest_payload: dict[str, Any] | None = None
    manifest_path = runtime / "runtime_manifest.json"
    if manifest_path.exists():
        try:
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest_payload = {"error": "invalid_json"}
    required_ready = all(item["exists"] for item in required_files.values() if item["path"] != str(manifest_path))
    postgres_binaries_ready = all(
        postgres["binaries"][name]["exists"] for name in ("postgres", "pg_ctl", "initdb", "psql")
    )
    current_machine_ready = bool(required_ready and python["exists"] and python["deps"]["ok"] and postgres_binaries_ready)
    clean_ready, blockers, risks = clean_mac_decision(runtime, python, postgres)
    return {
        "schema": "sentence_reader.runtime_portability_report.v1",
        "generated_at": now_iso(),
        "project_root": str(ROOT),
        "app_bundle": str(app),
        "runtime": str(runtime),
        "required_files": required_files,
        "runtime_manifest": manifest_payload,
        "python": python,
        "postgres": postgres,
        "current_machine_ready": current_machine_ready,
        "clean_mac_ready": clean_ready,
        "bootstrap_contract_ready": (runtime / "scripts" / "sentence_reader_runtime_bootstrap.py").exists(),
        "clean_mac_blockers": blockers,
        "feature_portability_risks": risks,
        "strategy": {
            "current_stage": "V2.0O runtime bootstrap contract",
            "base_app_current_machine": "packaged ReaderRuntime plus external Postgres.app",
            "clean_mac_target": "bootstrap-selected Python runtime plus explicit PostgreSQL preflight",
            "next_actions": [
                "use sentence_reader_runtime_bootstrap.py to select or create the Reader API Python runtime",
                "turn PostgreSQL dependency into a guided preflight instead of a hidden assumption",
                "move FunASR path configuration out of hard-coded user directories",
            ],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    blockers = report.get("clean_mac_blockers", [])
    risks = report.get("feature_portability_risks", [])
    lines = [
        "# Sentence Reader Runtime Portability",
        "",
        f"- Generated at: `{report.get('generated_at')}`",
        f"- Current machine ready: `{report.get('current_machine_ready')}`",
        f"- Clean Mac ready: `{report.get('clean_mac_ready')}`",
        f"- Runtime: `{report.get('runtime')}`",
        "",
        "## Clean Mac Blockers",
        "",
    ]
    if blockers:
        lines.extend([f"- `{blocker}`" for blocker in blockers])
    else:
        lines.append("- none")
    lines.extend(["", "## Feature Portability Risks", ""])
    if risks:
        lines.extend([f"- `{risk}`" for risk in risks])
    else:
        lines.append("- none")
    lines.extend(["", "## Strategy", ""])
    for action in report.get("strategy", {}).get("next_actions", []):
        lines.append(f"- {action}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check packaged Sentence Reader runtime portability.")
    parser.add_argument("--runtime", default=str(DEFAULT_RUNTIME))
    parser.add_argument("--app", default=str(DEFAULT_APP))
    parser.add_argument("--pg-bin", default=str(DEFAULT_PG_BIN))
    parser.add_argument("--output", default=str(REPORTS / "sentence_reader_runtime_portability_report.json"))
    parser.add_argument("--markdown", default=str(REPORTS / "sentence_reader_runtime_portability_report.md"))
    parser.add_argument("--require-current-machine-ready", action="store_true")
    parser.add_argument(
        "--require-clean-mac-decision",
        action="store_true",
        help="Require either clean_mac_ready=true or explicit clean_mac_blockers.",
    )
    args = parser.parse_args()

    report = build_report(Path(args.runtime), Path(args.app), Path(args.pg_bin))
    output = Path(args.output).expanduser()
    markdown = Path(args.markdown).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown.write_text(render_markdown(report), encoding="utf-8")

    failures: list[str] = []
    if args.require_current_machine_ready and not report["current_machine_ready"]:
        failures.append("current_machine_ready")
    if args.require_clean_mac_decision and not (report["clean_mac_ready"] or report["clean_mac_blockers"]):
        failures.append("clean_mac_decision")

    report["ok"] = not failures
    report["failures"] = failures
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"runtime_portability_report={output}")
    print(f"runtime_portability_markdown={markdown}")
    print(f"current_machine_ready={report['current_machine_ready']}")
    print(f"clean_mac_ready={report['clean_mac_ready']} blockers={report['clean_mac_blockers']}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
