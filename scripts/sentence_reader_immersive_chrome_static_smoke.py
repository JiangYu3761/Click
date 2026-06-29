#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SWIFT = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"

MARKERS = [
    "readerHeaderView",
    "readerFooterView",
    "readerChromeEventMonitor",
    "installReaderChromeMonitor",
    "revealReaderChromeTemporarily",
    "scheduleReaderChromeAutoHide",
    "setReaderChromeVisible(false)",
    ".mouseMoved",
    "mouseLocationOutsideOfEventStream",
    "titlebarAppearsTransparent = true",
    ".fullSizeContentView",
    "window.acceptsMouseMovedEvents = true",
    "webView.topAnchor.constraint(equalTo: root.topAnchor)",
    "notesRailWidthConstraint = notesRail.widthAnchor.constraint(equalToConstant: 0)",
    "notesRail.isHidden = true",
    "notesRail.topAnchor.constraint(equalTo: header.bottomAnchor",
    "notesRail.bottomAnchor.constraint(equalTo: footer.topAnchor",
]


def main() -> int:
    if not SWIFT.exists():
        print(f"immersive chrome static FAIL missing={SWIFT}")
        return 1
    text = SWIFT.read_text(encoding="utf-8")
    missing = [marker for marker in MARKERS if marker not in text]
    if missing:
        print(f"immersive chrome static FAIL missing_markers={missing}")
        return 1
    print("immersive chrome static PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
