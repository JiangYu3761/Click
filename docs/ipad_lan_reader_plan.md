# Sentence Reader iPad LAN Reader V1 Plan

Updated: 2026-06-26

## Direction

The right next step is a LAN Web Reader, not an iPad native app and not public cloud sync.

Reason:

- The Mac app already owns EPUB import, PostgreSQL records, annotations, and reading positions.
- iPad access should reuse Reader API and the same `reader` schema.
- A browser-based reader is the fastest way to test real iPad value without committing to a second native app.

## Product Boundary

V1 supports trusted same-LAN use only.

In scope:

- iPad opens a local URL served by Reader API.
- The page lists books known to `reader.books`.
- The page loads EPUB chapters from the original EPUB file.
- The page renders readable chapter HTML with a dark reading theme.
- The page renders as a full-screen paginated reader, not a permanent split layout.
- The page can turn pages with buttons, keyboard, and horizontal swipe, and only crosses chapters at page edges.
- The book/chapter navigator is hidden in a `目录` drawer by default.
- The page restores red highlights and note markers from Reader API.
- The page can create red highlights and notes through existing annotation endpoints.
- The page can create voice notes by recording/uploading audio to the Mac-side Reader API/FunASR path, with browser/file/manual fallbacks.
- The page can save reading position through existing position endpoint.
- Tapping a sentence opens a bottom sentence action bar for red highlight, note, voice note, copy, and cancel.
- Long-pressing a sentence toggles red highlight for fast touch reading.
- `Aa` opens reading settings for font size, line height, and side padding, persisted in browser local storage.
- `书库` returns to `/library` with the current book id.
- The Mac app exposes an `iPad` top-bar entry that shows LAN URLs and starts LAN mode when it owns the Reader API process.

Out of scope:

- public internet access
- account login
- iCloud sync
- iPad native app
- PDF parity
- WebSocket live sync
- a full Readium web engine
- guaranteed microphone access on every iPad browser without HTTPS/certificate work

## 2026-06-26 Touch Interaction Refinement

The touch reader should not copy the Mac gesture model exactly. Double-click and two-finger click are good desktop shortcuts, but they are poor primary iPad controls because they are easy to miss and force the user to reach for top chrome after selecting text.

The accepted iPad interaction is:

- tap sentence: focus it and show the bottom action bar
- tap a note-marked sentence: show the note preview above the bottom action bar
- long press sentence: quick red highlight toggle
- bottom action bar: `红标`, `笔记`, `语音`, `复制`, `取消`
- top toolbar: only navigation-level actions, `书库`, `目录`, `Aa`, `上一页`, `下一页`
- `Aa`: font size, line height, and side padding
- `书库`: return to the product library instead of trapping the user in the reader

2026-06-26 compact chrome refinement:

- The top toolbar is a compact reading strip, not a full control panel.
- `上一页` / `下一页` are shown as small arrow buttons because horizontal swipe is the primary page-turn interaction on iPad.
- The bottom sentence action bar is a compact floating pill.
- The reader no longer reserves a permanent large bottom padding for a hidden action bar; the final text line should use the bottom of the page more fully.

Acceptance:

- Selecting a sentence must not put long sentence text into the top status bar.
- Sentence actions must be reachable near the bottom thumb zone.
- The note preview and action bar must not overlap the top page navigation.
- Reading settings must survive page reload on the same iPad browser.
- Returning to `/library` must preserve the current `book_id` in the URL query when known.
- Default reading state must prioritize正文 area over buttons.
- Hidden or inactive controls must not reserve visible page space.

## File-Level Work

### `reader_api/app.py`

Adjust this file.

Work:

- Add EPUB helper functions using Python stdlib `zipfile` and `xml.etree.ElementTree`.
- Resolve OPF spine reading order directly from the EPUB file.
- Add LAN endpoints:
  - `GET /lan/reader`
  - `GET /lan/books`
  - `GET /lan/books/{book_id}/manifest`
  - `GET /lan/books/{book_id}/chapters/{chapter_index}`
  - `GET /lan/books/{book_id}/asset/{asset_path:path}`
  - `POST /lan/audio-notes/transcribe`
- Transform chapter image/link assets to local `/lan/books/.../asset/...` URLs.
- Extract only EPUB body content before injecting the chapter into the browser reader.
- Keep the LAN reader paginated with a hidden TOC drawer and no permanent chapter column.
- Keep existing JSON CRUD endpoints unchanged.
- Do not add a database migration.

Acceptance:

- `/lan/reader` returns HTML.
- `/lan/books` returns known books.
- `/lan/books/{book_id}/manifest` returns chapters from EPUB spine.
- `/lan/books/{book_id}/chapters/0` returns transformed chapter HTML.
- Asset path traversal is rejected.
- LAN page contains `turnPage`, `drawer-open`, `lan_reader_paginated`, and `startVoiceNote`.
- LAN voice endpoint stores audio under app support and records an `audio_notes` row even when FunASR is unavailable.
- Existing API tests still pass.

### `Probe/NativeSentenceReader/SentenceReaderNative.swift`

Adjust this file.

Work:

- Add top-bar `iPad` button.
- Add LAN-mode Reader API launcher path with `READER_API_HOST=0.0.0.0`.
- Show local and LAN URLs in a sheet.
- Copy the preferred iPad URL to pasteboard.
- Preserve existing Reader API local mode and existing UI.

Acceptance:

- Swift compiles.
- Existing top-bar controls remain.
- `iPad` entry is visible.
- The dialog shows `http://<local-ip>:18180/lan/reader`.

### `scripts/reader_api_static_smoke.py`

Adjust this file.

Work:

- Add static endpoint markers for LAN reader routes.

Acceptance:

- Reader API static smoke fails if LAN routes are removed.

### `scripts/sentence_reader_ipad_lan_static_smoke.py`

Add this file.

Work:

- Check LAN endpoint, EPUB helper, Swift iPad button, LAN host env, package markers, and docs.

Acceptance:

- Prints `ipad lan static PASS`.

### `scripts/reader_api_ipad_lan_smoke.py`

Add this file.

Work:

- Use FastAPI `TestClient` and monkeypatched DB connection to exercise:
  - `/lan/reader`
  - `/lan/books`
  - `/lan/books/{book_id}/manifest`
  - `/lan/books/{book_id}/chapters/0`
  - asset traversal rejection
- Build a temporary tiny EPUB in the smoke test.

Acceptance:

- Prints `reader api ipad lan smoke PASS`.

### `scripts/v21_ipad_lan_acceptance.sh`

Add this file.

Work:

- Run V2.0S gate.
- Run LAN static smoke.
- Run LAN API smoke.
- Compile Python.
- Compile Swift.
- Package app.

Acceptance:

- Prints `V2.1 iPad LAN reader acceptance PASS`.

### `docs/current_status.md`

Adjust this file.

Work:

- Record LAN Reader V1 status and validation.
- State clearly that this is same-LAN browser access, not external access.

Acceptance:

- Status doc tells the next operator what is implemented and what remains.

### `docs/product_roadmap.md`

Adjust this file.

Work:

- Add V2.1 LAN Reader stage after local annotation correctness.

Acceptance:

- Roadmap sequence is local reader stability -> same-LAN reader -> later portability/security hardening.

## Manual Acceptance

1. Open Sentence Reader on Mac.
2. Click `iPad`.
3. Ensure the dialog shows a URL like `http://192.168.x.x:18180/lan/reader`.
4. On iPad connected to the same Wi-Fi, open that URL in Safari.
5. Confirm `目录` opens/closes the book/chapter drawer and is not permanently visible.
6. Confirm the正文 fills the page, left/right swipe turns pages, and page edges cross chapters.
7. Confirm red highlight, notes, and position save are usable.
8. Confirm `语音` either records/uploads to Mac-side FunASR or gives a clear fallback path when iPad Safari blocks direct microphone access.
