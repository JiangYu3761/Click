# Click iPad Shell

This is the iPad P1 shell for Click. It is a SwiftUI + WKWebView client that connects to the Mac Click service and opens `/home` in a full-screen app surface.

The P1 workspace exposes the same three entries as Android:

- 阅读: `/library`, then the existing `/lan/reader`.
- 录音: `/recordings`, using the Mac `~/Documents/Recordings` total recording store.
- Hermes: `/hermes`, using the Mac-side Hermes runtime through the local workspace gateway.

It does not implement a second reader, local EPUB import, local PostgreSQL, offline reading, or cloud sync.

The shell stores the last Mac address, a stable local `device_id`, and an optional local access token. Device approval still happens on the Mac Click Local Hub through `/v1/mobile/access/*`; this is not a public account system.

Build check:

```bash
xcodebuild -project apps/ios/ClickShell/ClickShell.xcodeproj -scheme ClickShell -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build
```

Real-device installation still requires an Apple signing team and an attached iPad.
