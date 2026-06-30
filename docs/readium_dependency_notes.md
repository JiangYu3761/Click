# Readium Dependency Notes

## Initial Finding

Readium Swift Toolkit's public `Package.swift` currently declares:

- Swift tools version: 5.10
- Platforms: `iOS 15.0`
- Products: `ReadiumShared`, `ReadiumStreamer`, `ReadiumNavigator`, `ReadiumOPDS`, `ReadiumLCP`
- UIKit linker usage in `ReadiumShared`

This means Readium is high-quality and relevant, but a pure macOS SwiftPM command-line build is not guaranteed to work without a full Xcode/iOS toolchain or a Mac-specific integration layer.

## Local Environment Finding

Current machine state:

- Full Xcode is installed and active at `/Applications/Xcode.app/Contents/Developer`.
- `xcodebuild -version` reports Xcode 26.5.
- Swift reports Apple Swift 6.3.2.
- Xcode license is accepted.

Impact:

- The local sentence/annotation core can build and run with `swift run`.
- The SwiftUI app shell probe builds.
- Readium dependencies can now resolve.
- Readium's navigator package can build for Mac Catalyst.
- Readium Streamer can open the real Desktop EPUB fixture.
- A real visual navigator app target is still not complete.

## Dependency Resolve Attempt

Command attempted:

```bash
cd Probe/ReadiumDependencyProbe
swift package resolve
```

Earlier observed result:

- SwiftPM began fetching `https://github.com/readium/swift-toolkit.git`.
- The fetch did not complete within a reasonable interactive window and was interrupted.
- No Readium checkout was left under `.build/checkouts`.

This no longer represents the current state after full Xcode was installed and package caches were warmed.

## Updated Source Probe

A shallow clone succeeded at:

```text
/tmp/readium-swift-toolkit-shallow
```

Confirmed from the cloned source:

- `Package.swift` declares only `iOS 15.0`.
- `ReadiumShared` links `UIKit`.
- The Navigator SwiftUI guide uses `UIViewControllerRepresentable`.
- The Highlights guide says highlights are built on the Decoration API and persistence is the app's responsibility.
- `DecorableNavigator`, `Decoration`, `Locator`, pointer input, and secondary mouse button support exist in source.

Earlier attempted:

```bash
cd /tmp/readium-swift-toolkit-shallow
swift build --product ReadiumNavigator
```

Observed:

- SwiftPM started fetching third-party dependencies.
- The command did not reach compilation within the interactive window and was interrupted.
- Therefore, macOS CLI build success is not proven.

Updated Xcode/Catalyst probe:

```bash
python3 scripts/probe_readium_xcode_build.py --timeout 90
```

Result:

- SwiftPM dependencies resolved.
- Xcode package dependencies resolved.
- Report: `reports/readium_xcode_build_probe.json`

```bash
xcodebuild -project /tmp/readium-swift-toolkit-shallow/Playground/Playground.xcodeproj \
  -scheme ReadiumNavigator \
  -destination 'generic/platform=macOS,variant=Mac Catalyst' \
  -clonedSourcePackagesDirPath /tmp/sentence-reader-readium-xcode-packages build
```

Result:

- `ReadiumNavigator` built successfully for Mac Catalyst.

```bash
python3 scripts/probe_readium_catalyst_adapter.py --timeout 240
```

Result:

- Our `ReadiumCatalystAdapterProbe` built successfully for Mac Catalyst.
- The probe imports `ReadiumNavigator` and `ReadiumShared`.
- The probe references `EPUBNavigatorViewController`, `Locator`, `Decoration`, and `DecorableNavigator`.
- Report: `reports/readium_catalyst_adapter_probe.json`

```bash
python3 scripts/probe_readium_publication_open.py --timeout 300
```

Result:

- Readium Streamer opened the bundled smoke EPUB fixture.
- Display name in the app: `Click 示例书`
- EPUB metadata title: `Sentence Reader Smoke Book`
- Media type: `application/epub+zip`
- Reading order count: `1`
- Table of contents count: `1`
- Reports:
  - `reports/readium_publication_open_probe.json`
  - `reports/readium_publication_open_summary.json`

Current judgment:

Readium is now materially stronger than a conceptual candidate. The core navigator and our adapter compile under Mac Catalyst, and Readium Streamer can open a real Desktop EPUB fixture. The remaining risk is no longer dependency/build/opening feasibility; it is visual navigator integration:

- mapping click/two-finger tap to a stable locator/range,
- rendering and restoring whole-sentence decorations,
- preserving Mac-native ergonomics despite the UIKit/Catalyst base.

## Probe Strategy

Keep two separate probes:

1. `Probe/`
   - Our own sentence and annotation core.
   - Must build on this Mac with Command Line Tools only.

2. `Probe/ReadiumDependencyProbe/`
   - Dependency resolution and build probe for Readium.
   - Expected to identify whether current local tooling can build it.

## Decision Rule

- If the next navigator probe can render the Desktop EPUB and map interactions to Locator/Decoration, use Readium as the long-term EPUB engine.
- If Readium requires iOS-only assumptions that make Mac integration fragile, keep our annotation core and replace only the reading engine adapter.
