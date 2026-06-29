#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE_ROOT = ROOT / "Probe" / "ReadiumVisualReaderProbe"
REPORT = ROOT / "reports" / "readium_visual_reader_probe.json"
PACKAGE_CACHE = Path("/tmp/sentence-reader-readium-xcode-packages")
DERIVED_DATA = Path("/tmp/sentence-reader-readium-visual-derived")
PRODUCTS = DERIVED_DATA / "Build" / "Products" / "Debug-maccatalyst"
PRODUCT_BINARY = PRODUCTS / "ReadiumVisualReaderProbe"


def main() -> int:
    payload = {
        "schema_version": "sentence_reader.readium_visual_reader_probe.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe_root": str(PROBE_ROOT),
        "derived_data": str(DERIVED_DATA),
        "environment": {
            "xcode_select": run(["xcode-select", "-p"], timeout=10),
            "xcodebuild_version": run(["xcodebuild", "-version"], timeout=10),
        },
        "commands": {},
        "product": {},
        "decision": {},
    }

    PACKAGE_CACHE.mkdir(parents=True, exist_ok=True)
    payload["commands"]["xcodebuild_visual_reader"] = run(
        [
            "xcodebuild",
            "-scheme",
            "ReadiumVisualReaderProbe",
            "-destination",
            "generic/platform=macOS,variant=Mac Catalyst",
            "-clonedSourcePackagesDirPath",
            str(PACKAGE_CACHE),
            "-derivedDataPath",
            str(DERIVED_DATA),
            "build",
        ],
        cwd=PROBE_ROOT,
        timeout=300,
    )

    payload["product"] = inspect_product()
    payload["decision"] = decide(payload)
    write_report(payload)
    print_status(payload)
    return 0 if payload["decision"]["status"] in {"compiled_not_app_bundle", "app_bundle_built"} else 1


def inspect_product() -> dict:
    app_bundles = sorted(str(path) for path in PRODUCTS.glob("*.app")) if PRODUCTS.exists() else []
    return {
        "products_dir": str(PRODUCTS),
        "binary_exists": PRODUCT_BINARY.exists(),
        "binary_path": str(PRODUCT_BINARY),
        "app_bundles": app_bundles,
    }


def decide(payload: dict) -> dict:
    command = payload["commands"].get("xcodebuild_visual_reader", {})
    product = payload.get("product", {})
    if command.get("returncode") == 0 and product.get("app_bundles"):
        return {
            "status": "app_bundle_built",
            "reason": "Visual Readium reader built as an app bundle.",
            "next_step": "Launch the app bundle and verify EPUB rendering visually.",
        }
    if command.get("returncode") == 0 and product.get("binary_exists"):
        return {
            "status": "compiled_not_app_bundle",
            "reason": "SwiftUI/Readium visual reader code compiled, but SwiftPM produced a Mach-O executable rather than a launchable .app bundle.",
            "next_step": "Create a real Xcode application target for the visual navigator runtime probe.",
        }
    if command.get("timed_out"):
        return {
            "status": "timed_out",
            "reason": "Visual reader build timed out.",
            "next_step": "Rerun with warmed package cache or inspect DerivedData.",
        }
    return {
        "status": "failed",
        "reason": "Visual reader build failed.",
        "next_step": "Inspect stdout/stderr tail in readium_visual_reader_probe.json.",
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


def write_report(payload: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_status(payload: dict) -> None:
    decision = payload.get("decision", {})
    product = payload.get("product", {})
    print(f"readium visual reader probe: {decision.get('status', 'unknown')}")
    print(f"reason: {decision.get('reason', '')}")
    print(f"binary={product.get('binary_path', '') if product.get('binary_exists') else ''}")
    print(f"app_bundles={len(product.get('app_bundles', []))}")
    print(f"report={REPORT}")


if __name__ == "__main__":
    raise SystemExit(main())
