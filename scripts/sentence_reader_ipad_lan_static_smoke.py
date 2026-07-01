#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "reader_api" / "app.py"
SWIFT = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"
PLAN = ROOT / "docs" / "ipad_lan_reader_plan.md"
API_SMOKE = ROOT / "scripts" / "reader_api_ipad_lan_smoke.py"


REQUIRED = {
    APP: [
        '@app.get("/lan/reader"',
        '@app.get("/lan/books")',
        '@app.get("/lan/books/{book_id}/manifest")',
        '@app.get("/lan/books/{book_id}/chapters/{chapter_index}")',
        '@app.get("/lan/books/{book_id}/asset/{asset_path:path}")',
        '@app.post("/lan/audio-notes/transcribe")',
        "epub_publication",
        "epub_rootfile_path",
        "transform_epub_html_assets",
        "body_match",
        "sentence_reader.lan_manifest.v1",
        "sentence_reader.lan_chapter.v1",
        "sentence_reader.lan_audio_transcription.v1",
        "trusted_lan_only",
        "drawer-open",
        "tocToggle",
        "closeDrawer",
        "turnPage",
        "layoutPages",
        "measuredContentWidth",
        "pageRatio",
        "lan_reader_paginated",
        "noteToast",
        "showNoteToast",
        "noteToastVisible",
        "sentenceBar",
        "barRed",
        "barNote",
        "barVoice",
        "barCopy",
        "barCancel",
        "copyFocusedSentence",
        "settingsSheet",
        "fontSettings",
        "fontSize",
        "lineHeight",
        "sidePadding",
        "sentenceReaderLanSettings",
        "goLibraryHome",
        "libraryHome",
        "__SentenceReaderInteractionRouter",
        "sentence-reader-first",
        "hasSystemTextSelection",
        "isEditableTarget",
        "shouldLetSystemHandle",
        "shouldLetSystemHandleContext",
        "claimSentenceEvent",
        "double-tap-note",
        "context-click-red",
        "contextmenu",
        "focusSentence(node);",
        "toggleRed().catch",
        "event.altKey ? lookupWordFromEvent(event) : ''",
        "touchSentence",
        "longPressTimer",
        "pageTurnLockUntil",
        "schedulePendingPageTurn",
        "pageTurnCooldownMs = 180",
        "state.pageTurnLockUntil = now + pageTurnCooldownMs",
        "wheelPageTurnThreshold = 96",
        "wheelDominanceRatio = 1.25",
        "wheelInertiaLockMs = 210",
        "hideNoteToast();",
        "{ passive: false }",
        "MediaRecorder",
        "audioFile",
        "webkitSpeechRecognition",
        "touchStartX",
        "100dvh",
    ],
    SWIFT: [
        "iPadLANButton",
        "showIPadLANReader",
        "ensureReaderAPILANAvailable",
        "preferredIPadLANReaderURL",
        "localLANAddresses",
        "READER_API_HOST",
        "0.0.0.0",
        "/lan/reader",
    ],
    PLAN: [
        "Sentence Reader iPad LAN Reader V1 Plan",
        "trusted same-LAN use only",
        "`GET /lan/reader`",
        "Manual Acceptance",
    ],
    API_SMOKE: [
        "reader api ipad lan smoke PASS",
        "write_epub",
        "TestClient",
        "/lan/books/book_lan_smoke/manifest",
        "turnPage",
        "startVoiceNote",
        "/lan/audio-notes/transcribe",
    ],
}


def main() -> int:
    missing_files = [str(path) for path in REQUIRED if not path.exists()]
    missing_markers: dict[str, list[str]] = {}
    for path, markers in REQUIRED.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            missing_markers[str(path)] = missing
    if missing_files or missing_markers:
        print(f"ipad lan static FAIL missing_files={missing_files} missing_markers={missing_markers}")
        return 1
    print("ipad lan static PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
