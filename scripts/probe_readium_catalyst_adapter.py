#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE_ROOT = ROOT / "Probe" / "ReadiumCatalystAdapterProbe"
REPORT = ROOT / "reports" / "readium_catalyst_adapter_probe.json"
LOCAL_READIUM = Path("/tmp/readium-swift-toolkit-shallow")
PACKAGE_CACHE = Path("/tmp/sentence-reader-readium-xcode-packages")
DERIVED_DATA = Path("/tmp/sentence-reader-readium-catalyst-derived")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Sentence Reader Readium Catalyst adapter probe.")
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("READIUM_CATALYST_ADAPTER_TIMEOUT", "240")))
    args = parser.parse_args()

    payload = {
        "schema_version": "sentence_reader.readium_catalyst_adapter_probe.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe_root": str(PROBE_ROOT),
        "local_readium_path": str(LOCAL_READIUM),
        "package_cache": str(PACKAGE_CACHE),
        "derived_data": str(DERIVED_DATA),
        "environment": {
            "xcode_select": run(["xcode-select", "-p"], timeout=10),
            "xcodebuild_version": run(["xcodebuild", "-version"], timeout=10),
        },
        "source": inspect_source(),
        "commands": {},
        "decision": {},
    }

    if not PROBE_ROOT.exists() or not LOCAL_READIUM.exists():
        payload["decision"] = {
            "status": "blocked",
            "reason": "Probe package or local Readium clone is missing.",
            "next_step": "Restore Probe/ReadiumCatalystAdapterProbe and /tmp/readium-swift-toolkit-shallow.",
        }
        write_report(payload)
        print_status(payload)
        return 1

    PACKAGE_CACHE.mkdir(parents=True, exist_ok=True)
    payload["commands"]["xcodebuild_catalyst_adapter"] = run(
        [
            "xcodebuild",
            "-scheme",
            "ReadiumCatalystAdapterProbe",
            "-destination",
            "generic/platform=macOS,variant=Mac Catalyst",
            "-clonedSourcePackagesDirPath",
            str(PACKAGE_CACHE),
            "-derivedDataPath",
            str(DERIVED_DATA),
            "build",
        ],
        cwd=PROBE_ROOT,
        timeout=args.timeout,
    )
    payload["decision"] = decide(payload)

    write_report(payload)
    print_status(payload)
    return 0 if payload["decision"]["status"] == "built" else 1


def inspect_source() -> dict:
    package = PROBE_ROOT / "Package.swift"
    source = PROBE_ROOT / "Sources" / "ReadiumCatalystAdapterProbe" / "ReadiumCatalystAdapterProbe.swift"
    source_text = read(source)
    return {
        "package_exists": package.exists(),
        "source_exists": source.exists(),
        "imports_readium_navigator": "import ReadiumNavigator" in source_text,
        "imports_readium_shared": "import ReadiumShared" in source_text,
        "references_epub_navigator": "EPUBNavigatorViewController" in source_text,
        "references_locator": "Locator(" in source_text,
        "references_decoration": "Decoration(" in source_text,
    }


def decide(payload: dict) -> dict:
    command = payload["commands"].get("xcodebuild_catalyst_adapter", {})
    source = payload.get("source", {})

    if command.get("returncode") == 0:
        return {
            "status": "built",
            "reason": "Readium Catalyst adapter probe compiled successfully.",
            "next_step": "Build a minimal app shell that opens a real EPUB and maps pointer events to Locator/Decoration.",
        }

    if command.get("timed_out"):
        return {
            "status": "timed_out",
            "reason": "Catalyst adapter build timed out.",
            "next_step": "Rerun with a longer timeout after package cache is warm.",
        }

    if not all(source.values()):
        return {
            "status": "blocked",
            "reason": "Probe source is missing required Readium contract references.",
            "next_step": "Restore Package.swift and ReadiumCatalystAdapterProbe.swift.",
        }

    return {
        "status": "failed",
        "reason": "Catalyst adapter build failed. See stderr/stdout tail in the report.",
        "next_step": "Fix the first Swift compiler error, then rerun this probe.",
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
        return {
            "args": args,
            "cwd": str(cwd) if cwd else None,
            "returncode": 124,
            "stdout": tail(stdout),
            "stderr": tail((stderr + f"\nTimed out after {timeout} seconds").strip()),
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


def write_report(payload: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_status(payload: dict) -> None:
    decision = payload.get("decision", {})
    print(f"readium catalyst adapter probe: {decision.get('status', 'unknown')}")
    print(f"reason: {decision.get('reason', '')}")
    print(f"report={REPORT}")


if __name__ == "__main__":
    raise SystemExit(main())
