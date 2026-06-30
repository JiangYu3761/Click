# Sentence Reader Library UI Plan

Updated: 2026-06-30

## Decision

Sentence Reader Library V2 uses a single-system, reading-first main interface:

- The home page is a reading product surface, not a system management panel.
- The first screen prioritizes `继续阅读`, recent books, and recent knowledge assets.
- Book cards are real entry points: clicking the cover/card opens the current book.
- Book-card hover must not reveal high-priority management actions. Secondary actions such as 收藏, 单词, and 详情 live in a low-priority row under the card content.
- Library removal is a management-mode action: click 管理, select one or more books, then use the batch bar. A single selected book is the single-book path; the details drawer only offers 选择管理.
- On macOS, the embedded Library/Vocabulary WebView must leave the transparent titlebar row to a native draggable strip, so the red/yellow/green control area remains usable for moving the window.
- The Library dashboard must recover owned EPUB copies already stored under app support, so a missing PostgreSQL index does not make previously imported books disappear.
- The Mac Library WebView owns EPUB import through a native macOS open panel; `导入 EPUB` must not silently fail.
- The top-left brand is the product name `Click` only, without placeholder icons or explanatory tagline copy.
- Technical and file-management details are moved into settings, details, or advanced disclosure.
- Mac reading always resolves through `sentence-reader://open-native?book_id=...` into the existing native sentence-level reader.
- iPad/browser reading keeps `/library` and `/lan/reader`.

This is not a Komga, Calibre, Kavita, Koodo, or Readest embedding. Those projects are references only.

## Current Entry Points

- App launch: the main window opens directly into `http://127.0.0.1:18180/library?surface=mac-app`.
- Mac App top bar `书库`: returns the same main window to the library home; it no longer opens a second library window.
- In the Mac App, the library UI does not own a second reading surface. Clicking `继续阅读` emits `sentence-reader://open-native?book_id=...`, and the App switches the same window into the original native sentence reader after resolving the EPUB path from `/api/library/dashboard`.
- If Reader API cannot start, the old native AppKit book table remains as a fallback only.
- iPad on the same Wi-Fi: open `http://<mac-lan-ip>:18180/library`.
- Direct browser/iPad reading remains available at `http://<mac-lan-ip>:18180/lan/reader`.

## Data Contract

The product library page reads:

- `GET /api/library/dashboard`
- `GET /api/library/books/{book_id}/cover`
- `POST /api/library/import`
- `POST /api/library/books/{book_id}/hide`
- `POST /api/library/books/{book_id}/reveal`

`GET /api/library/dashboard` returns:

- book list
- current/recent book
- reading progress
- note count
- red highlight count
- audio note count
- cover URL and cover kind
- reading state: 未开始 / 在读 / 已读 / 搁置
- recent notes and red highlights
- internal EPUB path status
- file existence status
- recent activity time

## Persistence

Existing durable data remains in PostgreSQL:

- `reader.books`
- `reader.book_files`
- `reader.reading_positions`
- `reader.annotations`
- `reader.audio_notes`
- `reader.exports`
- `reader.sync_events`

The new non-destructive UI state is stored in:

- `reader.library_state`

`reader.library_state.hidden=true` only hides a book from the product library list. It does not delete:

- EPUB files
- reading positions
- notes
- red highlights
- audio notes
- PostgreSQL book records

## Library V2 UI Shape

The `/library` page provides:

- left navigation: 首页, 书库, 笔记, 红标, 设置
- top controls: global search, refresh, import
- home: large `继续阅读` hero, recent reading rail, recent notes/red highlights
- library: cover wall, reading state, progress, note/red counts, low-priority card secondary actions, explicit management mode, and batch actions
- notes: true note center, not just a book filter
- red: true highlight/excerpt center, not just a book filter
- settings: readable service/iPad/import status
- details drawer: cover, progress, open, note/red shortcuts, reveal, export, choose-for-management, and advanced file details

The Mac App must not use `/lan/reader` as its final reading surface. `/lan/reader` is the same-LAN browser/iPad surface. The library UI is only a management shell on Mac; the original native reader owns the Mac reading experience so the same book does not render differently depending on whether the user clicked `打开` or `书库 -> 继续阅读`.

The Mac reading chrome is intentionally simplified: `书库`, `目录`, `笔记`, `设置`, and `更多` are the only visible reader buttons. Less frequent actions such as import, switch book, export, Hermes sync, Cognitive OS, runtime environment, and iPad address live under `更多`.

## Boundaries

Do not add these to this UI phase:

- cloud sync
- account system
- Calibre database adoption
- direct Komga/Kavita embedding
- reader engine rewrite
- paid service calls
- destructive delete

## Acceptance

The library UI is accepted when these pass:

- `python3 scripts/reader_api_static_smoke.py`
- `.venv-reader-api/bin/python scripts/sentence_reader_library_ui_static_smoke.py`
- `.venv-reader-api/bin/python scripts/sentence_reader_library_v2_smoke.py`
- `python3 scripts/sentence_reader_product_static_smoke.py`
- `./scripts/v1_acceptance.sh`
- `./scripts/v21_ipad_lan_acceptance.sh`
- Swift compile
- package build
- live product readiness smoke
