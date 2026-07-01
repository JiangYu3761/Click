# Click Android Shell

Status: local P1 scaffold implemented and extended through the Mobile Workspace P1.1-P6 local acceptance route. Debug APK is a local build target; no signed release APK is published yet.

This Android shell uses a native Android Activity plus WebView to connect to the Mac Click service, check `/health`, open `/home`, and show the workspace with 阅读 / 录音 / Hermes.

The three entries route to:

- 阅读: `/library`, then the existing `/lan/reader` after a book is opened.
- 录音: `/recordings`, saving durable recording assets into the Mac `~/Documents/Recordings` total recording store.
- Hermes: `/hermes`, using the Mac-side Hermes runtime through the local workspace gateway.

It does not implement a second reader, Android-local EPUB import, Android-local PostgreSQL, offline reading, cloud sync, or a separate database.

Current user flow:

1. Open Click.
2. Enter the Mac LAN address, Reader / Click port, and Hermes port. The default Click port is `18180`; the default Hermes port shown for diagnostics is `8765`.
3. The app keeps a stable local `device_id`; after Mac-side approval, paste the local access token into the device token field.
4. The app checks `/health`.
5. On success it opens `/home` in a full-screen WebView.
6. The floating menu can return to 首页, 阅读, 录音, Hermes, refresh, or change the Mac address.

Mobile Workspace boundary:

- Device access uses the Click Local Hub `/v1/mobile/access/*` routes. This is local-only access control, not a public account system.
- `/recordings` lists durable recordings from `~/Documents/Recordings`, can edit title/category/tags, can hide without deleting files, and can trigger reprocess dry-run.
- `/hermes` supports text chat and temporary voice messages through VoiceInbox. These messages are not durable recording assets unless a later explicit save flow is added.
- edge-tts audio replies use the local Mac command when available; text replies still work without TTS.

Build boundary:

- This repo contains the Android project scaffold under `apps/android/ClickShell`.
- A debug APK can be produced after Java, Gradle, and Android SDK are available.
- The repo does not publish a signed release APK yet.
- Build with:

```bash
scripts/build_android_click_shell.sh
```

The build script copies the debug APK and its SHA256 file to the desktop Quark backup folder root for phone testing. It does not create nested backup folders.

P1.1 icon boundary:

- The Android launcher icon is `Click Focus`: a self-drawn dark Click icon with a book, click point, and light audio cue.
- The workspace entry icons are separate local resources for reading, recording, and Hermes.
- The local recording entry can use a Voice Memos-style microphone/waveform cue for private builds, but the resource is replaceable before public distribution.

Or import `apps/android/ClickShell` into Android Studio and run the `app` configuration. Android Studio can also generate a Gradle wrapper later if we want this project to build with `./gradlew`.
