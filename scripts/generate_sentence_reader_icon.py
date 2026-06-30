#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICONSET = ASSETS / "SentenceReader.iconset"
ICNS = ASSETS / "SentenceReader.icns"

SWIFT_SOURCE = r'''
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else {
    fputs("usage: IconMaker <size> <output>\n", stderr)
    exit(2)
}
let size = Int(args[1])!
let output = URL(fileURLWithPath: args[2])
let canvas = CGFloat(size)
let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: size,
    pixelsHigh: size,
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: 0,
    bitsPerPixel: 0
)!

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
NSColor.clear.setFill()
NSRect(x: 0, y: 0, width: canvas, height: canvas).fill()

let radius = canvas * 0.205
let background = NSBezierPath(roundedRect: NSRect(x: canvas * 0.055, y: canvas * 0.055, width: canvas * 0.89, height: canvas * 0.89), xRadius: radius, yRadius: radius)
let gradient = NSGradient(colors: [
    NSColor(calibratedRed: 0.08, green: 0.10, blue: 0.07, alpha: 1.0),
    NSColor(calibratedRed: 0.01, green: 0.08, blue: 0.07, alpha: 1.0)
])!
gradient.draw(in: background, angle: 90)

let bookShadow = NSBezierPath(roundedRect: NSRect(x: canvas * 0.20, y: canvas * 0.21, width: canvas * 0.60, height: canvas * 0.55), xRadius: canvas * 0.055, yRadius: canvas * 0.055)
NSColor(calibratedWhite: 0, alpha: 0.23).setFill()
bookShadow.fill()

let leftPage = NSBezierPath(roundedRect: NSRect(x: canvas * 0.18, y: canvas * 0.25, width: canvas * 0.32, height: canvas * 0.52), xRadius: canvas * 0.045, yRadius: canvas * 0.045)
NSColor(calibratedRed: 0.94, green: 0.95, blue: 0.90, alpha: 1).setFill()
leftPage.fill()

let rightPage = NSBezierPath(roundedRect: NSRect(x: canvas * 0.50, y: canvas * 0.25, width: canvas * 0.32, height: canvas * 0.52), xRadius: canvas * 0.045, yRadius: canvas * 0.045)
NSColor(calibratedRed: 0.99, green: 0.98, blue: 0.93, alpha: 1).setFill()
rightPage.fill()

NSColor(calibratedRed: 0.15, green: 0.18, blue: 0.18, alpha: 0.27).setStroke()
let spine = NSBezierPath()
spine.move(to: NSPoint(x: canvas * 0.50, y: canvas * 0.26))
spine.line(to: NSPoint(x: canvas * 0.50, y: canvas * 0.76))
spine.lineWidth = max(1, canvas * 0.012)
spine.stroke()

NSColor(calibratedRed: 0.09, green: 0.36, blue: 0.42, alpha: 0.32).setStroke()
for offset in [0.34, 0.43, 0.52] {
    let line = NSBezierPath()
    line.move(to: NSPoint(x: canvas * 0.25, y: canvas * CGFloat(offset)))
    line.line(to: NSPoint(x: canvas * 0.43, y: canvas * CGFloat(offset + 0.015)))
    line.lineWidth = max(1, canvas * 0.009)
    line.stroke()
}
for offset in [0.36, 0.45, 0.54] {
    let line = NSBezierPath()
    line.move(to: NSPoint(x: canvas * 0.57, y: canvas * CGFloat(offset + 0.015)))
    line.line(to: NSPoint(x: canvas * 0.75, y: canvas * CGFloat(offset)))
    line.lineWidth = max(1, canvas * 0.009)
    line.stroke()
}

let bookmark = NSBezierPath()
bookmark.move(to: NSPoint(x: canvas * 0.63, y: canvas * 0.78))
bookmark.line(to: NSPoint(x: canvas * 0.74, y: canvas * 0.78))
bookmark.line(to: NSPoint(x: canvas * 0.74, y: canvas * 0.43))
bookmark.line(to: NSPoint(x: canvas * 0.685, y: canvas * 0.49))
bookmark.line(to: NSPoint(x: canvas * 0.63, y: canvas * 0.43))
bookmark.close()
NSColor(calibratedRed: 0.86, green: 0.18, blue: 0.16, alpha: 1).setFill()
bookmark.fill()

let glint = NSBezierPath(ovalIn: NSRect(x: canvas * 0.25, y: canvas * 0.66, width: canvas * 0.10, height: canvas * 0.035))
NSColor(calibratedWhite: 1, alpha: 0.30).setFill()
glint.fill()

let clickRing = NSBezierPath(ovalIn: NSRect(x: canvas * 0.62, y: canvas * 0.60, width: canvas * 0.22, height: canvas * 0.22))
NSColor(calibratedRed: 0.97, green: 0.75, blue: 0.30, alpha: 0.92).setStroke()
clickRing.lineWidth = max(1, canvas * 0.018)
clickRing.stroke()

let clickCore = NSBezierPath(ovalIn: NSRect(x: canvas * 0.705, y: canvas * 0.685, width: canvas * 0.052, height: canvas * 0.052))
NSColor(calibratedRed: 0.97, green: 0.75, blue: 0.30, alpha: 1).setFill()
clickCore.fill()

let badge = NSBezierPath(roundedRect: NSRect(x: canvas * 0.20, y: canvas * 0.15, width: canvas * 0.32, height: canvas * 0.23), xRadius: canvas * 0.055, yRadius: canvas * 0.055)
NSColor(calibratedRed: 0.03, green: 0.09, blue: 0.08, alpha: 0.90).setFill()
badge.fill()
NSColor(calibratedRed: 0.97, green: 0.75, blue: 0.30, alpha: 0.90).setStroke()
badge.lineWidth = max(1, canvas * 0.010)
badge.stroke()

let cAttrs: [NSAttributedString.Key: Any] = [
    .font: NSFont.systemFont(ofSize: canvas * 0.145, weight: .black),
    .foregroundColor: NSColor(calibratedRed: 0.98, green: 0.91, blue: 0.73, alpha: 1)
]
("C" as NSString).draw(in: NSRect(x: canvas * 0.295, y: canvas * 0.182, width: canvas * 0.16, height: canvas * 0.17), withAttributes: cAttrs)

let cursor = NSBezierPath()
cursor.move(to: NSPoint(x: canvas * 0.70, y: canvas * 0.26))
cursor.line(to: NSPoint(x: canvas * 0.70, y: canvas * 0.52))
cursor.line(to: NSPoint(x: canvas * 0.88, y: canvas * 0.35))
cursor.line(to: NSPoint(x: canvas * 0.78, y: canvas * 0.34))
cursor.line(to: NSPoint(x: canvas * 0.84, y: canvas * 0.20))
cursor.line(to: NSPoint(x: canvas * 0.78, y: canvas * 0.18))
cursor.line(to: NSPoint(x: canvas * 0.72, y: canvas * 0.32))
cursor.close()
NSColor(calibratedWhite: 1, alpha: 0.96).setFill()
cursor.fill()
NSColor(calibratedRed: 0.03, green: 0.08, blue: 0.08, alpha: 0.72).setStroke()
cursor.lineWidth = max(1, canvas * 0.010)
cursor.stroke()

NSGraphicsContext.restoreGraphicsState()

guard let data = rep.representation(using: .png, properties: [:]) else {
    fputs("png representation failed\n", stderr)
    exit(1)
}
try data.write(to: output)
'''


ICON_FILES = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Click .icns app icon.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if shutil.which("swiftc") is None or shutil.which("iconutil") is None:
        print("icon generation requires swiftc and iconutil")
        return 1

    ASSETS.mkdir(parents=True, exist_ok=True)
    if ICONSET.exists():
        shutil.rmtree(ICONSET)
    ICONSET.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="sentence-reader-icon.") as tmp:
        tmp_path = Path(tmp)
        swift_file = tmp_path / "IconMaker.swift"
        binary = tmp_path / "IconMaker"
        swift_file.write_text(SWIFT_SOURCE, encoding="utf-8")
        build = subprocess.run(
            ["swiftc", str(swift_file), "-o", str(binary), "-framework", "AppKit"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if build.returncode != 0:
            print(build.stdout)
            return build.returncode
        for name, size in ICON_FILES.items():
            output = ICONSET / name
            result = subprocess.run([str(binary), str(size), str(output)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if result.returncode != 0:
                print(result.stdout)
                return result.returncode

    if ICNS.exists():
        ICNS.unlink()
    iconutil = subprocess.run(["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if iconutil.returncode != 0:
        print(iconutil.stdout)
        return iconutil.returncode
    if not args.quiet:
        print(f"iconset={ICONSET}")
        print(f"icns={ICNS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
