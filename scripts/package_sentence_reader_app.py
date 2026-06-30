#!/usr/bin/env python3
from __future__ import annotations

import json
import plistlib
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VISUAL_PROBE = ROOT / "Probe" / "ReadiumVisualReaderProbe"
NATIVE_SOURCE = ROOT / "Probe" / "NativeSentenceReader" / "SentenceReaderNative.swift"
APP = ROOT / "build" / "Click.app"
LEGACY_APP = ROOT / "build" / "Sentence Reader.app"
EXECUTABLE = APP / "Contents" / "MacOS" / "SentenceReader"
INFO_PLIST = APP / "Contents" / "Info.plist"
RESOURCES = APP / "Contents" / "Resources"
RUNTIME = RESOURCES / "ReaderRuntime"
DEFAULT_EPUB = ROOT / "fixtures" / "sentence-reader-smoke.epub"
NATIVE_BINARY = ROOT / "build" / "SentenceReaderNative"
PACKAGE_CACHE = Path("/tmp/sentence-reader-readium-xcode-packages")
DERIVED_DATA = Path("/tmp/sentence-reader-readium-visual-derived")
PRODUCTS = DERIVED_DATA / "Build" / "Products" / "Debug-maccatalyst"
PRODUCT_BINARY = PRODUCTS / "ReadiumVisualReaderProbe"
READER_VENV = ROOT / ".venv-reader-api"
APP_ICON = ROOT / "assets" / "SentenceReader.icns"
APP_ICON_NAME = "SentenceReader"


def ensure_default_epub() -> None:
    if DEFAULT_EPUB.exists():
        return
    DEFAULT_EPUB.parent.mkdir(parents=True, exist_ok=True)
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
    with zipfile.ZipFile(DEFAULT_EPUB, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, content in files.items():
            archive.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)


def copy_reader_venv() -> None:
    source = READER_VENV
    target = RUNTIME / ".venv-reader-api"
    if not source.exists():
        return
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        symlinks=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )


def write_runtime_manifest() -> None:
    runtime_python = RUNTIME / ".venv-reader-api" / "bin" / "python"
    pyvenv = RUNTIME / ".venv-reader-api" / "pyvenv.cfg"
    manifest = {
        "schema": "sentence_reader.runtime_manifest.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime": str(RUNTIME),
        "reader_api": str(RUNTIME / "reader_api"),
        "requirements": str(RUNTIME / "requirements-reader-api.txt"),
        "bootstrap": {
            "script": str(RUNTIME / "scripts" / "sentence_reader_runtime_bootstrap.py"),
            "first_run_preflight": str(RUNTIME / "scripts" / "sentence_reader_first_run_preflight.py"),
            "runtime_config": str(RUNTIME / "scripts" / "sentence_reader_runtime_config.py"),
            "user_venv": "~/Library/Application Support/SentenceReader/Runtime/.venv-reader-api",
            "auto_repair_requires_env": "SENTENCE_READER_BOOTSTRAP_REPAIR=1",
            "dependency_install_requires_env": "SENTENCE_READER_BOOTSTRAP_INSTALL_DEPS=1",
        },
        "python": {
            "path": str(runtime_python),
            "exists": runtime_python.exists(),
            "realpath": str(runtime_python.resolve(strict=False)),
            "pyvenv_cfg": pyvenv.read_text(encoding="utf-8", errors="replace") if pyvenv.exists() else "",
            "portable_clean_mac_ready": False,
        },
        "postgres": {
            "strategy": "external_postgres_app_or_POSTGRES_APP_BIN",
            "bundled": False,
            "default_bin": "/Applications/Postgres.app/Contents/Versions/latest/bin",
        },
        "portability": {
            "current_machine_supported": True,
            "clean_mac_supported": False,
            "bootstrap_preflight_supported": True,
            "known_blockers": [
                "runtime_python_points_outside_ReaderRuntime_when copied from Xcode virtualenv",
                "postgres_not_bundled",
            ],
        },
    }
    (RUNTIME / "runtime_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def copy_reader_runtime() -> None:
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    RUNTIME.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        ROOT / "reader_api",
        RUNTIME / "reader_api",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        ROOT / "migrations",
        RUNTIME / "migrations",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    scripts_dir = RUNTIME / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for script_name in (
        "run_reader_api.sh",
        "reader_pg_migrate.py",
        "reader_pg_status.py",
        "sentence_reader_runtime_bootstrap.py",
        "sentence_reader_runtime_config.py",
        "sentence_reader_first_run_preflight.py",
        "sentence_reader_product_diagnostics.py",
        "sentence_reader_runtime_portability.py",
        "sentence_reader_backup.py",
        "sentence_reader_restore_verify.py",
        "sentence_reader_hermes_ingest.py",
        "sentence_reader_intake_draft.py",
        "sentence_reader_promote_intake_draft.py",
        "sentence_reader_review_queue.py",
        "sentence_reader_active_pack_operator.py",
        "sentence_reader_book_vocab.py",
    ):
        source = ROOT / "scripts" / script_name
        if source.exists():
            target = scripts_dir / script_name
            shutil.copy2(source, target)
            target.chmod(0o755)
    shutil.copy2(ROOT / "requirements-reader-api.txt", RUNTIME / "requirements-reader-api.txt")
    copy_reader_venv()
    write_runtime_manifest()
    (RUNTIME / "README_RUNTIME.md").write_text(
        "\n".join(
            [
                "# Sentence Reader Runtime",
                "",
                "This folder is the bundled boundary for Reader API startup and product diagnostics.",
                "It includes a project-verified `.venv-reader-api` when that environment exists at package time.",
                "The native shell starts `scripts/run_reader_api.sh`, which prefers this bundled virtual environment.",
                "If the bundled virtual environment is unavailable, startup can call `sentence_reader_runtime_bootstrap.py`.",
                "If bundled startup is unavailable, the native shell can still fall back to the development project script.",
                "Runtime portability is assessed by `scripts/sentence_reader_runtime_portability.py` and `runtime_manifest.json`.",
                "First-run readiness is assessed by `scripts/sentence_reader_first_run_preflight.py`.",
                "Local paths such as FunASR can be configured with `scripts/sentence_reader_runtime_config.py`.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def ensure_app_icon() -> bool:
    generator = ROOT / "scripts" / "generate_sentence_reader_icon.py"
    if APP_ICON.exists() and generator.exists() and APP_ICON.stat().st_mtime >= generator.stat().st_mtime:
        return True
    if not generator.exists():
        return False
    result = subprocess.run(
        ["python3", str(generator), "--quiet"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout)
        return False
    return APP_ICON.exists()


def main() -> int:
    build = subprocess.run(
        [
            "xcodebuild",
            "-scheme",
            "ReadiumVisualReaderProbe",
            "-destination",
            "generic/platform=macOS,variant=Mac Catalyst",
            "-clonedSourcePackagesDirPath",
            str(PACKAGE_CACHE),
            "-derivedDataPath",
            str(DERIVED_DATA),
            "build",
        ],
        cwd=VISUAL_PROBE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if build.returncode != 0:
        print(build.stdout)
        return build.returncode

    if not PRODUCT_BINARY.exists():
        print(f"Missing built executable: {PRODUCT_BINARY}")
        return 1

    native = subprocess.run(
        [
            "swiftc",
            str(NATIVE_SOURCE),
            "-o",
            str(NATIVE_BINARY),
            "-framework",
            "Cocoa",
            "-framework",
            "WebKit",
            "-framework",
            "AVFoundation",
            "-framework",
            "Speech",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if native.returncode != 0:
        print(native.stdout)
        return native.returncode

    for app_bundle in (APP, LEGACY_APP):
        if app_bundle.exists():
            shutil.rmtree(app_bundle)

    EXECUTABLE.parent.mkdir(parents=True, exist_ok=True)
    RESOURCES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(NATIVE_BINARY, EXECUTABLE)
    EXECUTABLE.chmod(0o755)

    for bundle in PRODUCTS.glob("*.bundle"):
        shutil.copytree(bundle, RESOURCES / bundle.name)

    copy_reader_runtime()
    icon_ready = ensure_app_icon()
    if icon_ready:
        shutil.copy2(APP_ICON, RESOURCES / f"{APP_ICON_NAME}.icns")

    ensure_default_epub()
    shutil.copy2(DEFAULT_EPUB, RESOURCES / "default-fixture.epub")
    book_dir = RESOURCES / "default-book"
    if book_dir.exists():
        shutil.rmtree(book_dir)
    with zipfile.ZipFile(DEFAULT_EPUB) as archive:
        archive.extractall(book_dir)

    plist = {
        "CFBundleDevelopmentRegion": "zh_CN",
        "CFBundleExecutable": "SentenceReader",
        "CFBundleIdentifier": "local.sentence-reader.v1.readium",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleIconFile": APP_ICON_NAME if icon_ready else "",
        "CFBundleName": "Click",
        "CFBundleDisplayName": "Click",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "EPUB Publication",
                "CFBundleTypeExtensions": ["epub"],
                "CFBundleTypeMIMETypes": ["application/epub+zip"],
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Owner",
                "LSItemContentTypes": ["org.idpf.epub-container"],
            }
        ],
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "1",
        "DTPlatformName": "maccatalyst",
        "LSMinimumSystemVersion": "14.0",
        "LSApplicationCategoryType": "public.app-category.productivity",
        "NSHighResolutionCapable": True,
        "NSDesktopFolderUsageDescription": "Click can open EPUB files selected from Desktop.",
        "NSDocumentsFolderUsageDescription": "Click can open EPUB files selected from Documents.",
        "NSMicrophoneUsageDescription": "Click records short voice notes so they can be converted to text.",
        "NSSpeechRecognitionUsageDescription": "Click can use Apple Speech to convert short voice notes to text.",
        "NSSupportsAutomaticGraphicsSwitching": True,
        "UIDeviceFamily": [2, 6],
        "UIApplicationSupportsIndirectInputEvents": True,
    }
    with INFO_PLIST.open("wb") as fh:
        plistlib.dump(plist, fh)

    print(f"packaged={APP}")
    print(f"executable={EXECUTABLE}")
    print(f"native_shell={NATIVE_SOURCE}")
    print(f"readium_probe_binary={PRODUCT_BINARY}")
    print(f"resources={len(list(RESOURCES.glob('*.bundle')))} bundles")
    print(f"reader_runtime={RUNTIME}")
    print(f"reader_runtime_venv={(RUNTIME / '.venv-reader-api').exists()}")
    print(f"app_icon={icon_ready}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
