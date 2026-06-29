#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"


REQUIRED_MARKERS = {
    "reader settings model": "struct ReaderSettings",
    "reader settings storage key": "SentenceReader.readerSettings.v1",
    "settings button": "settingsButton",
    "settings menu": "showReaderSettings",
    "settings change action": "changeReaderSetting",
    "settings persistence load": "loadReaderSettings",
    "settings persistence save": "saveReaderSettings",
    "settings sanitize": "sanitizedReaderSettings",
    "webview settings injection": "applyReaderSettingsToWebView",
    "js settings bridge": "__sentenceReaderApplySettings",
    "css font variable": "--sr-font-size",
    "css line height variable": "--sr-line-height",
    "css margin variable": "--sr-page-margin-x",
    "css theme background variable": "--sr-bg",
    "warm theme": "theme === 'warm'",
    "page reflow after settings": "applyPage(false, 0)",
    "pagination cache invalidation": "invalidatePagination",
    "viewport-filled page surface": "height: 100vh !important;",
    "tight bottom page padding": "padding: 2px var(--sr-page-margin-x) 4px !important;",
    "webkit column fill": "-webkit-column-fill: auto !important;",
    "paragraphs can cross pages": "break-inside: auto !important;",
    "real content width pagination": "measuredContentWidth",
    "pagination sliver guard": "paginationEpsilon",
    "left page sliver guard": "leftPageSliverGuard",
    "pixel aligned offset": "pixelAlignedOffset",
    "safe page offset": "pageOffsetForIndex",
    "horizontal swipe state machine": "handleHorizontalWheel",
    "horizontal swipe threshold": "wheelGestureDistance >= 144",
    "horizontal swipe inertia lock": "wheelInertiaLockUntil = now + pageTurnCooldownMs",
    "page turn cooldown lock": "pageTurnLockUntil = now + pageTurnCooldownMs",
    "Esc closes attached note sheet": "dismissAttachedSheetIfNeeded",
    "vertical wheel suppression": "event.preventDefault();",
    "immersive chrome hidden default": "setReaderChromeVisible(false)",
    "immersive chrome monitor": "installReaderChromeMonitor",
    "immersive chrome full webview": "webView.topAnchor.constraint(equalTo: root.topAnchor)",
    "image height containment": "max-height: calc(100vh - 16px)",
    "image page break protection": "break-inside: avoid !important;",
    "chapter edge bridge": "post({ type: 'edge'",
    "annotation core v2 flag": "__sentenceReaderAnnotationCoreV2",
    "full annotation restore": "__sentenceReaderApplyAnnotations",
    "note markers": "applyNoteMarkers",
    "note preview on click": "postNotePreview",
    "selection range intersection": "rangesIntersect",
    "selected sentences": "selectedSentences",
    "selection awareness": "hasSystemTextSelection",
    "interaction router": "__SentenceReaderInteractionRouter",
    "sentence reader priority": "sentence-reader-first",
    "editable system guard": "isEditableTarget",
    "system routing guard": "shouldLetSystemHandle",
    "context red routing guard": "shouldLetSystemHandleContext",
    "sentence event claim helper": "claimSentenceEvent",
    "hard context red route": "return toggleRed(sentenceFromTarget(event.target), event);",
    "double click note default": "double-click-note",
    "batch red toggle": "toggleRedSentences",
    "non-boundary colon semicolon": "nonSentenceBoundaryCharacters = '：:；;'",
}


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    missing = [name for name, marker in REQUIRED_MARKERS.items() if marker not in text]
    if missing:
        print(f"reader stability static FAIL missing={missing}")
        return 1
    print("reader stability static PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
