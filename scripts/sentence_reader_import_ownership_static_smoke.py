#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SWIFT = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"


REQUIRED_MARKERS = {
    "owned import copier": "copyImportedEPUBToOwnedLibrary",
    "owned copy verifier": "verifyOwnedEPUBCopy",
    "owned file guard": "isOwnedImportedBookFile",
    "owned root resolver": "ownedBookRootURLOrThrow",
    "legacy library normalizer": "normalizedImportedBookEntry",
    "app support books directory": "appSupportBooksDirectory",
    "copy source into owned book": "copyItem(at: sourceURL, to: epubCopy)",
    "copied hash verification": "fileHash(for: copiedURL) == expectedHash",
    "copied size verification": "sourceSize >= 0 && sourceSize == copiedSize",
    "load guard for imported books": "书籍内部副本缺失，请重新导入",
    "user-facing delete-safe status": "原 EPUB 可删除",
    "reader api uses owned path": "filePath: entry.epubPath",
}


FORBIDDEN_MARKERS = {
    "book entry must not persist source url directly": "epubPath: url.path",
    "reader api must not register source url directly": "filePath: url.path",
}


def main() -> int:
    missing_files = [] if SWIFT.exists() else [str(SWIFT)]
    missing_markers: dict[str, list[str]] = {}
    forbidden_markers: dict[str, list[str]] = {}
    if SWIFT.exists():
        text = SWIFT.read_text(encoding="utf-8")
        missing = [name for name, marker in REQUIRED_MARKERS.items() if marker not in text]
        forbidden = [name for name, marker in FORBIDDEN_MARKERS.items() if marker in text]
        if missing:
            missing_markers[str(SWIFT)] = missing
        if forbidden:
            forbidden_markers[str(SWIFT)] = forbidden

    if missing_files or missing_markers or forbidden_markers:
        print(
            "import ownership static FAIL "
            f"missing_files={missing_files} "
            f"missing_markers={missing_markers} "
            f"forbidden_markers={forbidden_markers}"
        )
        return 1
    print("import ownership static PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
