#!/usr/bin/env python3
from __future__ import annotations

import plistlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ICON_GENERATOR = ROOT / "scripts" / "generate_sentence_reader_icon.py"
DOCK_PIN = ROOT / "scripts" / "pin_sentence_reader_to_dock.py"
PACKAGE = ROOT / "scripts" / "package_sentence_reader_app.py"
APP = ROOT / "build" / "Sentence Reader.app"
INFO_PLIST = APP / "Contents" / "Info.plist"
APP_ICON = ROOT / "assets" / "SentenceReader.icns"
PACKAGED_ICON = APP / "Contents" / "Resources" / "SentenceReader.icns"


def has_markers(path: Path, markers: list[str]) -> list[str]:
    if not path.exists():
        return [f"missing_file:{path}"]
    text = path.read_text(encoding="utf-8")
    return [marker for marker in markers if marker not in text]


def main() -> int:
    missing: dict[str, list[str]] = {}
    for path, markers in {
        ICON_GENERATOR: ["SentenceReader.icns", "iconutil", "leftPage", "rightPage", "bookmark"],
        DOCK_PIN: ["persistent-apps", "Sentence Reader.app", "killall", "Dock", "--dry-run", "dedupe_dock_entries", "removed_duplicates"],
        PACKAGE: ["CFBundleIconFile", "SentenceReader.icns", "ensure_app_icon", "app_icon="],
    }.items():
        result = has_markers(path, markers)
        if result:
            missing[str(path)] = result

    if not APP_ICON.exists():
        missing[str(APP_ICON)] = ["icon_missing"]
    if not PACKAGED_ICON.exists():
        missing[str(PACKAGED_ICON)] = ["packaged_icon_missing"]
    if INFO_PLIST.exists():
        with INFO_PLIST.open("rb") as fh:
            plist = plistlib.load(fh)
        if plist.get("CFBundleIconFile") != "SentenceReader":
            missing[str(INFO_PLIST)] = [f"CFBundleIconFile={plist.get('CFBundleIconFile')!r}"]
    else:
        missing[str(INFO_PLIST)] = ["info_plist_missing"]

    if missing:
        print(f"identity static FAIL {missing}")
        return 1
    print("identity static PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
