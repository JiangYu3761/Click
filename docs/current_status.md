# Sentence Reader Current Status

Updated: 2026-06-29

## Current Stage

V2.1 is now the daily-use product-grade boundary for this Mac: PostgreSQL data base, Swift data integration, notes loop, multi-book loop, export loop, voice-note persistence, reading stability, Hermes sync, packaged runtime, Hermes ingestion, reviewable Cognitive OS draft generation, explicit draft-to-formal-intake promotion, operator review queue generation, transaction-style active-pack rebuild operation, a safe Reader API/Swift surface, runtime/bootstrap/preflight paths, recognizable Dock-pinned app access, and trusted same-LAN iPad browser reading are all implemented and covered by acceptance checks.

日常可用产品级 in this project means local EPUB reading, source-independent EPUB imports, sentence-level annotations, notes, voice-note persistence, reading position restore, Reader API/PostgreSQL durability, packaged Mac app access, warm FunASR on this machine, and same-Wi-Fi iPad browser reading at the current Mac LAN URL, for example `http://<mac-lan-ip>:18180/lan/reader`.

Source-independent import rule: after Sentence Reader reports that an EPUB has been imported, the original EPUB path is no longer a runtime dependency. The app copies and verifies the book at `~/Library/Application Support/SentenceReader/Books/<book_hash>/book.epub`, normalizes saved book-library records to that owned path, and only registers the owned path with Reader API/PostgreSQL. The user may delete or move the original source file after import.

The product acceptance boundary is documented in `docs/product_acceptance.md`; the live service smoke is `scripts/sentence_reader_product_readiness_smoke.py`.

Latest verification on 2026-06-26: Library V2 changes the Mac app main interface from a management-panel style book list into a reading-first product home. The app still opens `http://127.0.0.1:18180/library?surface=mac-app` in the main window, but the visible first task is now `继续阅读`, followed by recent books and recent notes/red highlights. Book cards use real EPUB cover extraction when possible and generated book covers otherwise. Clicking a cover/card opens the selected book through `sentence-reader://open-native?book_id=...` into the original native sentence reader; iPad/browser access still uses `/lan/reader`. Notes and red highlights now have dedicated centers, while file paths and advanced status are moved into the details drawer or settings. The reader chrome remains simplified to `书库`, `目录`, `笔记`, `设置`, and `更多`.

Latest iPad LAN touch verification on 2026-06-26: `/lan/reader` now uses a touch-first interaction model. Tap sentence opens a bottom sentence action bar; long press toggles red highlight; `Aa` controls font size, line height, and side padding; `书库` returns to `/library?book_id=...`. Validation passed `v1_acceptance.sh`, `v21_ipad_lan_acceptance.sh`, Reader API pytest, Python compileall, Swift compile, package build, iPad static/API smoke, Library V2 smoke, live product readiness smoke, and live `/library` + `/lan/reader` marker checks. Current verified LAN URLs: library `http://192.168.31.96:18180/library`, direct reader `http://192.168.31.96:18180/lan/reader`.

Latest iPad compact-chrome refinement on 2026-06-26: `/lan/reader` now reduces visible control space again. The top toolbar is shorter, previous/next controls are arrow buttons, the bottom sentence action bar is a compact floating pill, and正文 no longer permanently reserves a large 96px bottom padding for hidden controls. `v21_ipad_lan_acceptance.sh`, static/API smoke, live product readiness smoke, and live compact chrome marker checks passed after the change. Current verified direct reader URL: `http://192.168.31.96:18180/lan/reader`.

Latest Mac reader notes-rail refinement on 2026-06-27: the native Mac reading surface now opens with the notes rail collapsed by default. The notes rail starts below the reader header and ends above the footer when opened, so its `收起笔记` control is not covered by the main reader buttons. Validation passed Swift compile, immersive chrome static smoke, product static smoke, packaging, and `v18_reading_stability_acceptance.sh`.

Latest Mac selection/pagination refinement on 2026-06-29: the selection/system boundary is now explicit. `Command+C` and non-sentence context menus remain the copy path for active text selection, but context click/two-finger click on `.sr-sentence` is reserved for Sentence Reader whole-sentence red highlight. Native pagination now aligns offsets to device pixels and adds a small left sliver guard on non-first pages to reduce previous-page column remnants after repeated page turns. Validation passed Swift compile, reader stability static smoke, annotation core V2 static smoke, product static smoke, packaging, and `v18_reading_stability_acceptance.sh`.

Latest interaction-router refinement on 2026-06-29: Mac native reader and iPad LAN reader now use a shared `SentenceReaderInteractionRouter` contract, documented in `docs/interaction_contract.md` and locked by `scripts/sentence_reader_interaction_contract_smoke.py`. In plain sentence-reading state, Sentence Reader actions have priority: double-click/double-tap opens the sentence note flow, context click/two-finger click on a sentence toggles whole-sentence red highlight, and tap/click focuses the sentence. Clicking or tapping an English word now triggers lookup after a short delay; a real double-click/double-tap cancels that pending lookup and opens the note flow. Editing fields and controls still yield to system behavior. Active text selection can still be copied with `Command+C` or a non-sentence context menu, but context click on a sentence remains a Sentence Reader red-highlight command because that gesture is the app's core annotation shortcut. `Option` + double-click remains a backup lookup path on pointer devices, and the native app now installs a standard application menu plus a key monitor so `Command+Q` quits Sentence Reader.

Latest vocabulary lookup repair on 2026-06-29: English click/tap lookup no longer depends only on prebuilt book-local vocabulary. If the current book has no `reader.book_vocab_items` entry for the clicked word, Reader API now falls back to `reader.dictionary_entries`, writes a safe dictionary-backed candidate into the current book vocabulary, and then returns a normal vocab item so review/known/edit actions still work. A compact general/business seed dictionary was added in `migrations/reader/005_general_dictionary_seed.sql`; larger ECDICT-style imports remain available through `scripts/sentence_reader_import_ecdict.py` when a CSV source is provided.

Repeat verification on 2026-06-25 13:27 CST passed the hard product checks again: `v1_acceptance.sh`, `v21_ipad_lan_acceptance.sh`, Reader API pytest, Python compileall, Swift compile, app packaging, and live LAN/FunASR readiness. No functional source or PostgreSQL schema change was required.

The current product boundary is intentionally strict:

- the app can view the review queue
- the app can run an operator dry-run
- the app can open a single draft detail report when one exists
- the app can open a Cognitive OS dashboard report before approval
- the app can show a native Cognitive OS dashboard table with status filtering
- the native dashboard can open the Markdown dashboard and selected draft source, but cannot approve drafts
- the API can preflight a selected draft without writing formal intakes
- the API can approve exactly one selected draft only after a matching `APPROVE <candidate_intake_id>` confirmation
- the App can surface approval only for `ready_to_approve` items and requires manual confirmation text before calling approval
- the dashboard must show approval history, quality-gate result, and rollback path instead of hiding mutation consequences
- the app cannot silently approve drafts or mutate active packs
- formal promotion and active-pack rebuild still require the explicit operator approval path

The existing V1 native reading shell already supports:

- bundled EPUB opening
- black reading surface
- compact top bar
- `目录(26)` chapter menu for the current sample book
- horizontal page turn with book-like animation
- edge navigation into previous/next EPUB spine item
- image containment
- reading position memory using `UserDefaults`
- double-click note editor
- note-editor voice input with local FunASR fallback to system speech recognition
- Reader API connection bootstrap
- Reader API-backed reading position save/restore
- Reader API-backed red highlight save/restore
- Reader API-backed note save
- V1.3 hard acceptance script: `scripts/v13_swift_data_acceptance.sh`
- right-side current-book notes rail
- notes search and type filter
- note edit/delete actions
- double-click note to jump back to its sentence
- V1.4 hard acceptance script: `scripts/v14_notes_acceptance.sh`
- open/import EPUB from disk
- local book library stored under `~/Library/Application Support/SentenceReader/Books`
- top-bar book switcher
- per-book Reader API records via `reader.books` and `reader.book_files`
- per-book reading-position fallback keys
- V1.5 hard acceptance script: `scripts/v15_multibook_acceptance.sh`
- top-bar export action for the current book
- Reader API-generated Markdown and JSON annotation exports
- export records persisted through `reader.exports`
- V1.6 hard acceptance script: `scripts/v16_export_acceptance.sh`
- persistent voice-note audio files under `~/Library/Application Support/SentenceReader/AudioNotes`
- Reader API audio-note lifecycle through `reader.audio_notes`
- voice-note pending/transcribed/failed status tracking
- voice-note annotation binding after the note is saved
- FunASR warm service: the App starts `funasr_worker.py --server` in the background after launch, prefers local `/transcribe`, and falls back to the old one-shot worker path when unavailable
- V1.7 hard acceptance script: `scripts/v17_voice_acceptance.sh`
- persistent reading settings through `SentenceReader.readerSettings.v1`
- top-bar `设置` menu for font size, line height, margin, theme, and reset
- WebView CSS-variable bridge through `__sentenceReaderApplySettings`
- dark and warm reading themes
- pagination hotfix: the WebView page surface now uses the full viewport height, allows paragraphs to flow across page breaks, and computes page count from measured content width to avoid trailing blank pages
- immersive chrome hotfix: the top command bar and bottom status bar are hidden by default, the WebView and notes rail use the full window height, and moving the mouse to the top/bottom edge temporarily reveals the controls
- Annotation Core V2 hotfix: drag/multi-line selection plus right-click/two-finger tap can batch-mark covered sentences, note markers restore into the page, single-clicking a note-marked sentence previews the saved note, and colon/semicolon are no longer treated as hard sentence boundaries
- Annotation Core V2 file-level plan: `docs/annotation_core_v2_plan.md`
- Annotation Core V2 smoke: `scripts/sentence_reader_annotation_core_v2_static_smoke.py`
- V1.8 hard acceptance script: `scripts/v18_reading_stability_acceptance.sh`
- top-bar `同步` action for the current book
- Reader API-generated Hermes/Cognitive OS sync payloads using schema `sentence_reader.hermes_sync.v1`
- sync payload files under `~/Library/Application Support/SentenceReader/HermesSync`
- pending sync attempts persisted through `reader.sync_events`
- V1.9 hard acceptance script: `scripts/v19_hermes_sync_acceptance.sh`
- bundled `ReaderRuntime` resources inside `build/Sentence Reader.app`
- Reader API startup script discovery from bundled runtime first, development path second
- product diagnostics report generation
- non-destructive PostgreSQL backup artifact generation
- restore verification without writing back to PostgreSQL
- V2.0A hard acceptance script: `scripts/v20_product_packaging_acceptance.sh`
- bundled `.venv-reader-api` inside `build/Sentence Reader.app/Contents/Resources/ReaderRuntime`
- bundled `migrations/reader/001_reader_schema.sql` inside ReaderRuntime
- package-local Reader API launch smoke test
- V2.0B hard acceptance script: `scripts/v20b_runtime_acceptance.sh`
- Hermes ingestion endpoint `POST /sync/hermes/ingest`
- command-line ingestion worker `scripts/sentence_reader_hermes_ingest.py`
- ReaderRuntime copy of the ingestion worker
- incoming asset handoff under `hermes_cognitive_os/incoming/sentence_reader`
- sync events marked `synced` after successful ingestion
- V2.0C hard acceptance script: `scripts/v20c_hermes_ingest_acceptance.sh`
- reviewable reader-intake drafts from incoming assets
- draft payload schema `sentence_reader.book_intake_draft.v1`
- draft quality gate schema `sentence_reader.reader_intake_quality_gate.v1`
- draft output under `hermes_cognitive_os/incoming/sentence_reader_drafts`
- V2.0D hard acceptance script: `scripts/v20d_intake_draft_acceptance.sh`
- explicit draft promotion worker `scripts/sentence_reader_promote_intake_draft.py`
- promotion report schema `sentence_reader.intake_draft_promotion_report.v1`
- promotion requires `--approved` before writing formal `hermes_cognitive_os/intakes/*.json`
- promotion can optionally rebuild active pack and run the Cognitive OS quality gate
- V2.0E hard acceptance script: `scripts/v20e_intake_promotion_acceptance.sh`
- review queue worker `scripts/sentence_reader_review_queue.py`
- review queue schema `sentence_reader.intake_review_queue.v1`
- queue classification: `ready_to_approve`, `needs_review`, `blocked`, `already_promoted`
- queue Markdown and JSON reports
- V2.0F hard acceptance script: `scripts/v20f_review_queue_acceptance.sh`
- active-pack operator `scripts/sentence_reader_active_pack_operator.py`
- active-pack operator report schema `sentence_reader.active_pack_operator_report.v1`
- rollback manifest schema `sentence_reader.active_pack_operator_rollback.v1`
- approved draft -> formal intake -> active pack rebuild -> optional Cognitive OS quality gate
- rollback-on-failure for files changed by the operator run
- V2.0G hard acceptance script: `scripts/v20g_active_pack_operator_acceptance.sh`
- Reader API cognitive queue endpoint `POST /cognitive/review-queue`
- Reader API operator dry-run endpoint `POST /cognitive/operator/dry-run`
- top-bar Swift `认知` action that checks queue state and opens the queue Markdown report
- V2.0H hard acceptance script: `scripts/v20h_cognitive_operator_entry_acceptance.sh`
- Reader API review item endpoint `POST /cognitive/review-item`
- Reader API selected preflight endpoint `POST /cognitive/operator/preflight`
- top-bar Swift `认知` action now opens a single-draft detail report when available
- V2.0I hard acceptance script: `scripts/v20i_review_detail_acceptance.sh`
- Reader API explicit approval endpoint `POST /cognitive/operator/approve`
- approval requires exact confirmation text `APPROVE <candidate_intake_id>`
- approval rejects blocked/not-ready drafts unless explicitly overridden where allowed
- V2.0J hard acceptance script: `scripts/v20j_explicit_approval_acceptance.sh`
- Swift `认知` flow exposes `批准入库...` only for `ready_to_approve` detail items
- Swift approval prompt requires exact `APPROVE <candidate_intake_id>` before calling the approval endpoint
- V2.0K hard acceptance script: `scripts/v20k_approval_ux_acceptance.sh`
- Reader API Cognitive dashboard endpoints `GET /cognitive/dashboard` and `POST /cognitive/dashboard`
- Cognitive dashboard schema `sentence_reader.cognitive_dashboard.v1`
- dashboard Markdown and JSON reports under `~/Library/Application Support/SentenceReader/CognitiveOps/dashboard`
- dashboard combines review queue counts, grouped draft status, approval history, quality-gate result, and rollback manifest paths
- Swift `认知` flow now offers `打开仪表盘` before opening detail or approving
- V2.0L hard acceptance script: `scripts/v20l_cognitive_dashboard_acceptance.sh`
- native Swift Cognitive dashboard window controller `CognitiveDashboardWindowController`
- native dashboard rows parse `CognitiveDashboardDraftRow` and `CognitiveDashboardHistoryRow`
- native status filter: `全部` / `可批准` / `待审` / `阻塞` / `已入库`
- native dashboard actions: `打开Markdown仪表盘`, `打开所选草稿`, `关闭`
- V2.0M hard acceptance script: `scripts/v20m_native_cognitive_dashboard_acceptance.sh`
- runtime portability report script `scripts/sentence_reader_runtime_portability.py`
- packaged `ReaderRuntime/runtime_manifest.json`
- product diagnostics includes runtime portability status
- runtime portability report files under `reports/sentence_reader_runtime_portability_report.json` and `.md`
- current machine is verified ready, while clean-Mac blockers are explicit instead of hidden
- V2.0N hard acceptance script: `scripts/v20n_runtime_portability_acceptance.sh`
- runtime bootstrap script `scripts/sentence_reader_runtime_bootstrap.py`
- runtime bootstrap smoke `scripts/sentence_reader_runtime_bootstrap_smoke.py`
- `run_reader_api.sh` can call bootstrap to select a working Python when bundled runtime Python is unavailable
- user-level Reader API venv bootstrap path under `~/Library/Application Support/SentenceReader/Runtime/.venv-reader-api`
- dependency installation remains explicit through `SENTENCE_READER_BOOTSTRAP_INSTALL_DEPS=1`
- product diagnostics includes runtime bootstrap status
- V2.0O hard acceptance script: `scripts/v20o_runtime_bootstrap_acceptance.sh`
- runtime config script `scripts/sentence_reader_runtime_config.py`
- first-run preflight script `scripts/sentence_reader_first_run_preflight.py`
- first-run preflight smoke `scripts/sentence_reader_first_run_preflight_smoke.py`
- Swift FunASR path resolution now checks UserDefaults, environment variables, runtime_config.json, then the legacy default
- product diagnostics includes first-run preflight status
- V2.0P hard acceptance script: `scripts/v20p_first_run_preflight_acceptance.sh`
- top-bar `环境` action opens a native runtime environment window
- runtime environment window can rerun first-run preflight from the App
- runtime environment window can save FunASR Python and worker paths to UserDefaults and `runtime_config.json`
- runtime environment window can open the generated preflight report
- V2.0Q hard acceptance script: `scripts/v20q_runtime_settings_acceptance.sh`
- first-run guide appears automatically only when `first_run_ready=false`
- runtime environment window now includes `首启修复引导`
- guide text explains PostgreSQL, Runtime Python/bootstrap, and FunASR recovery steps
- guide can be copied with `复制修复指引`
- config folder can be opened from the environment window
- V2.0R hard acceptance script: `scripts/v20r_first_run_guide_acceptance.sh`
- reading-related app icon generator: `scripts/generate_sentence_reader_icon.py`
- generated `.icns` asset: `assets/SentenceReader.icns`
- packaged App uses `CFBundleIconFile=SentenceReader`
- Dock pin helper: `scripts/pin_sentence_reader_to_dock.py`
- product identity smoke: `scripts/sentence_reader_identity_static_smoke.py`
- V2.0S hard acceptance script: `scripts/v20s_product_identity_acceptance.sh`
- current packaged app has been added to the macOS Dock as `Sentence Reader`
- V2.1 iPad LAN Reader: trusted same-LAN browser access through `GET /lan/reader`
- iPad LAN Reader can list books, open EPUB spine chapters, serve EPUB assets, save Reader API-backed red highlights, save notes, and save paginated reading position
- iPad LAN Reader hotfix: chapter/book lists are now hidden in a slide-out `目录` drawer instead of permanently occupying the reading page
- iPad LAN Reader hotfix: page turning now uses `turnPage` with button, keyboard, and horizontal touch-swipe support; page position is stored as `lan_reader_paginated`
- iPad LAN Reader hotfix: chapter HTML is reduced to body content before rendering, and the page uses full `100dvh` height plus measured column pagination to avoid cropped text and trailing blank pages
- iPad LAN Reader product-readiness hotfix: pagination now measures real sentence/image element rectangles through `measuredContentWidth`, reducing false blank pages from CSS column scroll width
- iPad LAN Reader note preview: clicking a note-marked sentence now opens a readable bottom note panel instead of only using the truncated status text
- iPad LAN Reader voice entry: `语音` now tries browser recording upload to Mac-side FunASR through `POST /lan/audio-notes/transcribe`, falls back to iPad audio file/capture upload, then falls back to browser speech/manual note where needed
- iPad LAN Reader touch interaction refinement: tapping a sentence now opens a bottom action bar for `红标` / `笔记` / `语音` / `复制` / `取消`; long-press toggles red highlight; top toolbar no longer carries sentence-level actions
- iPad LAN Reader reading settings: `Aa` opens font size, line-height, and side-padding controls persisted in browser local storage as `sentenceReaderLanSettings`
- iPad LAN Reader navigation refinement: `书库` returns to `/library?book_id=...`, so the iPad reader is no longer a dead-end page
- iPad LAN Reader live readiness smoke: `scripts/sentence_reader_product_readiness_smoke.py` checks exactly one live `18180` listener, verifies the LAN page is the new drawer/paginated/voice page, and checks FunASR `/health`
- V2.1 hard acceptance script: `scripts/v21_ipad_lan_acceptance.sh`

Still outside the current local-reader scope:

- public internet access, user accounts, HTTPS certificate management, WebSocket live sync, and a native iPad app are not implemented yet.
- iPad browser microphone behavior depends on Safari permissions and secure-origin rules; the product fallback is audio capture/upload plus manual note if browser recording is blocked.
- PDF annotation parity is not implemented yet.
- Annotation Core V2 does not change the PostgreSQL schema; multi-sentence locators are stored through existing annotation metadata/range locator fields.

## V1.2 Added This Round

- PostgreSQL migration file: `migrations/reader/001_reader_schema.sql`
- Reader API package skeleton: `reader_api/`
- Reader API dependency list: `requirements-reader-api.txt`
- static Reader API smoke test: `scripts/reader_api_static_smoke.py`
- mock Reader API CRUD pytest: `tests/test_reader_api_mock.py`
- PostgreSQL readiness checker: `scripts/reader_pg_status.py`
- PostgreSQL migration runner: `scripts/reader_pg_migrate.py`
- PostgreSQL CRUD smoke runner: `scripts/reader_pg_smoke.py`
- live Reader API + PostgreSQL smoke runner: `scripts/reader_api_live_smoke.py`
- V1.2 hard data acceptance: `scripts/v12_data_acceptance.sh`
- PostgreSQL setup notes: `docs/postgresql_setup.md`
- V1 acceptance now checks Reader API static contract, compiles Python files, and runs the Reader API mock pytest when dependencies are available.
- Project-local Python environment: `.venv-reader-api/`
- Local development ignore file: `.gitignore`

## Validation Completed This Round

- `scripts/v12_data_acceptance.sh`: passed.
- Postgres.app 2.9.5 / PostgreSQL 18.4 installed at `/Applications/Postgres.app`.
- PostgreSQL data directory: `~/Library/Application Support/SentenceReader/Postgres/data-18`.
- `jiangyu_os` database created.
- `reader` schema migration passed.
- direct PostgreSQL CRUD smoke passed.
- live Reader API + PostgreSQL smoke passed.
- `tests/test_reader_api_mock.py`: passed, 7 tests.
- `scripts/v1_acceptance.sh`: passed.
- Reader API static smoke: passed.
- Python compileall for `reader_api` and `scripts`: passed.
- Swift/readium V1 acceptance path: passed through `scripts/v1_acceptance.sh`.
- `scripts/reader_pg_status.py`: works and reports PostgreSQL/schema ready.
- `scripts/reader_api_http_smoke.py`: passed against a running HTTP Reader API.
- Swift native reader compile: passed after Reader API integration.
- `scripts/package_sentence_reader_app.py`: passed after Reader API integration.
- `scripts/v13_swift_data_acceptance.sh`: passed.
- `scripts/reader_api_notes_loop_smoke.py`: passed.
- `scripts/v14_notes_acceptance.sh`: passed.
- `scripts/reader_api_multibook_smoke.py`: added for V1.5.
- `scripts/v15_multibook_acceptance.sh`: passed.
- `scripts/reader_api_export_smoke.py`: passed.
- `scripts/v16_export_acceptance.sh`: passed.
- `scripts/reader_api_audio_notes_smoke.py`: passed.
- `scripts/v17_voice_acceptance.sh`: passed.
- `scripts/reader_stability_static_smoke.py`: passed.
- `scripts/v18_reading_stability_acceptance.sh`: passed.
- `scripts/reader_api_hermes_sync_smoke.py`: passed.
- `scripts/v19_hermes_sync_acceptance.sh`: passed.
- `scripts/sentence_reader_product_static_smoke.py`: passed.
- `scripts/sentence_reader_product_diagnostics.py`: passed.
- `scripts/sentence_reader_backup.py`: passed with `--skip-files` smoke backup.
- `scripts/sentence_reader_restore_verify.py`: passed.
- `scripts/v20_product_packaging_acceptance.sh`: passed.
- `scripts/reader_runtime_launch_smoke.py`: passed.
- `scripts/v20b_runtime_acceptance.sh`: passed.
- `scripts/reader_api_hermes_ingest_smoke.py`: passed.
- `scripts/v20c_hermes_ingest_acceptance.sh`: passed.
- `scripts/reader_intake_draft_smoke.py`: added for V2.0D.
- `scripts/reader_intake_draft_smoke.py`: passed.
- `scripts/v20d_intake_draft_acceptance.sh`: passed.
- Production Cognitive OS dry run: passed with `discovered_count=0`, meaning no real reader incoming assets exist yet.
- `scripts/reader_intake_promotion_smoke.py`: passed.
- `scripts/v20e_intake_promotion_acceptance.sh`: passed.
- Production Cognitive OS promotion dry run: passed with `draft_count=0` and `promoted_count=0`, meaning no real draft was promoted.
- `scripts/reader_review_queue_smoke.py`: passed.
- `scripts/v20f_review_queue_acceptance.sh`: passed.
- Production Cognitive OS review queue dry run: passed with `draft_count=0`, meaning no real draft is waiting for review yet.
- `scripts/reader_active_pack_operator_smoke.py`: passed.
- `scripts/v20g_active_pack_operator_acceptance.sh`: passed.
- Production Cognitive OS active-pack operator dry run: passed with `selected_count=0`, meaning no real active pack rebuild or promotion was performed.
- `scripts/reader_api_cognitive_operator_smoke.py`: passed.
- Swift native reader compile after adding the `认知` entry: passed.
- Reader API static smoke after adding cognitive endpoints: passed.
- Product static smoke after adding API/App cognitive markers: passed.
- `scripts/v20h_cognitive_operator_entry_acceptance.sh`: passed.
- `scripts/reader_api_cognitive_operator_smoke.py`: upgraded to cover one ready draft, review-item detail, selected preflight, and no formal-intake writes.
- Swift native reader compile after adding detail report opening: passed.
- Reader API static smoke after adding review-item/preflight endpoints: passed.
- Product static smoke after adding V2.0I API/App markers: passed.
- `scripts/v20i_review_detail_acceptance.sh`: passed.
- `scripts/reader_api_cognitive_operator_smoke.py`: upgraded to reject bad confirmation and approve one ready draft in a temporary Cognitive OS root.
- Swift native reader compile after V2.0J API changes: passed.
- Reader API static smoke after adding approve endpoint: passed.
- Product static smoke after adding V2.0J markers: passed.
- `scripts/v20j_explicit_approval_acceptance.sh`: passed.
- Swift native reader compile after adding V2.0K approval UX: passed.
- Product static smoke after adding V2.0K Swift markers: passed.
- `scripts/v20k_approval_ux_acceptance.sh`: passed.
- `scripts/reader_api_cognitive_operator_smoke.py`: upgraded to cover the Cognitive dashboard schema, Markdown report, approval history, and rollback visibility.
- Swift native reader compile after adding V2.0L dashboard UX: passed.
- Reader API static smoke after adding dashboard endpoints: passed.
- Product static smoke after adding V2.0L dashboard markers: passed.
- `scripts/v20l_cognitive_dashboard_acceptance.sh`: passed.
- `scripts/sentence_reader_native_cognitive_dashboard_smoke.py`: passed.
- Swift native reader compile after adding V2.0M native dashboard table: passed.
- Product static smoke after adding V2.0M native dashboard markers: passed.
- `scripts/v20m_native_cognitive_dashboard_acceptance.sh`: passed.
- `scripts/sentence_reader_runtime_portability.py`: passed with `current_machine_ready=True`.
- Runtime portability report currently says `clean_mac_ready=False` with blockers: `runtime_python_points_to_xcode`, `runtime_python_points_outside_ReaderRuntime`, `postgres_not_bundled`.
- Product diagnostics with runtime portability: passed.
- Packaged ReaderRuntime launch smoke after adding runtime manifest: passed.
- `scripts/v20n_runtime_portability_acceptance.sh`: passed.
- `scripts/sentence_reader_runtime_bootstrap_smoke.py`: passed.
- Runtime bootstrap report: passed with `startup_ready=True`.
- Product diagnostics with runtime bootstrap: passed.
- Packaged ReaderRuntime launch smoke after bootstrap integration: passed.
- `scripts/v20o_runtime_bootstrap_acceptance.sh`: passed.
- `scripts/v20p_first_run_preflight_acceptance.sh`: passed.
- `scripts/v20q_runtime_settings_acceptance.sh`: passed.
- `scripts/v20r_first_run_guide_acceptance.sh`: passed.
- `scripts/v20s_product_identity_acceptance.sh`: passed.
- `scripts/sentence_reader_annotation_core_v2_static_smoke.py`: passed.
- Swift native reader compile after Annotation Core V2: passed.
- Python compileall for `reader_api`, `scripts`, and `tests` after Annotation Core V2: passed.
- `scripts/v18_reading_stability_acceptance.sh`: passed after Annotation Core V2.
- `scripts/sentence_reader_identity_static_smoke.py`: passed after final package.
- Dock dry-run reports the current packaged app is already present.
- V2.1 iPad LAN Reader plan: `docs/ipad_lan_reader_plan.md`.
- Reader API now exposes same-LAN browser routes under `/lan/reader` and `/lan/books/...`.
- Swift top bar now has an `iPad` entry that shows/copies `http://<local-ip>:18180/lan/reader` and can launch Reader API in LAN mode when the App owns the API process.
- `scripts/sentence_reader_ipad_lan_static_smoke.py`: passed.
- `scripts/reader_api_ipad_lan_smoke.py`: passed with a temporary EPUB.
- Swift native reader compile after iPad LAN entry: passed.
- Product static smoke after iPad LAN entry: passed.
- `scripts/v21_ipad_lan_acceptance.sh`: passed.
- Current LAN test URL on this machine: `http://192.168.1.100:18180/lan/reader`.
- Live LAN API smoke: `http://127.0.0.1:18180/lan/reader` and `http://192.168.1.100:18180/lan/reader` both returned HTTP 200.
- Real default book LAN manifest smoke: returned schema `sentence_reader.lan_manifest.v1` with 50 chapters.

V2.1 current limitation:

- This is trusted same-LAN browser access only.
- It is not public internet access and has no account/login layer yet.
- Current live readiness requires exactly one Reader API process on `18180`, bound to all interfaces. If an old local-only process is found, stop it and restart the LAN service before considering iPad ready.

## Latest Recheck

The current shell sees PostgreSQL through Postgres.app:

```text
psql /Applications/Postgres.app/Contents/Versions/latest/bin/psql
postgres /Applications/Postgres.app/Contents/Versions/latest/bin/postgres
pg_ctl /Applications/Postgres.app/Contents/Versions/latest/bin/pg_ctl
initdb /Applications/Postgres.app/Contents/Versions/latest/bin/initdb
brew not found
docker not found
```

The project-local Reader API environment is ready:

```text
fastapi installed
uvicorn installed
psycopg installed
pytest installed
httpx installed
```

Reader API Python dependencies were installed into the project-local virtual environment:

```text
.venv-reader-api/
```

They are still not installed in the current system Python, by design:

```text
fastapi missing
uvicorn missing
psycopg missing
pytest missing
```

`scripts/v12_data_acceptance.sh` is now the hard gate for V1.2. It first checks PostgreSQL server readiness, then creates/migrates `jiangyu_os`, then verifies the `reader` schema and CRUD paths.

The V1.2 hard gate currently reaches this point:

```text
== V1.2 static/API contract ==
reader api static PASS
6 passed
== V1.2 PostgreSQL schema readiness ==
tcp ok=True host=localhost port=5432
database ok=True
```

## V1.5 Status

V1.5 adds the minimum product-grade multi-book loop:

- user-selected EPUB files are copied into app support storage; originals are not moved
- EPUB files are unpacked into an app-owned book directory
- imported books are deduplicated by a stable file hash
- the top bar exposes `打开` and `书籍` controls
- switching books reloads chapters, TOC, notes rail, red highlights, and reading position for that book
- API `/books` lists persisted books and latest file metadata
- API smoke verifies two books keep independent reading positions and annotations

V1.5 is intentionally not a bookshelf design. It is the data and workflow foundation for multi-book reading.

## V1.6 Status

V1.6 adds the minimum product-grade export loop:

- Reader API exposes `POST /books/{book_id}/export`
- exports include current-book notes and red highlights
- Markdown preserves book title, author, book hash, chapter title, source sentence, note text, locator, sentence index, and timestamps
- JSON companion uses schema `sentence_reader.annotations_export.v1`
- generated files are written under `~/Library/Application Support/SentenceReader/Exports` by default
- every Markdown/JSON output is recorded in `reader.exports`
- Swift App top bar exposes `导出` and calls the Reader API contract
- smoke test verifies files exist, contents include note/red source text, and export records exist

V1.6 is intentionally not cloud sync and not AI summary. It is the durable local export boundary.

## V1.7 Status

V1.7 adds the minimum product-grade voice-note persistence loop:

- recorded WAV files are stored in app support instead of temporary storage
- Swift creates a pending audio note before transcription
- successful FunASR or Apple Speech transcription updates the audio note to `transcribed`
- transcription failure updates the audio note to `failed`
- saved text notes bind the audio note to the resulting annotation when possible
- Reader API exposes `POST /audio-notes`, `PATCH /audio-notes/{audio_note_id}`, and `GET /books/{book_id}/audio-notes`
- the native App now warms a local FunASR server on launch using the configured FunASR Python/worker paths
- transcription first tries the warm local `/transcribe` endpoint, then safely falls back to the original subprocess worker and Apple Speech fallback
- the warm service writes logs under `~/Library/Application Support/SentenceReader/Logs/funasr_server.log` and is terminated when the App exits if the App started it
- smoke test verifies pending -> transcribed lifecycle, annotation binding, transcript persistence, and per-book listing

V1.7 now has a local warm FunASR service boundary. It is still not a separately installed system daemon; it runs while Sentence Reader is open and falls back cleanly when unavailable.

## V1.8 Status

V1.8 adds the minimum product-grade reading stability layer:

- reader settings are persisted in `UserDefaults` under `SentenceReader.readerSettings.v1`
- top-bar `设置` menu controls font size, line height, horizontal margins, dark theme, warm theme, and reset
- settings are sanitized to safe ranges before saving
- settings are injected into the WebView through `window.__sentenceReaderApplySettings`
- CSS variables drive font size, line height, margins, column width, column gap, background, text color, and focus color
- page layout reflows after settings change without touching annotations or reading position storage
- page layout now avoids self-reserved bottom space by using full viewport height and tight bottom padding
- pagination now measures actual sentence/image rects instead of trusting trailing CSS multi-column scroll width alone, reducing false blank pages during page turns
- paragraph/list/body text is allowed to cross page breaks so a long paragraph does not leave the lower part of a page empty
- top and bottom reader chrome is now immersive: hidden by default, revealed by edge mouse movement, and auto-hidden after a short delay
- the native title bar is transparent with hidden title text so the app avoids a double top-bar feeling
- static smoke checks still cover horizontal swipe threshold, inertia lock, vertical-wheel suppression, image containment, and chapter-edge bridge

V1.8 is not a full design-system pass. It stabilizes the reading controls that affect long sessions.

## V1.9 Status

V1.9 adds the minimum product-grade Hermes/Cognitive OS handoff boundary:

- Reader API exposes `POST /books/{book_id}/sync/hermes`
- Reader API exposes `GET /books/{book_id}/sync-events`
- sync payloads include book metadata, source sentences, note text, red highlights, locators, sentence indexes, and a cognitive contract
- sync payloads use schema `sentence_reader.hermes_sync.v1`
- sync payloads are written to `~/Library/Application Support/SentenceReader/HermesSync` by default
- every sync handoff writes a pending row to `reader.sync_events`
- Swift App top bar exposes `同步` and calls Reader API instead of calling Hermes directly
- smoke test verifies file generation, payload schema, annotation count, and sync-event persistence

V1.9 is not AI summary generation and not real Hermes ingestion. It is the clean local contract that lets Hermes/Cognitive OS consume reading assets later without coupling the Mac reading UI to model calls.

## V2.0A Status

V2.0A adds the first product-packaging foundation:

- `package_sentence_reader_app.py` now bundles `ReaderRuntime` into `build/Sentence Reader.app/Contents/Resources/ReaderRuntime`
- bundled runtime includes `reader_api`, `requirements-reader-api.txt`, Reader API startup/migration/status scripts, diagnostics, backup, and restore verification tools
- Swift Reader API startup now checks `ReaderRuntime/scripts/run_reader_api.sh` first and falls back to the development project script path
- `sentence_reader_product_diagnostics.py` writes a JSON report for PostgreSQL, Reader API, app bundle, ReaderRuntime, app-support storage, FunASR paths, and sync-event counts
- `sentence_reader_backup.py` creates a non-destructive backup artifact with `pg_dump --schema=reader` and file inventory
- `sentence_reader_restore_verify.py` validates a backup manifest without restoring or overwriting anything
- `v20_product_packaging_acceptance.sh` gates V1.9, product static contract, package output, diagnostics, backup, and restore verification

V2.0A is not the final installer and not a destructive restore tool. The app still needs a compatible local Python environment for Reader API dependencies. Full restore remains approval-gated because it can overwrite user data.

## V2.0B Status

V2.0B makes the Reader API runtime substantially more self-contained:

- `package_sentence_reader_app.py` now copies `.venv-reader-api` into `ReaderRuntime`
- symlinks are preserved when copying the venv so Xcode Python continues to load its runtime correctly
- `package_sentence_reader_app.py` now copies `migrations/reader/001_reader_schema.sql` into `ReaderRuntime`
- `run_reader_api.sh` prefers `ReaderRuntime/.venv-reader-api/bin/python`
- `reader_runtime_launch_smoke.py` starts `ReaderRuntime/scripts/run_reader_api.sh` from inside the packaged app on a temporary port and verifies `/health`
- product diagnostics now requires package-local runtime Python and core imports when `--require-package` is used

V2.0B is a real improvement over V2.0A: the packaged app no longer merely contains Reader API source code; it contains the verified Python dependency environment and can start the API from the package on this Mac.

V2.0B is still not a universal installer. The bundled venv points to this machine's Xcode Python, and PostgreSQL still depends on the local Postgres.app/tooling. A clean-Mac installer would need a more portable Python/PostgreSQL strategy.

## V2.0C Status

V2.0C closes the first real Hermes/Cognitive OS ingestion loop:

- Reader API exposes `POST /sync/hermes/ingest`
- ingestion can process all pending events or restrict to specific `sync_event_ids`
- source `sentence_reader.hermes_sync.v1` payloads are copied into `hermes_cognitive_os/incoming/sentence_reader`
- each copied asset gets a manifest using schema `sentence_reader.hermes_ingestion_manifest.v1`
- manifest policy states `active_pack_mutation=false` and `requires_human_or_pipeline_review=true`
- successful ingestion marks the original `reader.sync_events` row as `synced`
- missing or invalid payload files mark the event as `failed` and continue the batch
- command-line worker `sentence_reader_hermes_ingest.py` can trigger ingestion through Reader API
- packaged `ReaderRuntime` includes the ingestion worker

V2.0C is not automatic book-model promotion. It safely transfers reader evidence into Hermes Cognitive OS incoming assets. Turning those assets into long-term cognitive models should still go through the existing book intake and quality-gate pipeline.

## V2.0D Status

V2.0D closes the first safe incoming-to-intake-draft loop and has passed acceptance:

- `sentence_reader_intake_draft.py` scans `hermes_cognitive_os/incoming/sentence_reader/*.manifest.json`
- each manifest loads its paired `sentence_reader.hermes_sync.v1` payload
- the script writes reviewable drafts to `hermes_cognitive_os/incoming/sentence_reader_drafts`
- drafts use schema `sentence_reader.book_intake_draft.v1`
- each draft contains a conservative `book_intake_candidate` compatible with the Hermes book intake shape
- each draft includes a quality gate with conclusion: `review_ready`, `needs_review`, or `blocked`
- every draft keeps `promotion_allowed=false` and `active_pack_mutation=false`
- package runtime now includes `sentence_reader_intake_draft.py`
- product diagnostics now reports both incoming reader assets and generated draft assets
- `reader_intake_draft_smoke.py` proves draft generation does not create formal `intakes/*.json`
- `v20d_intake_draft_acceptance.sh` gates V2.0C, draft smoke, and product static contract

V2.0D is deliberately strict. It does not rebuild `compiled_packs/active_cognitive_pack.json`, and it does not write into `hermes_cognitive_os/intakes/`. The next promotion step must be explicit because reader highlights without interpretation are weak evidence.

## V2.0E Status

V2.0E closes the first explicit draft-to-formal-intake promotion loop and has passed acceptance:

- `sentence_reader_promote_intake_draft.py` promotes selected `sentence_reader.book_intake_draft.v1` files into formal Hermes Cognitive OS `intakes/*.json`
- promotion requires the explicit `--approved` flag; without it the worker fails with `missing_approved_flag`
- `review_ready` drafts can be promoted by default
- `needs_review` drafts require the explicit `--allow-needs-review` override
- `blocked` drafts still fail
- existing formal intake files are not overwritten unless `--overwrite` is passed
- active pack rebuild is opt-in through `--rebuild-active-pack`
- Cognitive OS quality gate runs only after an opt-in rebuild, unless `--skip-quality-gate` is explicitly passed
- packaged `ReaderRuntime` includes the promotion worker
- product diagnostics now reports reader drafts, promotion reports, and formal Cognitive OS intakes
- `reader_intake_promotion_smoke.py` proves that unapproved promotion fails and approved promotion writes exactly one formal intake in a temporary Cognitive OS
- production dry run found no real drafts to promote, so no formal production intake was written

V2.0E is still not a final operator UI. It is a safe command boundary. The app can now produce reading assets and the backend can turn reviewed drafts into formal Cognitive OS intakes, but the human review screen/queue is not built yet.

## V2.0F Status

V2.0F adds the first operator review queue and has passed acceptance:

- `sentence_reader_review_queue.py` scans `hermes_cognitive_os/incoming/sentence_reader_drafts/*.draft.json`
- it emits JSON using schema `sentence_reader.intake_review_queue.v1`
- it emits a Markdown review report for human reading
- each draft is classified as `ready_to_approve`, `needs_review`, `blocked`, or `already_promoted`
- ready drafts get suggested approve/rebuild commands that still require `--approved`
- weak drafts surface warnings such as missing notes or placeholder interpretation
- blocked drafts show blocking reasons instead of being silently skipped
- packaged `ReaderRuntime` includes the review queue worker
- product diagnostics now inventories the review queue directory
- `reader_review_queue_smoke.py` proves the queue can separate one ready draft from one weak draft
- production dry run found no real drafts, so the queue report is empty and no promotion happened

V2.0F is not a polished Swift operator UI. It is the safer product boundary before building UI: the system can now tell you what needs review and what command would approve it, without taking action on your behalf.

## V2.0G Status

V2.0G adds the first transaction-style active-pack operator flow and has passed acceptance:

- `sentence_reader_active_pack_operator.py` builds or reads the V2.0F queue and selects explicit drafts, draft ids, or all `ready_to_approve` items
- non-dry-run execution requires `--approved`
- it runs a promotion preflight before writing any formal intake
- it writes rollback artifacts before changing formal intakes or active packs
- it calls the V2.0E promotion worker to write formal `intakes/*.json`
- it calls Hermes Cognitive OS `scripts/build_active_cognitive_pack.py` to rebuild `compiled_packs/active_cognitive_pack.json`
- it runs the Cognitive OS quality gate by default after rebuild when available
- `--skip-quality-gate` exists for smoke tests and controlled exceptional cases
- failure after writes triggers rollback by default for files created or changed by the operator run
- the operator writes `sentence_reader.active_pack_operator_report.v1`
- the rollback manifest uses `sentence_reader.active_pack_operator_rollback.v1`
- packaged `ReaderRuntime` includes the active-pack operator worker
- production dry run found no real drafts and skipped promotion/rebuild cleanly

V2.0G is still not a polished UI. It is the command-level transaction boundary that the future UI should call.

## V2.0H Status

V2.0H adds the first safe in-app/operator surface and has passed its focused smoke checks:

- Reader API exposes `POST /cognitive/review-queue`
- Reader API exposes `POST /cognitive/operator/dry-run`
- both endpoints use the existing V2.0F/V2.0G scripts instead of duplicating operator logic
- queue reports are written under `~/Library/Application Support/SentenceReader/CognitiveOps/review_queue`
- dry-run reports are written under `~/Library/Application Support/SentenceReader/CognitiveOps/operator_dry_runs`
- Swift top bar now has a `认知` button
- the `认知` button checks queue counts, runs a safe dry-run, updates the status line, and can open the Markdown queue report
- static checks now verify the API endpoints and Swift markers
- `reader_api_cognitive_operator_smoke.py` proves an empty temporary Cognitive OS root produces a queue report and a dry-run report without approval or active-pack mutation

V2.0H is not final approval UI. That is deliberate. The correct next UI step is to show draft detail and require explicit human approval before calling the non-dry-run operator.

## V2.0I Status

V2.0I adds the first single-draft review detail and selected preflight boundary:

- Reader API exposes `POST /cognitive/review-item`
- Reader API exposes `POST /cognitive/operator/preflight`
- review item selection supports `draft_path`, `draft_id`, `candidate_intake_id`, or default priority order
- default priority order is `ready_to_approve`, then `needs_review`, then `blocked`
- review-item reports use schema `sentence_reader.cognitive_review_item.v1`
- review-item Markdown includes source evidence, user interpretation, why it matters, proposed model, warnings, blocking reasons, approval policy, and preflight summary
- draft reading is restricted to `hermes_cognitive_os/incoming/sentence_reader_drafts`
- selected preflight runs the existing active-pack operator in dry-run mode
- selected preflight must not write `hermes_cognitive_os/intakes/*.json`
- Swift `认知` now opens the single-draft detail report when a draft exists; otherwise it falls back to the queue report
- `reader_api_cognitive_operator_smoke.py` now creates one ready temporary draft and proves detail/preflight behavior without active-pack mutation

V2.0I still does not add a one-click approval button. The next approval UI must require explicit human intent and should surface rollback/quality-gate consequences before any non-dry-run operator call.

## V2.0J Status

V2.0J adds the first strongly confirmed approval boundary:

- Reader API exposes `POST /cognitive/operator/approve`
- approval is one draft at a time, keyed by `candidate_intake_id`
- approval requires exact confirmation text: `APPROVE <candidate_intake_id>`
- bad confirmation returns an error before any operator command runs
- blocked drafts are rejected
- `needs_review` drafts remain rejected unless `allow_needs_review=true`
- `skip_quality_gate=true` requires `skip_quality_gate_reason`
- approval reruns selected preflight before executing the non-dry-run operator
- approval uses the existing V2.0G active-pack operator with rollback-on-failure
- approval response includes promotion report, active-pack rebuild result, quality-gate result, rollback manifest, and confirmation metadata
- smoke coverage proves a bad confirmation is rejected and a correct confirmation writes exactly one formal intake plus an active pack in a temporary Cognitive OS root

V2.0J is still not a polished approval UI. It is the backend approval contract that a future UI can call. That is intentional: the dangerous write path now exists, so the next UI must make approval intent unmistakable.

## V2.0K Status

V2.0K adds the first App-level approval UX on top of the V2.0J backend contract:

- Swift `认知` flow now detects the current review item status and candidate intake id
- `批准入库...` is only shown when the selected detail item is `ready_to_approve`
- clicking approval opens a second confirmation dialog
- the user must type the exact phrase `APPROVE <candidate_intake_id>`
- if the phrase does not match, the App refuses to call the approval endpoint
- approval calls `POST /cognitive/operator/approve`
- success opens the operator report when available
- failure opens the detail report to keep the user anchored in the evidence
- product static smoke checks for `cognitiveApprove`, `promptCognitiveApproval`, `approveCognitiveDraft`, `APPROVE`, and `确认短语不匹配`

V2.0K is intentionally a small UX surface. It is not a full review dashboard, but it turns the dangerous write path into a deliberate two-step action inside the App.

## V2.0L Status

V2.0L adds the first Cognitive OS operator dashboard on top of the V2.0K approval UX:

- Reader API exposes `GET /cognitive/dashboard`
- Reader API exposes `POST /cognitive/dashboard`
- dashboard reports use schema `sentence_reader.cognitive_dashboard.v1`
- dashboard JSON and Markdown are written under `~/Library/Application Support/SentenceReader/CognitiveOps/dashboard`
- the dashboard reruns the review queue and groups drafts by `ready_to_approve`, `needs_review`, `blocked`, and `already_promoted`
- the dashboard includes safety policy text for exact approval confirmation, dry-run preflight, rollback visibility, and quality-gate visibility
- the dashboard scans operator reports for the same Cognitive OS root and shows approval history
- approval history summarizes approved status, dry-run status, selected count, active-pack rebuild result, quality-gate result, and rollback manifest path
- Swift `认知` now calls the dashboard endpoint and offers `打开仪表盘`
- the App still keeps `批准入库...` behind the V2.0K exact typed confirmation flow
- `reader_api_cognitive_operator_smoke.py` now proves the dashboard is affected by a ready draft and later shows a successful approval history
- `v20l_cognitive_dashboard_acceptance.sh` gates V2.0K, dashboard smoke, Swift compile, Reader API static checks, and product static checks

V2.0L is still a report-first dashboard, not a native table view with filters inside the Swift window. That is the correct boundary for this round: approval is now visible and traceable, but active-pack mutation is still deliberate.

## V2.0M Status

V2.0M turns the V2.0L report-first dashboard into a native App review surface:

- Swift adds `CognitiveDashboardWindowController`
- dashboard draft rows are parsed into `CognitiveDashboardDraftRow`
- approval history rows are parsed into `CognitiveDashboardHistoryRow`
- the top-bar `认知` flow now opens a native `认知审核台` when the dashboard schema is valid
- the native dashboard shows queue counts from `sentence_reader.cognitive_dashboard.v1`
- the native table lists status, book/candidate, quality, model, and warning/blocking issue summary
- status filtering supports `全部`, `可批准`, `待审`, `阻塞`, and `已入库`
- the lower history panel shows recent approval/operator history with rebuild, quality, skipped, and rollback fields
- the window can open the generated Markdown dashboard and selected draft source
- the native dashboard intentionally does not include an approval button; approval remains behind the V2.0K typed-confirm flow
- `sentence_reader_native_cognitive_dashboard_smoke.py` locks the Swift markers
- `v20m_native_cognitive_dashboard_acceptance.sh` gates V2.0L, native dashboard static smoke, Swift compile, product static smoke, and dashboard API smoke

V2.0M is a product usability improvement, not a new mutation path. That is the right design: review is easy, approval is still deliberate.

## V2.0N Status

V2.0N adds a hard runtime portability contract:

- `sentence_reader_runtime_portability.py` writes `sentence_reader.runtime_portability_report.v1`
- the report separates `current_machine_ready` from `clean_mac_ready`
- the report checks packaged ReaderRuntime files, bundled virtualenv, Python dependency imports, PostgreSQL strategy, runtime manifest, and feature portability risks
- `package_sentence_reader_app.py` now writes `ReaderRuntime/runtime_manifest.json` with schema `sentence_reader.runtime_manifest.v1`
- `package_sentence_reader_app.py` now copies `sentence_reader_runtime_portability.py` into ReaderRuntime
- `sentence_reader_product_diagnostics.py` now runs the portability report when `--require-package` is used
- `sentence_reader_product_static_smoke.py` now locks portability script, diagnostics, and package manifest markers
- `docs/runtime_portability.md` records the current strategy and known clean-Mac blockers
- `v20n_runtime_portability_acceptance.sh` gates V2.0M, package creation, portability report, runtime launch smoke, product diagnostics, and product static checks

The current report is deliberately not clean-Mac green:

- `current_machine_ready=true`
- `clean_mac_ready=false`
- blockers: `runtime_python_points_to_xcode`, `runtime_python_points_outside_ReaderRuntime`, `postgres_not_bundled`

This is stronger than the previous state because the risk is now machine-checkable. It is not the final installer.

## V2.0O Status

V2.0O adds a real startup bootstrap/preflight path:

- `sentence_reader_runtime_bootstrap.py` writes `sentence_reader.runtime_bootstrap_report.v1`
- it checks candidate Python runtimes: explicit `READER_API_PYTHON`, user app-support venv, bundled runtime venv, and system `python3`
- it selects the first Python that can import FastAPI, Uvicorn, Psycopg, and HTTPX
- it can create a user-level venv under `~/Library/Application Support/SentenceReader/Runtime/.venv-reader-api` when called with `--repair-python`
- dependency installation requires the explicit `--install-deps` flag
- PostgreSQL remains an explicit preflight: existing server or available Postgres.app tools are accepted
- `run_reader_api.sh` now calls the bootstrap selector if no bundled/runtime Python is executable
- automatic dependency installation is disabled by default
- automatic PostgreSQL installation is disabled by default
- product diagnostics now includes runtime bootstrap status
- `sentence_reader_runtime_bootstrap_smoke.py` proves user-level venv creation and Python selection without installing dependencies
- `v20o_runtime_bootstrap_acceptance.sh` gates V2.0N, package creation, bootstrap smoke, bootstrap report, runtime launch smoke, product diagnostics, and product static checks

V2.0O still does not make the app a universal installer. It turns a previously hidden startup failure into a recoverable, explicit bootstrap flow.

## V2.0P Status

V2.0P makes first-run readiness explicit:

- `sentence_reader_runtime_config.py` writes and reads `sentence_reader.runtime_config.v1`
- FunASR paths can be configured by `SENTENCE_READER_RUNTIME_CONFIG`, `SENTENCE_READER_FUNASR_PYTHON`, `SENTENCE_READER_FUNASR_WORKER`, or the app-support runtime config file
- Swift note transcription no longer depends only on a hard-coded user project path
- Swift still keeps the legacy FunASR path as a compatibility fallback
- `sentence_reader_first_run_preflight.py` writes `sentence_reader.first_run_preflight_report.v1`
- first-run preflight reports PostgreSQL readiness, Reader API startup/migration boundary, runtime bootstrap status, runtime config path, and FunASR readiness/fallback
- product diagnostics now fails package acceptance if first-run preflight cannot run
- `sentence_reader_first_run_preflight_smoke.py` verifies runtime config + preflight behavior without real transcription or paid services
- `package_sentence_reader_app.py` bundles the runtime config and first-run preflight scripts into ReaderRuntime
- `v20p_first_run_preflight_acceptance.sh` gates V2.0O, package creation, runtime config smoke, first-run preflight smoke/report with `first_run_ready=true`, product diagnostics, product static smoke, and Swift compile

V2.0P still does not install PostgreSQL or FunASR automatically. That is intentional: install/repair remains explicit, and missing FunASR falls back to Apple Speech so reading and manual notes are not blocked.

## V2.0Q Status

V2.0Q moves first-run visibility into the App:

- Swift adds `RuntimeEnvironmentWindowController`
- the top bar now includes `环境`
- `环境` opens a native runtime environment window
- the window runs `sentence_reader_first_run_preflight.py` with `--require-first-run-ready`
- App-run reports are written under `~/Library/Application Support/SentenceReader/Diagnostics`
- the window shows PostgreSQL, Reader API, runtime bootstrap, runtime config, and FunASR status
- the window can open the generated Markdown/JSON preflight report
- FunASR Python and worker paths can be saved from the App
- saved paths are written both to `UserDefaults` and to `~/Library/Application Support/SentenceReader/config/runtime_config.json`
- `sentence_reader_runtime_settings_static_smoke.py` locks the App-level runtime settings markers
- `v20q_runtime_settings_acceptance.sh` gates V2.0P, runtime settings static smoke, package creation, first-run preflight, product static smoke, and Swift compile

V2.0Q still does not run a destructive installer. It makes runtime health visible and configurable inside the app, while keeping PostgreSQL/bootstrap repair explicit.

## V2.0R Status

V2.0R makes first-run failure actionable without becoming an installer:

- App launch now runs a background first-run preflight
- the runtime environment window appears automatically only when `first_run_ready=false`
- normal ready state does not interrupt reading
- runtime environment window includes a `首启修复引导` section
- the guide explains PostgreSQL recovery, Runtime Python/bootstrap recovery, and FunASR recovery
- guide text preserves the explicit policy: no hidden dependency install, no automatic PostgreSQL install, no destructive database operation
- users can copy the guide via `复制修复指引`
- users can open the runtime config folder via `打开配置目录`
- `sentence_reader_first_run_guide_static_smoke.py` locks the Swift guide markers
- `v20r_first_run_guide_acceptance.sh` gates V2.0Q, first-run guide static smoke, product static smoke, package creation, and Swift compile

V2.0R still does not make a clean-Mac universal installer. It makes the failure path understandable inside the App.

## V2.0S Status

V2.0S adds product identity and Dock-friendly access:

- `generate_sentence_reader_icon.py` generates a reading-themed icon with an open book and red bookmark
- generated icon files live under `assets/SentenceReader.iconset`
- generated app icon is `assets/SentenceReader.icns`
- `package_sentence_reader_app.py` copies the icon into `Sentence Reader.app/Contents/Resources`
- `Info.plist` now sets `CFBundleIconFile` to `SentenceReader`
- packaged output prints `app_icon=True`
- `pin_sentence_reader_to_dock.py` adds the packaged app to the Dock with duplicate detection
- `sentence_reader_identity_static_smoke.py` verifies icon, Info.plist, package integration, and Dock script markers
- `v20s_product_identity_acceptance.sh` gates V2.0R, icon generation, package creation, Dock dry-run, identity smoke, and product static smoke
- the current packaged app was added to the macOS Dock

V2.0S still pins the project build app path, not a signed `/Applications` installer. That is good enough for this local product stage, but not final distribution.

## Next Required Step

## V2.0T Status

V2.0T adds the missing product main surface:

- the top bar now has a native `书库` entry
- `书库` opens a real library management window instead of only a quick switch menu
- the library window lists bundled and imported books from `SentenceReader.bookLibrary.v1`
- imported EPUBs are shown as owned internal library copies
- actions include `导入 EPUB`, `打开所选`, `显示内部副本`, and `从书库移除`
- `从书库移除` is deliberately non-destructive: it removes only the library index entry and does not delete internal EPUB copies, reading positions, highlights, notes, audio notes, or PostgreSQL data
- the old `书籍` quick switch remains as a fast menu, but it is no longer the only book-management surface
- `check_native_reader.py` and product static smoke now lock the library window markers

This fixes a real product gap. Before V2.0T the app had a reading window plus a switcher, but not a main/library management interface. Now it has a functional book management surface. It is still not a polished visual bookshelf.

## Library UI Productization Status

The simplified native book table is no longer the primary product surface. Library V2 is the primary product home.

Current state:

- Reader API exposes `GET /library` as a reading-first product home.
- Reader API exposes `GET /api/library/dashboard` with `ui_version=library_v2`, books, current/recent reading, progress, reading state, cover URL, note counts, red highlight counts, audio note counts, recent notes/red highlights, file status, and internal-copy status.
- Reader API exposes `GET /api/library/books/{book_id}/cover` for real EPUB cover extraction with generated fallback covers.
- Reader API exposes `POST /api/library/import` for EPUB import into the Mac-owned internal library.
- Reader API exposes `POST /api/library/books/{book_id}/hide` for non-destructive list removal.
- Reader API exposes `POST /api/library/books/{book_id}/reveal` for showing the EPUB copy in Finder on the Mac.
- PostgreSQL has `reader.library_state` for UI visibility state only.
- Swift opens the main window directly to `http://127.0.0.1:18180/library?surface=mac-app` when Reader API is available.
- Swift `书库` returns to the same main-window library surface instead of opening a separate window.
- Clicking a book cover/card in the Mac App opens the original native sentence reader through `sentence-reader://open-native?book_id=...`; it does not route the Mac user into `/lan/reader`.
- The home page has a large `继续阅读` area, recent-reading rail, recent notes/red highlights, a cover-wall library, dedicated notes center, dedicated red-highlight center, details drawer, and basic batch hide/export.
- The reader chrome uses larger grouped controls: `书库`, `目录`, `笔记`, `设置`, and `更多`.
- The old AppKit book table remains only as a fallback if Reader API cannot start.
- iPad entry now gives the `/library` URL first and preserves `/lan/reader` as a direct reading URL.
- `sentence_reader_library_ui_static_smoke.py` and `sentence_reader_library_v2_smoke.py` lock the page, API, cover endpoint, Mac native-open contract, notes/red centers, batch actions, Swift entry, migration, and non-destructive hide contract.

No external reader system is embedded. The App has one product direction: local durable reading data + sentence-level native reader + Library V2 product shell.

## Vocabulary Lookup Repair Status

English lookup is no longer only a UI gesture. The backend now has a real fallback path:

- single-click/single-tap English lookup first checks book-local vocabulary
- if the current book has no generated vocabulary rows, Reader API falls back to `reader.dictionary_entries`
- the fallback creates a dictionary-backed `reader.book_vocab_items` row so repeated lookup is stable
- simple morphology is covered for common forms like plural `strategies`
- a compact general/business seed dictionary is installed by `005_general_dictionary_seed.sql`
- the full ECDICT-compatible CSV has been downloaded to `data/external/ecdict/ecdict.csv`
- `sentence_reader_import_ecdict.py` imported 768,739 dictionary rows into PostgreSQL with source `ecdict`
- lookup quality is now backed by a real local dictionary, not just a tiny seed list

The Readium publication-open probe also no longer depends on a specific Desktop EPUB. The project now generates and packages `fixtures/sentence-reader-smoke.epub` as the stable test fixture, so the original source book can be moved or deleted without breaking validation.

## Next Required Step

After library UI productization, decide:

- manually test Library V2 with 10+ real EPUBs and unusual cover metadata
- whether to install/copy a stable app build into `/Applications` or keep using the project build path
- add a small release packaging note so future rebuilds do not confuse Dock aliases
- keep first-run repair explicit and avoid automatic destructive setup
- keep destructive restore and active-pack mutation behind explicit user approval
