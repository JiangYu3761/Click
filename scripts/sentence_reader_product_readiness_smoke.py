#!/usr/bin/env python3
from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
APP_BUNDLE = ROOT / "build" / "Click.app"
CURRENT_STATUS = ROOT / "docs" / "current_status.md"
PRODUCT_ROADMAP = ROOT / "docs" / "product_roadmap.md"
PRODUCT_ACCEPTANCE = ROOT / "docs" / "product_acceptance.md"
LAN_MARKERS = [
    "drawer-open",
    "tocToggle",
    "turnPage",
    "measuredContentWidth",
    "noteToast",
    "startVoiceNote",
    "/lan/audio-notes/transcribe",
    "lan_reader_paginated",
]


def run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.returncode, result.stdout


def local_lan_addresses() -> list[str]:
    addresses: list[str] = []
    code, output = run(["/sbin/ifconfig"])
    if code != 0:
        return addresses
    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] == "inet":
            ip = parts[1]
            if ip.startswith(("127.", "169.254.", "0.")):
                continue
            if ip.count(".") == 3 and ip not in addresses:
                addresses.append(ip)
    if addresses:
        return addresses
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ip.count(".") == 3 and not ip.startswith(("127.", "169.254.", "0.")) and ip not in addresses:
                addresses.append(ip)
    except socket.gaierror:
        pass
    return addresses


def fetch(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with urlopen(url, timeout=timeout) as response:  # noqa: S310 - local/LAN readiness smoke.
            return response.status == 200, response.read().decode("utf-8", errors="replace")
    except (OSError, URLError) as exc:
        return False, str(exc)


def check_docs() -> list[str]:
    failures: list[str] = []
    required_docs = {
        CURRENT_STATUS: ["日常可用产品级", "iPad LAN Reader", "http://<mac-lan-ip>:18180/lan/reader"],
        PRODUCT_ROADMAP: ["V2.1", "iPad LAN Reader", "browser recording upload"],
        PRODUCT_ACCEPTANCE: ["Sentence Reader Product Acceptance", "Daily-use Product Boundary", "Stop Condition"],
    }
    for path, markers in required_docs.items():
        if not path.exists():
            failures.append(f"missing_doc:{path}")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            failures.append(f"doc_markers:{path.name}:{','.join(missing)}")
    return failures


def check_lan_service() -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    detail: dict[str, Any] = {}
    code, output = run(["/usr/sbin/lsof", "-nP", "-iTCP:18180", "-sTCP:LISTEN"])
    listeners = [line for line in output.splitlines() if "TCP" in line and ":18180" in line]
    detail["listeners"] = listeners
    if code != 0 or len(listeners) != 1:
        failures.append(f"lan_listener_count:{len(listeners)}")
    elif "*:18180" not in listeners[0] and "0.0.0.0:18180" not in listeners[0]:
        failures.append("lan_listener_not_all_interfaces")

    ok, text = fetch("http://127.0.0.1:18180/lan/reader")
    detail["local_page_ok"] = ok
    if not ok:
        failures.append("local_lan_page_unavailable")
    else:
        missing = [marker for marker in LAN_MARKERS if marker not in text]
        if missing:
            failures.append(f"local_lan_page_markers:{','.join(missing)}")

    addresses = local_lan_addresses()
    detail["lan_addresses"] = addresses
    if not addresses:
        failures.append("missing_lan_address")
    else:
        lan_url = f"http://{addresses[0]}:18180/lan/reader"
        ok, text = fetch(lan_url)
        detail["preferred_lan_url"] = lan_url
        detail["preferred_lan_page_ok"] = ok
        if not ok:
            failures.append("preferred_lan_page_unavailable")
        else:
            missing = [marker for marker in LAN_MARKERS if marker not in text]
            if missing:
                failures.append(f"preferred_lan_page_markers:{','.join(missing)}")

    return failures, detail


def check_funasr() -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    ok, text = fetch("http://127.0.0.1:18081/health", timeout=2.0)
    detail: dict[str, Any] = {"ok": ok, "required": False, "raw": text[:200]}
    if not ok:
        detail["decision"] = "funasr_health_unavailable"
        return failures, detail
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        detail["decision"] = "optional_invalid_json"
        return failures, detail
    detail["payload"] = payload
    if payload.get("ok") is not True:
        detail["decision"] = "optional_not_ok"
    else:
        detail["decision"] = "optional_ready"
    return failures, detail


def main() -> int:
    failures: list[str] = []
    report: dict[str, Any] = {
        "schema": "sentence_reader.product_readiness_smoke.v1",
        "app_bundle_exists": APP_BUNDLE.exists(),
    }
    if not APP_BUNDLE.exists():
        failures.append("missing_app_bundle")

    failures.extend(check_docs())
    lan_failures, lan_detail = check_lan_service()
    funasr_failures, funasr_detail = check_funasr()
    failures.extend(lan_failures)
    failures.extend(funasr_failures)
    report["lan"] = lan_detail
    report["funasr"] = funasr_detail
    report["ok"] = not failures
    report["failures"] = failures
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if failures:
        print(f"sentence reader product readiness smoke FAIL failures={failures}", file=sys.stderr)
        return 1
    print("sentence reader product readiness smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
