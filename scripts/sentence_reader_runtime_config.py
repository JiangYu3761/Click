#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "sentence_reader.runtime_config.v1"
DEFAULT_FUNASR_PYTHON = str(
    Path.home() / "Library" / "Application Support" / "SentenceReader" / "FunASR" / ".venv" / "bin" / "python"
)
DEFAULT_FUNASR_WORKER = str(
    Path.home() / "Library" / "Application Support" / "SentenceReader" / "FunASR" / "funasr_worker.py"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_app_support() -> Path:
    return Path(
        os.getenv(
            "SENTENCE_READER_APP_SUPPORT",
            str(Path.home() / "Library" / "Application Support" / "SentenceReader"),
        )
    )


def default_config_path(app_support: Path | None = None) -> Path:
    if os.getenv("SENTENCE_READER_RUNTIME_CONFIG"):
        return Path(os.environ["SENTENCE_READER_RUNTIME_CONFIG"]).expanduser()
    root = app_support or default_app_support()
    return root.expanduser() / "config" / "runtime_config.json"


def empty_config() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "funasr": {},
        "postgres": {},
    }


def load_runtime_config(path: Path | None = None, app_support: Path | None = None) -> dict[str, Any]:
    config_path = (path or default_config_path(app_support)).expanduser()
    if not config_path.exists():
        config = empty_config()
        config["_path"] = str(config_path)
        config["_exists"] = False
        return config
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        config = empty_config()
        config["_load_error"] = f"{exc.__class__.__name__}: {exc}"
    if not isinstance(config, dict):
        config = empty_config()
        config["_load_error"] = "config_root_not_object"
    config.setdefault("schema", SCHEMA)
    config.setdefault("funasr", {})
    config.setdefault("postgres", {})
    config["_path"] = str(config_path)
    config["_exists"] = True
    return config


def write_runtime_config(
    config: dict[str, Any],
    path: Path | None = None,
    app_support: Path | None = None,
) -> Path:
    config_path = (path or default_config_path(app_support)).expanduser()
    payload = {key: value for key, value in config.items() if not key.startswith("_")}
    payload["schema"] = SCHEMA
    payload.setdefault("created_at", now_iso())
    payload["updated_at"] = now_iso()
    payload.setdefault("funasr", {})
    payload.setdefault("postgres", {})
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return config_path


def _configured_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def resolve_funasr_paths(path: Path | None = None, app_support: Path | None = None) -> dict[str, Any]:
    config = load_runtime_config(path=path, app_support=app_support)
    funasr = config.get("funasr") if isinstance(config.get("funasr"), dict) else {}

    python_candidates: list[tuple[str, str | None]] = [
        ("env_SENTENCE_READER_FUNASR_PYTHON", _configured_string(os.getenv("SENTENCE_READER_FUNASR_PYTHON"))),
        ("runtime_config", _configured_string(funasr.get("python"))),
        ("legacy_default", DEFAULT_FUNASR_PYTHON),
    ]
    worker_candidates: list[tuple[str, str | None]] = [
        ("env_SENTENCE_READER_FUNASR_WORKER", _configured_string(os.getenv("SENTENCE_READER_FUNASR_WORKER"))),
        ("runtime_config", _configured_string(funasr.get("worker"))),
        ("legacy_default", DEFAULT_FUNASR_WORKER),
    ]

    python_source, python_value = next((source, value) for source, value in python_candidates if value)
    worker_source, worker_value = next((source, value) for source, value in worker_candidates if value)
    python_path = Path(python_value).expanduser()
    worker_path = Path(worker_value).expanduser()
    return {
        "schema": "sentence_reader.funasr_runtime_resolution.v1",
        "config_path": config.get("_path") or str(default_config_path(app_support)),
        "config_exists": bool(config.get("_exists")),
        "config_schema": config.get("schema"),
        "config_load_error": config.get("_load_error"),
        "python": str(python_path),
        "python_source": python_source,
        "python_exists": python_path.exists(),
        "python_executable": os.access(python_path, os.X_OK),
        "worker": str(worker_path),
        "worker_source": worker_source,
        "worker_exists": worker_path.exists(),
        "ready": bool(os.access(python_path, os.X_OK) and worker_path.exists()),
        "configurable": True,
        "env_keys": ["SENTENCE_READER_FUNASR_PYTHON", "SENTENCE_READER_FUNASR_WORKER"],
        "user_defaults_keys": [
            "SentenceReader.funASRPythonPath.v1",
            "SentenceReader.funASRWorkerPath.v1",
        ],
        "legacy_defaults": {
            "python": DEFAULT_FUNASR_PYTHON,
            "worker": DEFAULT_FUNASR_WORKER,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read or update Sentence Reader local runtime configuration.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--app-support", default=None)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--funasr-python", default=None)
    parser.add_argument("--funasr-worker", default=None)
    parser.add_argument("--print-funasr", action="store_true")
    args = parser.parse_args()

    app_support = Path(args.app_support).expanduser() if args.app_support else None
    config_path = Path(args.config).expanduser() if args.config else None
    config = load_runtime_config(path=config_path, app_support=app_support)

    if args.write:
        funasr = config.setdefault("funasr", {})
        if args.funasr_python:
            funasr["python"] = args.funasr_python
        if args.funasr_worker:
            funasr["worker"] = args.funasr_worker
        written = write_runtime_config(config, path=config_path, app_support=app_support)
        config = load_runtime_config(path=written)

    resolution = resolve_funasr_paths(path=config_path, app_support=app_support)
    payload = {
        "schema": SCHEMA,
        "config_path": config.get("_path") or str(default_config_path(app_support)),
        "config_exists": bool(config.get("_exists")),
        "config": {key: value for key, value in config.items() if not key.startswith("_")},
        "funasr_resolution": resolution,
    }

    if args.print_funasr:
        print(json.dumps(resolution, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
