#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIRE = ROOT / "prototypes" / "v1_reader_wireframe.html"

REQUIRED_MARKERS = [
    "workspace",
    "sidebar",
    "reader-shell",
    "notesRail",
    "floating-editor",
    "contextMenu",
    "dblclick",
    "contextmenu",
    "toggleHighlight",
    "readerEntry",
    "阅读入口",
    "Sentence Reader",
]


def main() -> int:
    text = WIRE.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_MARKERS if marker not in text]
    if missing:
        print(f"wireframe FAIL missing={missing}")
        return 1
    print(f"wireframe PASS path={WIRE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
