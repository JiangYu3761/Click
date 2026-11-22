"""Build the signed Sparkle integration and produce GitHub Release assets."""
from pathlib import Path
import hashlib
import plistlib
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.10.1"
SHA256 = "1a856d2a9edb8e628de88121d7be04cf0e2167f8641650b78fca00b14244cf27"
REPO = "https://github.com/JiangYu3761/Click"
ACCOUNT = "ClickMacUpdates-" + REPO.split("/")[-2]
PLIST = {
    "SUFeedURL": REPO + "/releases/latest/download/appcast.xml",
    "SUPublicEDKey": "q6rV6664X4YBcTIiRNutYx1mBqfwFH/MoghJyPMZrJw=",
    "SURequireSignedFeed": True,
    "SUEnableAutomaticChecks": True,
    "SUAutomaticallyUpdate": True,
    "SUScheduledCheckInterval": 14400,
}


def prepare_sparkle(cache):
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"Sparkle-{VERSION}.tar.xz"
    if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        with tempfile.TemporaryDirectory(dir=cache) as temp:
            partial = Path(temp) / archive.name
            subprocess.run(["curl", "-fsSL", "--retry", "2", "-o", str(partial),
                            f"https://github.com/sparkle-project/Sparkle/releases/download/{VERSION}/{archive.name}"], check=True)
            if hashlib.sha256(partial.read_bytes()).hexdigest() != SHA256:
                raise ValueError("Sparkle archive checksum mismatch")
            partial.replace(archive)
    dest = cache / VERSION
    dest.mkdir(exist_ok=True)
    subprocess.run(["tar", "-xf", str(archive), "-C", str(dest), "./Sparkle.framework", "./LICENSE", "./bin"], check=True)
    return dest


def swift_link_flags(sdk, obj):
    sources = ROOT / "Probe/NativeSentenceReader/Updates"
    subprocess.run(["xcrun", "clang", "-fobjc-arc", "-mmacosx-version-min=14.0", "-F", str(sdk),
                    "-c", str(sources / "ClickUpdates.m"), "-o", str(obj)], check=True)
    return ["-target", "arm64-apple-macos14.0", "-D", "CLICK_SPARKLE", "-import-objc-header",
            str(sources / "ClickUpdates.h"), str(obj), "-F", str(sdk), "-framework", "Sparkle",
            "-Xlinker", "-rpath", "-Xlinker", "@executable_path/../Frameworks"]


def embed_sparkle(app, sdk):
    folder = app / "Contents/Frameworks"
    folder.mkdir(exist_ok=True)
    subprocess.run(["ditto", str(sdk / "Sparkle.framework"), str(folder / "Sparkle.framework")], check=True)
    shutil.copy2(sdk / "LICENSE", app / "Contents/Resources/Sparkle-LICENSE")


def release_assets(app, output, sdk):
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    version, build = info["CFBundleShortVersionString"], info["CFBundleVersion"]
    subprocess.run(["codesign", "--verify", "--strict", str(app)], check=True)
    output.mkdir(parents=True, exist_ok=True)
    name = f"Click-{version}-macOS-arm64.zip"
    archive = output / name
    subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(archive)], check=True)
    args = [str(sdk / "bin/sign_update"), "--account", ACCOUNT]
    signature = subprocess.check_output([*args, "-p", str(archive)], text=True).strip()
    subprocess.run([*args, "--verify", str(archive), signature], check=True)
    ns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
    ET.register_namespace("sparkle", ns)
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Click for Mac"
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = "Click " + version
    for key, value in [("version", build), ("shortVersionString", version), ("minimumSystemVersion", info["LSMinimumSystemVersion"])]:
        ET.SubElement(item, "{%s}%s" % (ns, key)).text = value
    ET.SubElement(item, "enclosure", {"url": f"{REPO}/releases/download/mac-v{version}/{name}",
                                      "length": str(archive.stat().st_size), "type": "application/octet-stream",
                                      "{%s}edSignature" % ns: signature})
    feed = output / "appcast.xml"
    ET.ElementTree(rss).write(feed, encoding="utf-8", xml_declaration=True)
    subprocess.run([*args, str(feed)], check=True)
    subprocess.run([*args, "--verify", str(feed)], check=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    release_assets(args.app.resolve(), args.output.resolve(), prepare_sparkle(ROOT / "build/sparkle"))
