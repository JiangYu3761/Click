#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WINDOWS_PLAN = ROOT / "docs" / "windows_client_plan.md"


README_REQUIRED = [
    "## 平台支持",
    "macOS App",
    "当前主力可用",
    "iPad / 浏览器",
    "当前可用",
    "Windows 浏览器版",
    "计划优先支持",
    "Windows 桌面版",
    "后续规划",
    "Windows 快捷键",
    "Web 层已实现基础键盘契约",
    "Windows 不重写阅读器",
    "Reader API",
    "Web 主界面",
    "Web 阅读器",
    "软件层本地识别优先",
    "系统语音识别只能作为备选",
]

WINDOWS_PLAN_REQUIRED = [
    "P1: Windows Browser Version",
    "P2: Windows Desktop Shell",
    "P3: Windows Installer",
    "WebView2",
    "Tauri",
    "Click.exe",
    "desktop shortcut",
    "Start Menu shortcut",
    "Windows reader shortcuts",
    "N` for note",
    "R` for red highlight",
    "V` for voice note",
    "system or browser speech recognition only as a fallback",
    "Do not rewrite a Windows native reader",
    "Do not create a second database",
]

FORBIDDEN_PATTERNS = [
    re.compile(r"Windows\s*已完成"),
    re.compile(r"Windows\s*当前可用"),
    re.compile(r"Windows\s*主力可用"),
    re.compile(r"Windows\s*已经支持"),
    re.compile(r"Windows\s*ready", re.IGNORECASE),
    re.compile(r"Windows\s*complete", re.IGNORECASE),
]


def require_contains(path: Path, markers: list[str], failures: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            failures.append(f"{path.relative_to(ROOT)} missing marker: {marker}")


def forbid_overclaims(path: Path, failures: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_PATTERNS:
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            failures.append(f"{path.relative_to(ROOT)}:{line_no}: Windows overclaim: {match.group(0)}")


def main() -> int:
    failures: list[str] = []
    for path in [README, WINDOWS_PLAN]:
        if not path.exists():
            failures.append(f"missing file: {path.relative_to(ROOT)}")
    if failures:
        print("public readme platform smoke FAIL")
        for failure in failures:
            print(failure)
        return 1

    require_contains(README, README_REQUIRED, failures)
    require_contains(WINDOWS_PLAN, WINDOWS_PLAN_REQUIRED, failures)
    forbid_overclaims(README, failures)
    forbid_overclaims(WINDOWS_PLAN, failures)

    if failures:
        print("public readme platform smoke FAIL")
        for failure in failures:
            print(failure)
        return 1

    print("public readme platform smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
