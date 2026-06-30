#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sentence_reader_library_ui_static_smoke as library_smoke


def main() -> int:
    status = library_smoke.main()
    if status != 0:
        return status
    print("library v2 smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
