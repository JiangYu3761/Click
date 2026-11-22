"""Build the API 14 edition with the Android SDK, JDK 17, Clang and LLD."""
import argparse
import base64
import csv
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
PDFIUM = "com/github/barteksc/pdfium-android/1.9.0/pdfium-android-1.9.0.aar"
INPUTS = {
    "collections.jar": (["https://dl.google.com/dl/android/maven2/com/android/support/collections/28.0.0/collections-28.0.0.jar"],
                        "93c258c8a09f531a267653829742c0f8f6da0e348b11cb8655b0855628f2d4f0"),
    "pdfium.aar": (["https://repo.maven.apache.org/maven2/" + PDFIUM,
                    "https://maven.aliyun.com/repository/jcenter/" + PDFIUM],
                   "2992e86cce9ad5576e9c47a99cc2ba8cb75777016944ad30fbed3d7b8f6caf3f"),
    "android14.jar": (["https://repo.maven.apache.org/maven2/com/google/android/android/4.0.1.2/android-4.0.1.2.jar"],
                      "be93b1f39060c03ceefc936027e2e3a06e77b11049bd747dba2699a18db3c8fd"),
    "jni.h": (["https://android.googlesource.com/platform/libnativehelper/+/aef2939781fc0b57b4477df7160935cdf5697919/include_jni/jni.h?format=TEXT"],
              "2a3cea5e4306872202592406593f6465f07b848d75ed03ad07e2936479867f0a"),
    "ecdict.csv": (["https://raw.githubusercontent.com/skywind3000/ECDICT/39cfb9672c0906b63569e0453c2e6abfb9ab182a/ecdict.csv"],
                   "d1ecbdf9ee2b920afb6f430ca6b6bb9f559588cf0dff86e04bd255f9390843cc"),
}

def verify(path, digest):
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest

def dependencies(cache):
    cache.mkdir(parents=True, exist_ok=True)
    for name, (urls, digest) in INPUTS.items():
        dest = cache / name
        if verify(dest, digest):
            continue
        with tempfile.TemporaryDirectory(dir=cache) as folder:
            tmp = Path(folder) / name
            for url in urls:
                if subprocess.run(["curl", "-fsSL", "--retry", "2", "-o", tmp, url]).returncode:
                    continue
                if name == "jni.h":
                    tmp.write_bytes(base64.b64decode(tmp.read_bytes()))
                if verify(tmp, digest):
                    tmp.replace(dest)
                    break
            else:
                raise ValueError("Unable to verify " + name)

def lexicon(source, dest):
    with sqlite3.connect(dest) as db, source.open(encoding="utf-8-sig", newline="") as stream:
        db.execute("CREATE TABLE words(word TEXT PRIMARY KEY, ipa TEXT, zh TEXT)")
        # Include common and curriculum words while keeping the dictionary small for old phones.
        for entry in csv.DictReader(stream):
            if not any(entry[k].strip("0 ") for k in ("frq", "bnc", "oxford", "collins", "tag")):
                continue
            word = entry["word"].lower()
            if len(word) > 70 or not entry["translation"]:
                continue
            db.execute("INSERT OR IGNORE INTO words VALUES(?,?,?)",
                       (word, entry["phonetic"], entry["translation"].replace(r"\n", "\n")))
        print("Offline dictionary entries:", db.execute("SELECT count(*) FROM words").fetchone()[0])

def build(args, temp):
    sdk = Path(os.environ.get("ANDROID_HOME", Path.home() / "Library/Android/sdk"))
    tools = sdk / "build-tools/35.0.0"
    platform = sdk / "platforms/android-35/android.jar"
    java = Path(os.environ["JAVA_HOME"]) / "bin"
    cache = args.cache.resolve()
    dependencies(cache)
    def run(*cmd):
        subprocess.run([str(x) for x in cmd], check=True)
    classes, dex, assets = temp/"classes", temp/"dex", temp/"assets"
    for folder in (classes, dex, assets):
        folder.mkdir()
    shutil.copytree(ROOT/"licenses", assets/"licenses")
    apache = ROOT.parent/"ClickShell/app/src/main/assets/licenses/sherpa-onnx-Apache-2.0.txt"
    shutil.copyfile(apache, assets/"licenses/Apache-2.0.txt")
    lexicon(cache/"ecdict.csv", assets/"lexicon.db")
    with zipfile.ZipFile(cache/"pdfium.aar") as aar:
        aar.extract("classes.jar", temp)
        for name in aar.namelist():
            if name.startswith("jni/") and name.endswith(".so") and name.split("/")[1] in ("armeabi-v7a", "arm64-v8a", "x86", "x86_64"):
                aar.extract(name, temp)
    native = temp/"jni"
    targets = {"armeabi-v7a": "armv7a-linux-androideabi14", "arm64-v8a": "aarch64-linux-android21",
               "x86": "i686-linux-android14", "x86_64": "x86_64-linux-android21"}
    for abi, target in targets.items():
        lib = native/abi
        obj = temp/(abi + ".o")
        run("clang", "-target", target, "-ffreestanding", "-fPIC", "-Oz", "-I", cache, "-c",
            ROOT/"native/page_text.c", "-o", obj)
        run(tools/"lld-bin/lld", "-flavor", "gnu", "-shared", "-z", "noexecstack", "--hash-style=sysv",
            "-soname", "libclicktext.so", "--no-undefined", "-o", lib/"libclicktext.so", obj, lib/"libmodpdfium.so")
    shared = ROOT.parent/"ClickShell/app/src/main/java/com/click/shell/EpubOfflineIndexer.java"
    run(java/"javac", "-source", "8", "-target", "8", "-encoding", "UTF-8", "-classpath",
        os.pathsep.join(map(str, [cache/"android14.jar", temp/"classes.jar"])), "-d", classes, shared,
        *sorted((ROOT/"src").rglob("*.java")))
    run(java/"jar", "cf", temp/"classic.jar", "-C", classes, ".")
    run(tools/"d8", "--min-api", "14", "--lib", platform, "--output", dex, temp/"classic.jar", temp/"classes.jar", cache/"collections.jar")
    res = temp/"res/drawable-xxhdpi"
    res.mkdir(parents=True)
    shutil.copyfile(ROOT.parents[2]/"assets/SentenceReader.iconset/icon_128x128.png", res/"click_launcher.png")
    raw = temp/"raw.apk"
    run(tools/"aapt", "package", "-f", "-M", ROOT/"AndroidManifest.xml", "-I", platform, "-A", assets, "-S", res.parent, "-F", raw)
    with zipfile.ZipFile(raw, "a", zipfile.ZIP_DEFLATED) as apk:
        apk.write(dex/"classes.dex", "classes.dex")
        for lib in sorted(native.rglob("*.so")):
            apk.write(lib, "lib/"+str(lib.relative_to(native)))
    run(tools/"zipalign", "-f", "4", raw, temp/"aligned.apk")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    signed = temp/"signed.apk"
    run(tools/"apksigner", "sign", "--min-sdk-version", "14", "--v1-signing-enabled", "true",
        "--v2-signing-enabled", "true", "--ks", args.keystore, "--ks-key-alias", args.alias,
        "--ks-pass", "file:"+str(args.password_file), "--out", signed, temp/"aligned.apk")
    run(tools/"apksigner", "verify", "--min-sdk-version", "14", "--verbose", signed)
    shutil.copyfile(signed, args.out)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("cache", "out", "keystore", "password-file"):
        p.add_argument("--"+name, type=Path, required=True)
    p.add_argument("--alias", required=True)
    args = p.parse_args()
    with tempfile.TemporaryDirectory() as folder:
        build(args, Path(folder))
