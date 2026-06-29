#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "readium_xcode_build_probe.json"
LOCAL_READIUM = Path("/tmp/readium-swift-toolkit-shallow")
XCODE_PACKAGE_CACHE = Path("/tmp/sentence-reader-readium-xcode-packages")


def main() -> int:
    parser = argparse.ArgumentParser(description="Timeout-safe Readium/Xcode dependency probe.")
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("READIUM_XCODE_PROBE_TIMEOUT", "180")))
    parser.add_argument("--skip-xcode-resolve", action="store_true")
    args = parser.parse_args()

    payload: dict = {
        "schema_version": "sentence_reader.readium_xcode_build_probe.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "local_readium_path": str(LOCAL_READIUM),
        "xcode_package_cache": str(XCODE_PACKAGE_CACHE),
        "timeout_seconds": args.timeout,
        "environment": {
            "xcode_select": run(["xcode-select", "-p"], timeout=10),
            "xcodebuild_version": run(["xcodebuild", "-version"], timeout=10),
            "swift_version": run(["swift", "--version"], timeout=10),
        },
        "readium_source": inspect_source(),
        "commands": {},
        "decision": {},
    }

    if not LOCAL_READIUM.exists():
        payload["decision"] = {
            "status": "blocked",
            "reason": "Readium shallow clone is missing.",
            "next_step": "Clone readium/swift-toolkit into /tmp/readium-swift-toolkit-shallow and rerun.",
        }
        write_report(payload)
        print_status(payload)
        return 1

    payload["commands"]["swift_package_dump"] = run(
        ["swift", "package", "dump-package"],
        cwd=LOCAL_READIUM,
        timeout=30,
    )

    payload["commands"]["swift_package_resolve"] = run(
        ["swift", "package", "resolve"],
        cwd=LOCAL_READIUM,
        timeout=args.timeout,
    )

    playground = LOCAL_READIUM / "Playground" / "Playground.xcodeproj"
    if playground.exists() and not args.skip_xcode_resolve:
        XCODE_PACKAGE_CACHE.mkdir(parents=True, exist_ok=True)
        payload["commands"]["xcode_resolve_playground"] = run(
            [
                "xcodebuild",
                "-resolvePackageDependencies",
                "-project",
                str(playground),
                "-clonedSourcePackagesDirPath",
                str(XCODE_PACKAGE_CACHE),
            ],
            cwd=LOCAL_READIUM,
            timeout=args.timeout,
        )
    elif not playground.exists():
        payload["commands"]["xcode_resolve_playground"] = {
            "returncode": 127,
            "stdout": "",
            "stderr": f"Missing project: {playground}",
            "timed_out": False,
        }

    payload["post_state"] = inspect_post_state()
    payload["decision"] = decide(payload)

    write_report(payload)
    print_status(payload)
    return 0 if payload["decision"]["status"] in {"resolved", "resolved_swiftpm_xcode_skipped", "source_ready_dependency_blocked"} else 1


def inspect_source() -> dict:
    package = LOCAL_READIUM / "Package.swift"
    playground = LOCAL_READIUM / "Playground" / "Playground.xcodeproj"
    package_text = read(package)
    return {
        "exists": LOCAL_READIUM.exists(),
        "package_exists": package.exists(),
        "playground_project_exists": playground.exists(),
        "ios_only_manifest": "platforms: [.iOS" in package_text and ".macOS" not in package_text,
        "links_uikit": '.linkedFramework("UIKit")' in package_text,
        "package_size_bytes": package.stat().st_size if package.exists() else 0,
    }


def inspect_post_state() -> dict:
    spm_checkouts = LOCAL_READIUM / ".build" / "checkouts"
    spm_repositories = LOCAL_READIUM / ".build" / "repositories"
    package_cache_checkouts = XCODE_PACKAGE_CACHE / "checkouts"
    return {
        "swiftpm_checkouts": list_child_dirs(spm_checkouts),
        "swiftpm_repositories": list_child_dirs(spm_repositories),
        "xcode_package_checkouts": list_child_dirs(package_cache_checkouts),
        "package_resolved_files": [str(path) for path in LOCAL_READIUM.rglob("Package.resolved")],
    }


def decide(payload: dict) -> dict:
    env = payload.get("environment", {})
    commands = payload.get("commands", {})
    post_state = payload.get("post_state", {})

    if env.get("xcodebuild_version", {}).get("returncode") != 0:
        return {
            "status": "blocked",
            "reason": "Full Xcode is not active.",
            "next_step": "Select/activate Xcode, then rerun this probe.",
        }

    swift_resolve = commands.get("swift_package_resolve", {})
    xcode_resolve = commands.get("xcode_resolve_playground", {})

    if swift_resolve.get("returncode") == 0 and xcode_resolve.get("returncode") == 0:
        return {
            "status": "resolved",
            "reason": "SwiftPM and Xcode package dependencies resolved.",
            "next_step": "Build a tiny Catalyst wrapper around EPUBNavigatorViewController and open the Desktop EPUB fixture.",
        }

    if swift_resolve.get("returncode") == 0 and "xcode_resolve_playground" not in commands:
        return {
            "status": "resolved_swiftpm_xcode_skipped",
            "reason": "SwiftPM dependencies resolved; Xcode package resolve was intentionally skipped.",
            "next_step": "Run this probe without --skip-xcode-resolve when the full Xcode package graph must be checked.",
        }

    if swift_resolve.get("timed_out") or xcode_resolve.get("timed_out"):
        return {
            "status": "source_ready_dependency_blocked",
            "reason": "Readium source is available, but dependency resolution timed out.",
            "next_step": "Retry with a longer timeout or prewarm the SwiftPM/Xcode package cache before building the Catalyst probe.",
            "partial_repositories": post_state.get("swiftpm_repositories", []),
            "partial_checkouts": post_state.get("swiftpm_checkouts", []) + post_state.get("xcode_package_checkouts", []),
        }

    return {
        "status": "blocked",
        "reason": "Readium dependency resolution failed before a buildable app probe could start.",
        "next_step": "Inspect stderr in readium_xcode_build_probe.json, then decide whether to continue Readium or switch the adapter.",
    }


def run(args: list[str], cwd: Path | None = None, timeout: int = 10) -> dict:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return {
            "args": args,
            "cwd": str(cwd) if cwd else None,
            "returncode": completed.returncode,
            "stdout": tail(completed.stdout),
            "stderr": tail(completed.stderr),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = decode_timeout_stream(exc.stdout)
        stderr = decode_timeout_stream(exc.stderr)
        timeout_note = f"Timed out after {timeout} seconds"
        return {
            "args": args,
            "cwd": str(cwd) if cwd else None,
            "returncode": 124,
            "stdout": tail(stdout),
            "stderr": tail((stderr + "\n" + timeout_note).strip()),
            "timed_out": True,
        }


def decode_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def tail(text: str, limit: int = 12000) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def list_child_dirs(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted(item.name for item in path.iterdir() if item.is_dir())


def write_report(payload: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_status(payload: dict) -> None:
    decision = payload.get("decision", {})
    print(f"readium xcode build probe: {decision.get('status', 'unknown')}")
    print(f"reason: {decision.get('reason', '')}")
    print(f"report={REPORT}")


if __name__ == "__main__":
    raise SystemExit(main())
