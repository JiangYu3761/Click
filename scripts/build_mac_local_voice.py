"""Build the offline Chinese/English Kokoro voice for the native macOS reader."""
import argparse
import gzip
import hashlib
from pathlib import Path
import sqlite3
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RELEASES = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
LIB = "sherpa-onnx-v1.12.39-osx-universal2-shared-lib"
MODEL = "kokoro-int8-multi-lang-v1_1"
IPA = "https://raw.githubusercontent.com/open-dict-data/ipa-dict/972cd67dd5f96bc5660e28070cde26e3928abcd7"
ASSETS = {
    "en_US.txt": (f"{IPA}/data/en_US.txt", "2af6f154a5c363275f052d1f85acedef38ed185ca9745aa4314be77f6b70de67"),
    "IPA-LICENSE": (f"{IPA}/LICENSE", "2c6a7e4c71f834a8fc0114fa4f65ca85e80bc4b4dc7ed08746963a09a7b0d177"),
    LIB + ".tar.bz2": (f"{RELEASES}/v1.12.39/{LIB}.tar.bz2",
                       "144c3a47bd1ea37201eb850a1b17e91f84bf3fbf1faf6c21fb98b0a57c219487"),
    MODEL + ".tar.bz2": (f"{RELEASES}/tts-models/{MODEL}.tar.bz2",
                         "259c9c8bc906d6078e4e0570421885dabb68b539c2f970fcbb890a58eeaf3e9c"),
    "c-api.h": ("https://raw.githubusercontent.com/k2-fsa/sherpa-onnx/v1.12.39/sherpa-onnx/c-api/c-api.h",
                "437b1279047877167d8fadc74a60d47f3df514d703fdac1c1b6851da9bc2fdb4"),
}


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def build_local_voice(destination, cache):
    cache.mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        stage = Path(temp)
        for name, (url, checksum) in ASSETS.items():
            asset = cache / name
            if not asset.exists() or digest(asset) != checksum:
                with tempfile.TemporaryDirectory(dir=cache) as incoming:
                    partial = Path(incoming) / name
                    subprocess.run(["curl", "-fLsS", "--retry", "2", "-o", str(partial), url], check=True)
                    if digest(partial) != checksum:
                        raise ValueError("Unexpected checksum for " + name)
                    partial.replace(asset)
            if name.endswith(".tar.bz2"):
                subprocess.run(["tar", "-xf", str(asset), "-C", str(stage)], check=True)
        pack = stage / "ClickLocalVoice"
        pack.mkdir()
        (stage / MODEL).rename(pack / "model")
        # The index preserves multiple pronunciations and the clicked inflected form.
        db = sqlite3.connect(pack / "pronunciation.sqlite")
        try:
            db.execute("CREATE TABLE pronunciations (word TEXT PRIMARY KEY, ipa TEXT NOT NULL) WITHOUT ROWID")
            with (cache / "en_US.txt").open(encoding="utf-8") as entries:
                db.executemany("INSERT INTO pronunciations VALUES (?, ?)",
                               (line.rstrip().split("\t", 1) for line in entries if line.strip()))
            db.commit()
        finally:
            db.close()
        shutil.copy2(cache / "IPA-LICENSE", pack)
        (pack / "IPA-SOURCE.txt").write_text(
            "American English pronunciation: open-dict-data/ipa-dict (en_US), based on "
            "lingz/cmudict-ipa and CMUdict. Source and attribution: "
            "https://github.com/open-dict-data/ipa-dict/tree/972cd67dd5f96bc5660e28070cde26e3928abcd7\n"
        )
        for library in ["libsherpa-onnx-c-api.dylib", "libonnxruntime.1.24.4.dylib"]:
            shutil.copy2(stage / LIB / "lib" / library, pack)
        subprocess.run(["xcrun", "clang", "-O2", "-mmacosx-version-min=14.0", "-I", str(cache), "-L", str(pack),
                        str(ROOT / "tts_runtime/click_local_speech.c"), "-lsherpa-onnx-c-api",
                        "-Wl,-rpath,@executable_path", "-o", str(pack / "click-speak")], check=True)
        license_dir = ROOT / "apps/android/ClickShell/app/src/main/assets/licenses"
        for notice in ["espeak-ng-GPL-3.0.txt", "sherpa-onnx-Apache-2.0.txt", "kokoro-model-source.txt"]:
            shutil.copy2(license_dir / notice, pack)
        shutil.copy2(ROOT / "tts_runtime/ONNX-Runtime-LICENSE", pack)
        notices = "ONNX-Runtime-ThirdPartyNotices.txt"
        with gzip.open(ROOT / "tts_runtime" / (notices + ".gz"), "rb") as source:
            (pack / notices).write_bytes(source.read())
        pack.rename(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--cache", type=Path, default=ROOT / "build/mac-local-voice-downloads")
    args = parser.parse_args()
    build_local_voice(args.destination.resolve(), args.cache.resolve())
