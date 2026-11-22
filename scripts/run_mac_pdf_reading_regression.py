"""Exercise the native PDF reader; pass ClickLocalVoice to include real offline playback."""
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "Probe/NativeSentenceReader/SentenceReaderNative.swift").read_text()
declarations, marker, _ = source.partition("\n#if !CLICK_EPUB_READING_ORDER_PROBE\nlet app = NSApplication.shared")
assert marker, "Cannot isolate the native app entry point"
with tempfile.TemporaryDirectory() as directory:
    probe = Path(directory) / "regression.swift"
    probe.write_text(declarations + "\n" + Path(__file__).with_name("mac_pdf_reading_regression.swift").read_text())
    contents = Path(directory) / "ReaderProbe.app/Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Info.plist").write_bytes(plistlib.dumps({
        "CFBundleIdentifier": "local.click.pdf-regression", "CFBundleExecutable": "ReaderProbe",
        "CFBundlePackageType": "APPL",
    }))
    if len(sys.argv) == 2:
        (contents / "Resources").mkdir()
        (contents / "Resources/ClickLocalVoice").symlink_to(Path(sys.argv[1]).resolve())
    binary = contents / "MacOS/ReaderProbe"
    subprocess.run(["xcrun", "swiftc", "-parse-as-library", str(probe), "-o", str(binary)], check=True)
    subprocess.run([str(binary), *sys.argv[1:]], check=True)
