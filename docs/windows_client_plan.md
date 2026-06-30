# Windows Client Plan

Updated: 2026-06-30

## Product Decision

Click / Sentence Reader is one local reading system with multiple client entries.

Windows should not become a second product and should not reimplement the reader from scratch. It should reuse:

- Reader API
- PostgreSQL reader schema
- EPUB import and owned-book storage rules
- sentence, note, red-highlight, reading-position, and vocabulary lookup logic
- Web library interface
- Web sentence-level reader

The Windows route is a platform packaging route, not a new reading engine.

## Current Platform Status

| Platform | Status | Boundary |
| --- | --- | --- |
| macOS App | Current primary usable client | Packaged local app with native sentence reader and Library V2 entry |
| iPad / browser | Current same-LAN usable client | Same-Wi-Fi browser access through `/library` and `/lan/reader` |
| Windows browser version | Planned first Windows step | Local Reader API plus browser-opened `http://localhost:18180/library` |
| Windows desktop version | Planned later shell | `Click.exe` with WebView2 or Tauri opening `/library` |

Windows is not currently described as completed.

## P1: Windows Browser Version

Goal: prove Windows can use the same local reading system without building a desktop shell first.

User flow:

1. Start local Reader API on Windows.
2. Open `http://localhost:18180/library` in a browser.
3. Import or open EPUBs through the Web library.
4. Read in the Web sentence-level reader.
5. Save notes, red highlights, reading position, and lookups through Reader API and PostgreSQL.

Acceptance:

- Reader API starts on Windows.
- PostgreSQL is available locally.
- `/library` opens in a Windows browser.
- A book can be opened and read.
- Add text notes, add voice notes when the browser path is available, red-highlight sentences, look up English words, and restore reading position.

## P2: Windows Desktop Shell

Goal: make the Windows experience feel like an app without rewriting the reader.

Design:

- Build `Click.exe`.
- Use WebView2 or Tauri as the desktop shell.
- On launch, start or connect to local Reader API.
- Load `/library` inside the app window.
- Keep reading in the same window.
- Use the same Web library and Web reader as P1.

Runtime directories should be user-level, for example:

```text
%APPDATA%\Click\
  Books\
  Runtime\
  Logs\
  Config\
```

P2 should not introduce a second database or a second reader engine.

## P3: Windows Installer

Goal: make Windows installation and removal understandable for normal users.

Installer should include:

- Reader API runtime
- app icon
- configuration directory
- log directory
- first-run diagnostic check
- uninstall logic

Shortcut design:

- Create a Start Menu shortcut by default.
- Offer a `Create desktop shortcut` option during installation.
- For ordinary users, the desktop shortcut option can be checked by default.
- Shortcut name: `Click`.
- Shortcut target: `Click.exe`.
- Shortcut icon: the reading-themed Click icon.
- Uninstall should remove the Start Menu shortcut and desktop shortcut if the installer created them.

## Windows Reading Interaction

Windows should follow computer-native expectations instead of copying macOS gestures.

| Action | Windows interaction |
| --- | --- |
| Add text note | Quick double-click a sentence |
| Add voice note | Use voice in the note window or sentence action bar |
| Red-highlight whole sentence | Select the sentence, then use the sentence action bar `Red` action |
| Look up English word | Single-click the English word |
| Copy text | Select text, then press `Ctrl+C` |
| Close popup or drawer | `Esc` |

Right-click should not be the main red-highlight path. It should remain available for normal copy/search/system expectations where appropriate.

## Voice Notes

Windows should not default to cloud speech recognition.

Priority:

1. Browser or WebView recording upload to local Reader API.
2. Optional local speech engine such as FunASR or another local runtime.
3. Manual text note fallback.

Online speech can be a future opt-in feature only. It is not part of this Windows plan.

## Non-Goals

- Do not rewrite a Windows native reader.
- Do not create a second database.
- Do not default to cloud speech services.
- Do not describe Windows as completed before P1/P2/P3 are implemented and tested.
- Do not fork the EPUB, sentence, note, red-highlight, or lookup data model.

## Next Implementation Boundary

The next real Windows implementation should start with P1:

1. Verify Reader API starts on Windows.
2. Verify PostgreSQL setup instructions are enough.
3. Verify `/library` and the Web reader work in a Windows browser.
4. Only after that, decide between WebView2 and Tauri for P2.
