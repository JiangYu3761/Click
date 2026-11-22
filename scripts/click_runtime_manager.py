#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_CONTRACT = "click.reader_runtime.v1"
DEFAULT_API_REVISION = 3
DEFAULT_PORT = 18180


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_runtime() -> Path:
    root = Path(__file__).resolve().parents[1]
    packaged = root if root.name == "ReaderRuntime" else root / "build" / "Click.app" / "Contents" / "Resources" / "ReaderRuntime"
    return packaged if packaged.exists() else root


def default_state_dir() -> Path:
    app_support = Path(
        os.getenv(
            "SENTENCE_READER_APP_SUPPORT",
            str(Path.home() / "Library" / "Application Support" / "SentenceReader"),
        )
    )
    return app_support / "Runtime" / "SharedReaderAPI"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@contextmanager
def locked(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def process_alive(pid: Any) -> bool:
    try:
        resolved = int(pid)
    except (TypeError, ValueError):
        return False
    if resolved <= 1:
        return False
    try:
        os.kill(resolved, 0)
    except OSError:
        return False
    return True


def health(base_url: str, *, timeout: float = 0.8) -> dict[str, Any]:
    try:
        request = Request(f"{base_url.rstrip('/')}/health", headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {"reachable": True, "payload": payload if isinstance(payload, dict) else {}}
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"reachable": False, "error": f"{exc.__class__.__name__}: {exc}"}


def compatibility(
    health_result: dict[str, Any],
    *,
    expected_contract: str,
    minimum_revision: int,
    required_capabilities: list[str],
) -> dict[str, Any]:
    payload = health_result.get("payload") if isinstance(health_result.get("payload"), dict) else {}
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    capabilities = runtime.get("capabilities") if isinstance(runtime.get("capabilities"), list) else []
    missing = [item for item in required_capabilities if item not in capabilities]
    try:
        revision = int(runtime.get("api_revision") or 0)
    except (TypeError, ValueError):
        revision = 0
    compatible = bool(
        health_result.get("reachable")
        and payload.get("ok") is True
        and runtime.get("contract") == expected_contract
        and revision >= minimum_revision
        and not missing
    )
    return {
        "compatible": compatible,
        "contract": runtime.get("contract"),
        "api_revision": revision,
        "capabilities": capabilities,
        "missing_capabilities": missing,
        "process_id": runtime.get("process_id"),
    }


def manager_status(args: argparse.Namespace) -> dict[str, Any]:
    state_dir = Path(args.state_dir).expanduser()
    state = read_json(state_dir / "reader_api.json")
    base_url = f"http://127.0.0.1:{args.port}"
    health_result = health(base_url)
    compatible = compatibility(
        health_result,
        expected_contract=args.expected_contract,
        minimum_revision=args.minimum_revision,
        required_capabilities=args.capability,
    )
    return {
        "schema": "click.runtime_manager.status.v1",
        "ok": compatible["compatible"],
        "base_url": base_url,
        "state_dir": str(state_dir),
        "state": state,
        "health": health_result,
        "compatibility": compatible,
    }


def ensure_runtime(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    runtime = Path(args.runtime).expanduser().resolve()
    state_dir = Path(args.state_dir).expanduser()
    state_path = state_dir / "reader_api.json"
    log_path = state_dir / "reader_api.log"
    lock_path = state_dir / "reader_api.lock"
    base_url = f"http://127.0.0.1:{args.port}"
    with locked(lock_path):
        existing_health = health(base_url)
        existing_compatibility = compatibility(
            existing_health,
            expected_contract=args.expected_contract,
            minimum_revision=args.minimum_revision,
            required_capabilities=args.capability,
        )
        if existing_compatibility["compatible"]:
            state = read_json(state_path)
            result = {
                "schema": "click.runtime_manager.ensure.v1",
                "ok": True,
                "decision": "reused_compatible_runtime",
                "base_url": base_url,
                "runtime": str(runtime),
                "process_id": existing_compatibility.get("process_id"),
                "managed": bool(state.get("managed") and state.get("process_id") == existing_compatibility.get("process_id")),
                "compatibility": existing_compatibility,
            }
            return 0, result
        if existing_health.get("reachable"):
            return 3, {
                "schema": "click.runtime_manager.ensure.v1",
                "ok": False,
                "decision": "blocked_incompatible_service",
                "base_url": base_url,
                "compatibility": existing_compatibility,
                "error": "Port is occupied by a reachable but incompatible service; it was not terminated.",
            }

        previous = read_json(state_path)
        if previous and not process_alive(previous.get("process_id")):
            previous["stale_detected_at"] = now_iso()
            previous["managed"] = False
            write_json_atomic(state_path, previous)

        script = runtime / "scripts" / "run_reader_api.sh"
        if not script.is_file() or not os.access(script, os.X_OK):
            return 4, {
                "schema": "click.runtime_manager.ensure.v1",
                "ok": False,
                "decision": "blocked_missing_runtime_script",
                "runtime": str(runtime),
                "script": str(script),
            }
        state_dir.mkdir(parents=True, exist_ok=True)
        environment = dict(os.environ)
        environment["READER_API_HOST"] = args.host
        environment["READER_API_PORT"] = str(args.port)
        environment["SENTENCE_READER_APP_SUPPORT"] = str(Path(args.app_support).expanduser())
        environment["CLICK_MOBILE_REQUIRE_APPROVAL"] = "1"
        with log_path.open("a", encoding="utf-8") as log:
            process = subprocess.Popen(
                [str(script)],
                cwd=runtime,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        state = {
            "schema": "click.runtime_manager.state.v1",
            "managed": True,
            "process_id": process.pid,
            "runtime": str(runtime),
            "script": str(script),
            "base_url": base_url,
            "host": args.host,
            "port": args.port,
            "started_at": now_iso(),
            "log": str(log_path),
        }
        write_json_atomic(state_path, state)

        deadline = time.monotonic() + max(1.0, float(args.timeout))
        last_health: dict[str, Any] = {"reachable": False, "error": "not_checked"}
        last_compatibility: dict[str, Any] = {"compatible": False}
        while time.monotonic() < deadline:
            if process.poll() is not None:
                state.update({"managed": False, "exited_at": now_iso(), "exit_code": process.returncode})
                write_json_atomic(state_path, state)
                return 5, {
                    "schema": "click.runtime_manager.ensure.v1",
                    "ok": False,
                    "decision": "runtime_exited_before_ready",
                    "state": state,
                    "log": str(log_path),
                }
            last_health = health(base_url)
            last_compatibility = compatibility(
                last_health,
                expected_contract=args.expected_contract,
                minimum_revision=args.minimum_revision,
                required_capabilities=args.capability,
            )
            if last_compatibility["compatible"]:
                state["ready_at"] = now_iso()
                state["runtime_process_id"] = last_compatibility.get("process_id")
                state["compatibility"] = last_compatibility
                write_json_atomic(state_path, state)
                return 0, {
                    "schema": "click.runtime_manager.ensure.v1",
                    "ok": True,
                    "decision": "started_compatible_runtime",
                    "base_url": base_url,
                    "runtime": str(runtime),
                    "process_id": last_compatibility.get("process_id"),
                    "managed": True,
                    "compatibility": last_compatibility,
                }
            time.sleep(0.2)
        return 6, {
            "schema": "click.runtime_manager.ensure.v1",
            "ok": False,
            "decision": "runtime_health_timeout",
            "base_url": base_url,
            "health": last_health,
            "compatibility": last_compatibility,
            "log": str(log_path),
        }


def stop_owned_runtime(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    state_dir = Path(args.state_dir).expanduser()
    state_path = state_dir / "reader_api.json"
    lock_path = state_dir / "reader_api.lock"
    with locked(lock_path):
        state = read_json(state_path)
        pid = state.get("process_id")
        if not state.get("managed") or not process_alive(pid):
            return 0, {
                "schema": "click.runtime_manager.stop.v1",
                "ok": True,
                "decision": "no_owned_runtime_running",
            }
        os.kill(int(pid), signal.SIGTERM)
        deadline = time.monotonic() + max(1.0, float(args.timeout))
        while time.monotonic() < deadline and process_alive(pid):
            time.sleep(0.1)
        if process_alive(pid):
            return 7, {
                "schema": "click.runtime_manager.stop.v1",
                "ok": False,
                "decision": "owned_runtime_did_not_stop",
                "process_id": pid,
            }
        state["managed"] = False
        state["stopped_at"] = now_iso()
        write_json_atomic(state_path, state)
        return 0, {
            "schema": "click.runtime_manager.stop.v1",
            "ok": True,
            "decision": "stopped_owned_runtime",
            "process_id": pid,
        }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Manage the one shared Click Reader API runtime.")
    root.add_argument("command", choices=("ensure", "status", "stop"))
    root.add_argument("--runtime", default=str(default_runtime()))
    root.add_argument("--app-support", default=str(default_state_dir().parents[1]))
    root.add_argument("--state-dir", default=str(default_state_dir()))
    root.add_argument("--host", default="0.0.0.0")
    root.add_argument("--port", type=int, default=DEFAULT_PORT)
    root.add_argument("--timeout", type=float, default=12.0)
    root.add_argument("--expected-contract", default=DEFAULT_CONTRACT)
    root.add_argument("--minimum-revision", type=int, default=DEFAULT_API_REVISION)
    root.add_argument("--capability", action="append", default=[])
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "ensure":
        code, result = ensure_runtime(args)
    elif args.command == "stop":
        code, result = stop_owned_runtime(args)
    else:
        result = manager_status(args)
        code = 0 if result["ok"] else 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
