#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "readium_dependency_probe.json"
LOCAL_READIUM = Path("/tmp/readium-swift-toolkit-shallow")


def main() -> int:
    xcode_select = run(["xcode-select", "-p"], timeout=5)
    xcodebuild = run(["xcodebuild", "-version"], timeout=5)

    readium = inspect_readium(LOCAL_READIUM)
    decision = decide(xcodebuild, readium)

    payload = {
        "schema_version": "sentence_reader.readium_probe.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "local_readium_path": str(LOCAL_READIUM),
        "environment": {
            "xcode_select": xcode_select,
            "xcodebuild": xcodebuild,
        },
        "readium": readium,
        "decision": decision,
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"readium status: {decision['status']}")
    print(f"report={REPORT}")
    return 0 if decision["status"] in {"continue_with_caveat", "ready_for_xcode_probe"} else 1


def inspect_readium(path: Path) -> dict:
    if not path.exists():
        return {
            "available": False,
            "reason": "local shallow clone missing",
        }

    package = path / "Package.swift"
    sources = path / "Sources"
    docs = path / "docs"
    package_text = read(package)

    return {
        "available": True,
        "package_exists": package.exists(),
        "platforms": parse_platforms(path),
        "products": parse_products(path),
        "package_markers": {
            "ios_only_manifest": "platforms: [.iOS" in package_text and ".macOS" not in package_text,
            "links_uikit": '.linkedFramework("UIKit")' in package_text,
        },
        "source_markers": {
            "uikit_imports": count_rg("import UIKit", sources),
            "appkit_imports": count_rg("import AppKit", sources),
            "decorable_navigator": rg_exists("protocol DecorableNavigator", sources),
            "decoration_api": rg_exists("struct Decoration", sources),
            "pointer_events": rg_exists("struct PointerEvent", sources),
            "secondary_mouse_button": rg_exists("static let secondary", sources),
        },
        "doc_markers": {
            "swiftui_guide_exists": (docs / "Guides/Navigator/SwiftUI.md").exists(),
            "highlights_guide_exists": (docs / "Guides/Navigator/Highlights.md").exists(),
            "swiftui_uses_uiviewcontrollerrepresentable": "UIViewControllerRepresentable" in read(docs / "Guides/Navigator/SwiftUI.md"),
            "highlight_uses_decoration_api": "Decoration API" in read(docs / "Guides/Navigator/Highlights.md"),
        },
    }


def parse_platforms(path: Path) -> list[dict]:
    result = run(["swift", "package", "dump-package"], cwd=path, timeout=20)
    if result["returncode"] != 0:
        return []
    try:
        data = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return []
    return data.get("platforms", [])


def parse_products(path: Path) -> list[str]:
    result = run(["swift", "package", "dump-package"], cwd=path, timeout=20)
    if result["returncode"] != 0:
        return []
    try:
        data = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return []
    return [item.get("name", "") for item in data.get("products", [])]


def decide(xcodebuild: dict, readium: dict) -> dict:
    if not readium.get("available"):
        return {
            "status": "blocked",
            "reason": "Readium local clone is missing; rerun shallow clone or SwiftPM resolve.",
            "next_step": "Clone readium/swift-toolkit and rerun this probe.",
        }

    has_xcode = xcodebuild["returncode"] == 0
    ios_only = readium.get("package_markers", {}).get("ios_only_manifest") is True
    has_decoration = readium.get("source_markers", {}).get("decorable_navigator") is True
    has_pointer = readium.get("source_markers", {}).get("pointer_events") is True

    if has_xcode and has_decoration and has_pointer:
        return {
            "status": "ready_for_xcode_probe",
            "reason": "Readium has decoration and pointer primitives; full Xcode is available for app-level integration.",
            "next_step": "Build a tiny iOS/Catalyst or Mac wrapper probe with EPUBNavigatorViewController.",
        }

    if not has_xcode and has_decoration and has_pointer:
        return {
            "status": "continue_with_caveat",
            "reason": "Readium has the needed primitives, but this machine is still Command Line Tools only.",
            "next_step": "Install/enable full Xcode, then verify whether UIKit navigator can run through Mac Catalyst or requires an adapter.",
            "risk": "ios_only_manifest" if ios_only else "unknown_mac_support",
        }

    return {
        "status": "blocked",
        "reason": "Readium primitives for decoration or pointer input were not confirmed.",
        "next_step": "Inspect Readium Navigator APIs manually or evaluate a WebView engine adapter.",
    }


def run(args: list[str], cwd: Path | None = None, timeout: int = 10) -> dict:
    try:
        completed = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": str(exc),
        }


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def rg_exists(pattern: str, path: Path) -> bool:
    return run(["rg", "-q", pattern, str(path)], timeout=10)["returncode"] == 0


def count_rg(pattern: str, path: Path) -> int:
    result = run(["rg", "-l", pattern, str(path)], timeout=10)
    if result["returncode"] not in {0, 1}:
        return 0
    return len([line for line in result["stdout"].splitlines() if line.strip()])


if __name__ == "__main__":
    raise SystemExit(main())

