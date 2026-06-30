#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE_ROOT = ROOT / "Probe" / "ReadiumPublicationOpenProbe"
REPORT = ROOT / "reports" / "readium_publication_open_probe.json"
SUMMARY = ROOT / "reports" / "readium_publication_open_summary.json"
TEST_SUMMARY = Path("/tmp/sentence-reader-readium-publication-open-summary.json")
DEFAULT_FIXTURE = ROOT / "fixtures" / "sentence-reader-smoke.epub"
TMP_FIXTURE = Path("/tmp/sentence-reader-fixtures/good-strategy-bad-strategy.epub")
PACKAGE_CACHE = Path("/tmp/sentence-reader-readium-xcode-packages")
DERIVED_DATA = Path("/tmp/sentence-reader-readium-publication-derived")


def main() -> int:
    parser = argparse.ArgumentParser(description="Open a real EPUB through Readium Streamer in a Catalyst XCTest probe.")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--use-tmp-copy", action="store_true", default=True)
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("READIUM_PUBLICATION_OPEN_TIMEOUT", "300")))
    args = parser.parse_args()

    source_fixture = Path(args.fixture).expanduser()
    if source_fixture == DEFAULT_FIXTURE:
        ensure_default_fixture(source_fixture)
    runtime_fixture = prepare_fixture(source_fixture, use_tmp_copy=args.use_tmp_copy)

    payload = {
        "schema_version": "sentence_reader.readium_publication_open_probe.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe_root": str(PROBE_ROOT),
        "source_fixture": str(source_fixture),
        "runtime_fixture": str(runtime_fixture) if runtime_fixture else None,
        "summary_report": str(SUMMARY),
        "environment": {
            "xcode_select": run(["xcode-select", "-p"], timeout=10),
            "xcodebuild_version": run(["xcodebuild", "-version"], timeout=10),
        },
        "commands": {},
        "summary": None,
        "decision": {},
    }

    if runtime_fixture is None:
        payload["decision"] = {
            "status": "blocked",
            "reason": "EPUB fixture is missing.",
            "next_step": "Put a non-DRM EPUB on the Desktop or pass --fixture.",
        }
        write_report(payload)
        print_status(payload)
        return 1

    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    for path in [SUMMARY, TEST_SUMMARY]:
        if path.exists():
            path.unlink()

    env = dict(os.environ)
    env["SENTENCE_READER_EPUB_FIXTURE"] = str(runtime_fixture)
    env["SENTENCE_READER_PUBLICATION_OPEN_SUMMARY"] = str(SUMMARY)

    PACKAGE_CACHE.mkdir(parents=True, exist_ok=True)
    payload["commands"]["xcodebuild_test_publication_open"] = run(
        [
            "xcodebuild",
            "test",
            "-scheme",
            "ReadiumPublicationOpenProbe",
            "-destination",
            "platform=macOS,variant=Mac Catalyst,name=My Mac",
            "-clonedSourcePackagesDirPath",
            str(PACKAGE_CACHE),
            "-derivedDataPath",
            str(DERIVED_DATA),
        ],
        cwd=PROBE_ROOT,
        timeout=args.timeout,
        env=env,
    )

    payload["summary"] = read_summary()
    payload["decision"] = decide(payload)
    write_report(payload)
    print_status(payload)
    return 0 if payload["decision"]["status"] == "opened" else 1


def prepare_fixture(source: Path, use_tmp_copy: bool) -> Path | None:
    if not source.exists():
        return None
    if not use_tmp_copy:
        return source
    TMP_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    if not TMP_FIXTURE.exists() or source.stat().st_mtime_ns != TMP_FIXTURE.stat().st_mtime_ns:
        shutil.copy2(source, TMP_FIXTURE)
    return TMP_FIXTURE


def ensure_default_fixture(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    files = {
        "META-INF/container.xml": """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        "EPUB/package.opf": """<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" unique-identifier="bookid" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">sentence-reader-smoke</dc:identifier>
    <dc:title>Sentence Reader Smoke Book</dc:title>
    <dc:language>en</dc:language>
    <dc:creator>Sentence Reader</dc:creator>
    <meta property="dcterms:modified">2026-06-29T00:00:00Z</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter"/>
  </spine>
</package>
""",
        "EPUB/nav.xhtml": """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <head><title>Contents</title></head>
  <body>
    <nav epub:type="toc">
      <ol><li><a href="chapter.xhtml">Smoke Chapter</a></li></ol>
    </nav>
  </body>
</html>
""",
        "EPUB/chapter.xhtml": """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Smoke Chapter</title></head>
  <body>
    <h1>Smoke Chapter</h1>
    <p>Strategy is a coherent response to a real challenge.</p>
    <p>Good reading software should preserve notes, highlights, and position.</p>
  </body>
</html>
""",
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, content in files.items():
            archive.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)


def read_summary() -> dict | None:
    if TEST_SUMMARY.exists():
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEST_SUMMARY, SUMMARY)
    if not SUMMARY.exists():
        return None
    try:
        return json.loads(SUMMARY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def decide(payload: dict) -> dict:
    command = payload["commands"].get("xcodebuild_test_publication_open", {})
    summary = payload.get("summary")
    if command.get("returncode") == 0 and summary:
        return {
            "status": "opened",
            "reason": "Readium Streamer opened the real EPUB fixture and produced a publication summary.",
            "next_step": "Build a minimal visual app target around EPUBNavigatorViewController.",
        }
    if command.get("timed_out"):
        return {
            "status": "timed_out",
            "reason": "Publication open probe timed out.",
            "next_step": "Inspect the xcresult and rerun with a longer timeout.",
        }
    return {
        "status": "failed",
        "reason": "Readium publication open probe failed or did not write a summary.",
        "next_step": "Inspect stdout/stderr tail in readium_publication_open_probe.json.",
    }


def run(args: list[str], cwd: Path | None = None, timeout: int = 10, env: dict | None = None) -> dict:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return {
            "args": args,
            "cwd": str(cwd) if cwd else None,
            "returncode": completed.returncode,
            "stdout": tail(completed.stdout),
            "stderr": tail(completed.stderr),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = decode_timeout_stream(exc.stdout)
        stderr = decode_timeout_stream(exc.stderr)
        return {
            "args": args,
            "cwd": str(cwd) if cwd else None,
            "returncode": 124,
            "stdout": tail(stdout),
            "stderr": tail((stderr + f"\nTimed out after {timeout} seconds").strip()),
            "timed_out": True,
        }


def decode_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def tail(text: str, limit: int = 12000) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def write_report(payload: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_status(payload: dict) -> None:
    decision = payload.get("decision", {})
    summary = payload.get("summary") or {}
    print(f"readium publication open probe: {decision.get('status', 'unknown')}")
    print(f"reason: {decision.get('reason', '')}")
    if summary:
        print(f"title={summary.get('title', '')}")
        print(f"media_type={summary.get('mediaType', '')}")
        print(f"reading_order={summary.get('readingOrderCount', '')}")
        print(f"toc={summary.get('tableOfContentsCount', '')}")
    print(f"report={REPORT}")


if __name__ == "__main__":
    raise SystemExit(main())
