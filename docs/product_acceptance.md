# Sentence Reader Product Acceptance

Updated: 2026-06-29

## Daily-use Product Boundary

Sentence Reader is accepted as a daily-use local reading product when these workflows work without manual database work:

- Open the packaged Mac app from the Dock or build folder.
- Open the app directly into the `书库` main interface, which loads `http://127.0.0.1:18180/library?surface=mac-app` in the main Mac window when Reader API is available.
- See a Library V2 reading-first home page: `继续阅读` is the first task, recent books appear below it, and recent notes/red highlights are visible as knowledge assets.
- Return from正文 to `书库` in the same main window; the app must not open a second library window for normal use.
- See all known books as a cover wall with progress, reading state, note count, and red-highlight count.
- Click a book cover/card to continue reading directly; management actions must live in the details drawer or batch controls.
- Import EPUBs, reveal the internal EPUB copy, export, and remove books from the library list without deleting notes or data.
- Use dedicated `笔记` and `红标` centers instead of treating them only as book filters.
- Search across book title, author, notes, and red-highlight text.
- Keep the stable library data contract available through `/api/library/dashboard`.
- Continue reading from the Mac App `书库` into the original native sentence reader through `sentence-reader://open-native?book_id=...`, not the iPad/LAN web reader, so direct App opening and library opening render the same book through the same Mac reading surface.
- Keep正文 controls readable and grouped: visible reader chrome is limited to `书库`, `目录`, `笔记`, `设置`, and `更多`; secondary actions belong under `更多`.
- Import EPUB files into Sentence Reader's owned app-support library so the original source file can be deleted or moved after import.
- Read EPUB in a black, Microsoft YaHei reading surface with compact hidden chrome.
- Turn pages horizontally without cropped bottom text or trailing blank pages.
- Move across chapter edges without losing reading position.
- Mark whole sentences red, including multi-line selections.
- Add text notes and voice notes, then see the note again by clicking the sentence.
- Keep the interaction-router contract stable: sentence-level gestures win on sentence text; editing fields and controls still keep system behavior.
- Use single-click/single-tap on an English word for lookup, double-click/double-tap for sentence notes, context click/two-finger click on a sentence for whole-sentence red highlight, `Command+C` for copying selected text, and `Option` + double-click as a backup word-lookup path on pointer devices.
- English lookup must fall back to the general dictionary even when the current book has not generated a book-local vocabulary list.
- Common reading/business words such as `strategy`, `strategies`, `market`, `business`, and `the` must return a dictionary-backed result through `/books/{book_id}/lookup`.
- The local dictionary should include the imported ECDICT-compatible source, not only the compact seed list.
- Keep normal Mac app quitting behavior: `Command+Q` exits Sentence Reader.
- Keep `docs/interaction_contract.md` and `scripts/sentence_reader_interaction_contract_smoke.py` passing before changing any sentence/system gesture boundary.
- Persist books, reading position, highlights, notes, audio-note state, exports, and sync events through Reader API and PostgreSQL.
- Warm FunASR after app launch and use it for local voice-note transcription when available.
- Open the iPad LAN reader at `http://<mac-lan-ip>:18180/lan/reader` on the same Wi-Fi.
- Open the iPad LAN library at `http://<mac-lan-ip>:18180/library` on the same Wi-Fi.
- Example LAN URL format: `http://192.168.1.100:18180/lan/reader`.
- Use the iPad LAN reader with hidden目录 drawer, full-screen正文, swipe/page buttons, persisted highlights/notes/position, bottom sentence action bar, font-size settings, return-to-library control, and clear voice fallback.
- Keep iPad reading chrome compact: top controls must not look like a management toolbar, sentence actions should float only after selection, and hidden controls must not leave a large unused bottom area under the last line.

## Hard Checks

The product-grade check is not a single manual glance. It requires:

- `./scripts/v1_acceptance.sh`
- `./scripts/v21_ipad_lan_acceptance.sh`
- `.venv-reader-api/bin/python -m pytest tests/test_reader_api_mock.py`
- `.venv-reader-api/bin/python -m compileall reader_api scripts tests`
- `swiftc Probe/NativeSentenceReader/SentenceReaderNative.swift -o /tmp/SentenceReaderNativeProductCheck -framework Cocoa -framework WebKit -framework AVFoundation -framework Speech`
- `python3 scripts/package_sentence_reader_app.py`
- `python3 scripts/sentence_reader_import_ownership_static_smoke.py`
- `python3 scripts/sentence_reader_interaction_contract_smoke.py`
- `python3 scripts/sentence_reader_vocab_lookup_static_smoke.py`
- `.venv-reader-api/bin/python scripts/sentence_reader_library_ui_static_smoke.py`
- `.venv-reader-api/bin/python scripts/sentence_reader_library_v2_smoke.py`
- `python3 scripts/probe_readium_publication_open.py --timeout 300` must use the project fixture when the original Desktop EPUB is absent.
- `python3 scripts/check_native_reader.py` must include the `书库` window and non-destructive library-remove markers.
- `python3 scripts/sentence_reader_product_readiness_smoke.py` after the live LAN service is running

## Current Product Decision

The current version is product-grade for local EPUB reading on this Mac and trusted same-LAN iPad browser reading, with a functional native book library manager.

It is not yet a public-network, multi-device account, signed installer, native iPad product, or polished visual bookshelf.

Latest verification on 2026-06-25 repeated the hard checks and live readiness smoke without finding a new code-level blocker. This means the right stop condition is to keep the current product boundary stable instead of adding new feature scope.

Repeat verification on 2026-06-25 13:27 CST passed `v1_acceptance.sh`, `v21_ipad_lan_acceptance.sh`, Reader API pytest, Python compileall, Swift compile, packaged app build, and live LAN/FunASR readiness checks. No functional source or PostgreSQL schema change was required in this pass.

Repeat verification on 2026-06-26 added the native `书库` management interface and passed `v1_acceptance.sh`, `v21_ipad_lan_acceptance.sh`, Swift compile, package build, product static smoke, library live smoke, and live product readiness smoke. Current iPad URLs during verification: library `http://192.168.1.81:18180/library`, direct reader `http://192.168.1.81:18180/lan/reader`.

The Library V2 UI adds a reading-first home page, cover endpoint, direct book-card opening, details drawer, note center, red-highlight center, batch actions, and iPad `/library` access. It remains one Sentence Reader system and does not introduce a second reader.

2026-06-26 iPad touch refinement added bottom sentence actions, `Aa` reading settings, long-press red highlight, and `书库` return from `/lan/reader` to `/library`. This fixes the product problem where sentence-level operations were too far away in the top toolbar and the reader had no obvious route back to the main interface.

Repeat verification after the iPad touch refinement passed `v1_acceptance.sh`, `v21_ipad_lan_acceptance.sh`, Reader API pytest, Python compileall, Swift compile, package build, iPad static/API smoke, Library V2 smoke, live product readiness smoke, and live `/library` + `/lan/reader` marker checks. Current verified iPad URLs: library `http://192.168.31.96:18180/library`, direct reader `http://192.168.31.96:18180/lan/reader`.

2026-06-26 compact-chrome refinement shortened the iPad toolbar, changed previous/next to arrow controls, compacted the bottom sentence action bar, and removed the permanent large bottom padding from正文. `v21_ipad_lan_acceptance.sh`, static/API smoke, live product readiness smoke, and live compact chrome marker checks passed after the change.

## Stop Condition

Stop this round when:

1. The code changes are limited to stability, persistence, iPad LAN, voice fallback, tests, and docs.
2. The hard checks pass.
3. The live Reader API has exactly one listener on port `18180`, bound to all interfaces.
4. FunASR health returns `{"ok": true}` on `127.0.0.1:18081`.
5. The native app opens directly to the `书库` main interface in the main window.
6. The native app exposes a real Library V2 interface through `/library`, not only a quick switch menu or fallback table.
7. The first screen has `继续阅读`, recent reading, and recent notes/red highlights; it must not present engineering architecture copy as user-facing content.
8. The native app uses `surface=mac-app` and intercepts `sentence-reader://open-native?book_id=...` clicks from its embedded `/library` surface, then opens the selected book in the original native reader in the same window; iPad/browser use `/lan/reader` directly.
9. The final report states the iPad URL and the remaining non-final limitations.
