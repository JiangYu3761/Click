# Sentence Reader Product Roadmap

## Product Goal

Sentence Reader is a sentence-level deep reading app. It should let the user read EPUB books, mark whole sentences, write or dictate notes, keep everything permanently, and export or sync the resulting knowledge assets.

## Database Decision

PostgreSQL is the product-grade source of truth.

Large files remain on disk:

- EPUB/PDF files
- note audio files
- exported Markdown/JSON
- diagnostic reports

PostgreSQL stores metadata, locators, annotations, reading positions, audio-note transcripts, export records, and sync events.

The Mac app should not become a direct database client in the long term. It should talk to a local Reader API service.

## Version Plan

| Version | Scope | Completion Standard |
| --- | --- | --- |
| V1.2 | PostgreSQL reader schema and local Reader API foundation | `reader` schema exists, migrations run, API health and CRUD smoke pass |
| V1.3 | Swift app data integration | reading position, red highlights, and notes survive restart through Reader API |
| V1.4 | Notes management loop | right notes rail, edit/delete/search, click note to jump back |
| V1.5 | Multi-book library | import/open multiple EPUBs with independent progress and annotations |
| V1.6 | Export loop | deterministic Markdown/JSON export with source sentence, notes, metadata |
| V1.7 | Voice notes productization | FunASR runs as a warm service/queue instead of cold-start per note |
| V1.8 | Reading stability | reading settings, image/TOC/page-turn robustness, hour-long reading test |
| V1.9 | Hermes/Cognitive OS sync | selected notes and reading models sync into Hermes/Cognitive OS |
| V2.0 | Product packaging | Readium-grade engine boundary, installer, backup/restore, diagnostics |
| V2.1 | iPad LAN Reader | trusted same-LAN browser reader using Reader API, shared books/annotations/positions |
| Platform P1 | Windows browser route | planned: Windows runs local Reader API and opens `http://localhost:18180/library` |
| Platform P2 | Windows desktop shell | planned: `Click.exe` with WebView2 or Tauri, reusing `/library`, the Web reader, and the shared Web keyboard contract |
| Platform P3 | Windows installer | planned: runtime, icon, diagnostics, Start Menu shortcut, optional desktop shortcut, uninstall cleanup; not implemented yet |

## Current Priority

The current priority is product acceptance, not feature expansion. V2.1 is accepted only when the Mac app, Reader API/PostgreSQL, FunASR, and the iPad LAN reader all pass their hard checks and the live `18180` service is verified as a single all-interface listener.

2026-06-25 repeat acceptance decision: do not open a V2.2/V3 expansion track until a real user-facing defect appears. The V2.1 product-grade boundary should be maintained by rerunning the hard checks and the live readiness smoke after any future change.

2026-06-25 13:27 CST repeat verification passed the full product-grade check set again. The roadmap remains in maintain-and-verify mode: fix real regressions, but do not expand scope beyond the V2.1 daily-use boundary without a new product decision.

2026-06-26 iPad touch refinement decision: keep the same `/lan/reader` surface, but stop forcing desktop gestures onto touch. Sentence-level actions belong in a bottom action bar, reading settings belong under `Aa`, and the reader must have a visible return path to `/library`.

2026-06-26 iPad compact-chrome decision: reduce permanent UI chrome again. Reading text is the product surface; toolbar buttons and sentence actions should be compact overlays and must not reserve large blank areas when inactive.

2026-06-29 Life-study vocabulary decision: Genesis is no longer blocked at the review gate. `Life-study Context Vocabulary Pipeline V1` has passed Genesis first 50 pages and Genesis full-run rule gates, imported only 25 A/B entries into the isolated `reader.domain_glossary_entries` boundary, imported the matching book-specific rows for `book_e0679064039e4e298e9faf3127b65876`, and applied the user-reviewed all-approve override through the explicit review apply command. `can_expand_next_volume=true` now applies only to controlled no-write probes, not to bulk production import. Exodus and Leviticus first-50 plus full no-write runs have completed, producing 19 Exodus A/B and 12 Leviticus A/B importable candidates with no database write. The corpus inventory now shows 51 processable Life-study volumes, with Genesis/Exodus/Leviticus full no-write complete and 48 volumes still needing first-50 no-write probes. All completed full no-write candidates are merged into `reports/lifestudy_vocab_corpus/lifestudy_master_vocab.csv/json/md` with source volume, page, evidence, and review status per term. Separately, all 51 processable volumes now feed one all-word master table at `reports/lifestudy_vocab_corpus/lifestudy_all_words_master.csv/json/md`, covering 38,166 unique normalized English words and 5,297,307 raw English tokens with source volume/page evidence. The implementation plan is `docs/lifestudy_vocab_pipeline_plan.md`.

2026-06-30 voice provider decision: Mac voice notes should default to Click's software-layer local recognition path (`FunASR`), with Apple Speech retained as the backup/system provider. When FunASR fails, the app should try Apple Speech as fallback instead of ending the note as failed.

2026-06-30 platform route decision: Click should present itself as one local reading system with multiple client entries. macOS App is the current primary usable client; iPad/browser same-LAN access is currently usable; Windows is a planned route. The shared Web reader now implements the keyboard contract that Windows will reuse (`N` note, `R` red highlight, `V` voice note, `Esc`, arrows/PageUp/PageDown). Windows should not rewrite the reader or introduce a second database. P1 is browser access with local Reader API, P2 is a WebView2 or Tauri `Click.exe` shell, and P3 is an installer with Start Menu and optional desktop shortcut behavior. The installer and shortcuts are not implemented yet. Details live in `docs/windows_client_plan.md`.

V1.2 is done only when:

1. PostgreSQL is available locally.
2. `sentence_reader` exists.
3. `reader` schema migration succeeds.
4. Reader API can start.
5. CRUD smoke test creates, reads, updates, and cleans up a book, sentence, annotation, and reading position.

Current V1.2 rule: API mock tests can prove the contract and CRUD route shape, but they do not replace the real PostgreSQL migration/smoke. Do not mark V1.2 complete until both layers pass.

Current V1.2 status:

- Reader API schema, endpoints, dependency file, and mock CRUD tests exist.
- Project-local Python API environment exists at `.venv-reader-api/`.
- V1.2 hard acceptance script exists at `scripts/v12_data_acceptance.sh`.
- Postgres.app 2.9.5 / PostgreSQL 18.4 is installed at `/Applications/Postgres.app`.
- `sentence_reader` and `reader` schema passed migration and CRUD smoke.

V1.3 completion standard:

1. Swift App can start or reach the local Reader API.
2. Swift App creates/uses a stable book record.
3. Reading position writes to Reader API and can be read back.
4. Red highlights write to Reader API and restore on chapter load.
5. Notes write to Reader API.
6. The app still compiles and packages without UI regressions.

V1.3 hard acceptance script:

```bash
./scripts/v13_swift_data_acceptance.sh
```

Current V1.3 status: passed.

V1.4 should add the notes management loop without changing the database decision:

- current-book notes rail
- edit/delete/search annotations
- filter notes and red highlights
- click note to jump back to its sentence
- continue writing through Reader API/PostgreSQL

Current V1.4 status: passed.

V1.4 hard acceptance script:

```bash
./scripts/v14_notes_acceptance.sh
```

V1.5 should add multi-book capability without breaking the current single-book reading workflow:

- open/import EPUB from disk
- persist `reader.books` and `reader.book_files` per imported book
- keep reading positions and annotations independent per book
- add a minimal book switcher
- keep current notes rail scoped to the selected book

Current V1.5 status: passed.

V1.5 hard acceptance script:

```bash
./scripts/v15_multibook_acceptance.sh
```

V1.6 should add export without changing the reader interaction model:

- export current-book annotations to Markdown and JSON
- preserve source sentence, note text, highlight kind, chapter title, locator, and created/updated timestamps
- write an export record through `reader.exports`
- avoid cloud sync and AI summaries in this stage

Current V1.6 status: passed.

V1.6 hard acceptance script:

```bash
./scripts/v16_export_acceptance.sh
```

V1.7 should make voice notes product-grade without changing the note editor workflow:

- define a local FunASR service or queue boundary
- avoid cold-starting transcription for every note where possible
- persist audio path, transcript, status, and provider through `reader.audio_notes`
- keep Apple Speech as fallback only
- add smoke tests that can run without paid cloud services

Current V1.7 status: passed for persistence, queue boundary, and App-lifetime warm FunASR service. It is not a system-wide daemon; Sentence Reader starts `funasr_worker.py --server` after launch, uses local `/transcribe` first, and falls back to one-shot worker plus Apple Speech when unavailable.

V1.7 hard acceptance script:

```bash
./scripts/v17_voice_acceptance.sh
```

V1.8 should stabilize the reading experience without changing the database contract:

- persist reader settings such as font size, line height, margins, and theme if needed
- harden horizontal page turn and chapter-edge behavior
- improve image containment and long-chapter behavior
- add static and smoke checks for the reading settings contract
- document a longer manual reading test path

Current V1.8 status: passed.

2026-06-24 pagination hotfix: V1.8 also now gates full-height WebView pagination, paragraph cross-page flow, measured content-width page counting, and trailing blank-page prevention.

2026-06-24 immersive chrome hotfix: V1.8 also gates hidden-by-default top/bottom reader chrome, full-height reading content, transparent titlebar, and edge-hover control reveal.

2026-06-25 Annotation Core V2 hotfix: V1.8 also gates multi-line selection red marking, note markers restored into the reading surface, single-click note preview, and sentence-boundary handling that does not split on colon or semicolon. This intentionally keeps the existing PostgreSQL schema and stores multi-sentence locators through the current annotation range/metadata fields.

V1.8 hard acceptance script:

```bash
./scripts/v18_reading_stability_acceptance.sh
```

V1.9 should connect reader knowledge assets to Hermes/Cognitive OS without putting AI work inside the reading surface:

- define a narrow sync payload from selected notes, source sentences, locators, and book metadata
- use Reader API as the boundary; Swift should not call Hermes directly
- record sync attempts through `reader.sync_events`
- keep local reading and annotation workflows usable when Hermes is offline
- add smoke tests for payload generation and sync-event persistence

Current V1.9 status: passed for the local sync handoff boundary.

Life-study vocabulary status on 2026-06-29: Genesis extraction, controlled import, frontend lookup, review pack generation, review-apply tooling, a no-write Reader API review UI, assistant evidence-triage suggestions, a single-word review lane, an all-word frequency/context report, a phrase/uncommon-word review document, a no-write stage gate, corpus inventory, high-confidence master vocabulary aggregation, full-corpus all-word master aggregation, and Life-study Context Vocabulary V1 are implemented. Genesis now has 25 reviewed/imported phrase entries, and the full Life-study all-word master covers 51 processable volumes in one table. The V1 quality gate cleaned 38,166 raw unique words into 33,724 clean lemma groups, generated a Top 500 review queue plus Top 2000 reserve queue, and imported only 34 A-grade direct-evidence terms into the Life-study domain glossary. `economy`, `dispensing`, and `mingled` now resolve through `lifestudy_domain_glossary` in Life-study books; ordinary books do not use this source. The V2 learning-review lane now has 6,321 dictionary-guided Chinese-context candidates, 4,102 possible front-end-after-review candidates, a 500-row front-end candidate pack, and a 28-row Codex-adjudicated first batch. Of those 28, 26 have now been explicitly applied into `reader.domain_glossary_entries` through the controlled dry-run/apply boundary; dictionary pollution remains 0 and active Life-study domain terms increased from 59 to 85. Live Reader API lookup now verifies the corrected terms in the imported Life-study Genesis book and confirms ordinary books do not use the Life-study adjudicated meanings. The next improvement is continuing the next reviewed batch, not bulk importing the 33,724-word learning table.

V1.9 hard acceptance script:

```bash
./scripts/v19_hermes_sync_acceptance.sh
```

V1.9 intentionally does not make the reading UI generate AI summaries. It creates `sentence_reader.hermes_sync.v1` payloads under `~/Library/Application Support/SentenceReader/HermesSync`, records a pending `reader.sync_events` row, and leaves actual Hermes/Cognitive OS ingestion to the next boundary.

V2.0 should turn the app from a strong local prototype into a maintainable product package:

- package and launch the Reader API reliably with the Mac app
- add startup diagnostics for PostgreSQL, API, FunASR, and filesystem paths
- add backup/restore for PostgreSQL metadata and app-support files
- define the real Hermes/Cognitive OS ingestion worker for pending sync events
- keep EPUB/PDF engine boundaries explicit before expanding PDF scope

Current V2.0A status: passed for product diagnostics, bundled runtime boundary, and safe backup/restore verification.

V2.0A hard acceptance script:

```bash
./scripts/v20_product_packaging_acceptance.sh
```

V2.0A adds:

- bundled `ReaderRuntime` resources inside `build/Sentence Reader.app`
- Swift startup fallback from bundled `ReaderRuntime/scripts/run_reader_api.sh` to the development script path
- product diagnostics report at `reports/sentence_reader_product_diagnostics_report.json`
- non-destructive PostgreSQL backup artifact using `pg_dump --schema=reader`
- backup manifest schema `sentence_reader.backup_manifest.v1`
- restore verification schema `sentence_reader.restore_verify.v1`

V2.0A is not a final installer. It still expects a compatible local Python environment for Reader API dependencies. Destructive restore is intentionally not implemented without explicit user approval.

Current V2.0B status: passed for bundled Reader API runtime launch on this machine.

V2.0B hard acceptance script:

```bash
./scripts/v20b_runtime_acceptance.sh
```

V2.0B adds:

- bundled `.venv-reader-api` inside `build/Sentence Reader.app/Contents/Resources/ReaderRuntime`
- bundled `migrations/reader/001_reader_schema.sql` inside ReaderRuntime
- `run_reader_api.sh` now prefers the runtime-local `.venv-reader-api/bin/python`
- launch smoke proves packaged `ReaderRuntime/scripts/run_reader_api.sh` can start Reader API on a temporary port
- diagnostics now verifies bundled runtime Python and core imports: FastAPI, Uvicorn, Psycopg, HTTPX

V2.0B is still not a universal signed installer. The bundled venv currently preserves a symlink to this machine's Xcode Python, so it is reliable on this machine but not yet portable to a clean Mac without matching developer tools.

Current V2.0C status: passed for safe Hermes/Cognitive OS incoming ingestion.

V2.0C hard acceptance script:

```bash
./scripts/v20c_hermes_ingest_acceptance.sh
```

V2.0C adds:

- Reader API endpoint `POST /sync/hermes/ingest`
- command-line worker `scripts/sentence_reader_hermes_ingest.py`
- package runtime copy of the ingestion worker
- ingestion manifest schema `sentence_reader.hermes_ingestion_manifest.v1`
- incoming asset handoff under `hermes_cognitive_os/incoming/sentence_reader`
- pending `reader.sync_events` marked `synced` after successful incoming handoff
- event-level failure handling that marks broken events `failed` without stopping the whole batch

V2.0C intentionally does not mutate `compiled_packs/active_cognitive_pack.json`. Reader annotations are source assets first. Promotion into cognitive models still requires the Hermes Cognitive OS review/pipeline layer.

Current V2.0D status: passed for safe incoming-to-intake-draft generation.

V2.0D hard acceptance script:

```bash
./scripts/v20d_intake_draft_acceptance.sh
```

V2.0D adds:

- `scripts/sentence_reader_intake_draft.py`
- `scripts/reader_intake_draft_smoke.py`
- `scripts/v20d_intake_draft_acceptance.sh`
- packaged runtime copy of the draft worker
- product static checks for the draft worker and package boundary
- diagnostics inventory for `incoming/sentence_reader_drafts`

V2.0D converts `hermes_cognitive_os/incoming/sentence_reader` assets into reviewable drafts under `hermes_cognitive_os/incoming/sentence_reader_drafts`. The draft includes a conservative `book_intake_candidate`, source manifest/payload paths, a review checklist, and a quality gate.

V2.0D intentionally does not write to `hermes_cognitive_os/intakes/` and does not rebuild `compiled_packs/active_cognitive_pack.json`. This is the correct product boundary: reading highlights are evidence, not automatically durable thinking models.

## V2.1 iPad LAN Reader

Current V2.1 status: implemented for same-LAN browser access.

V2.1 adds:

- Reader API route `GET /lan/reader`
- Reader API route `GET /lan/books`
- Reader API route `GET /lan/books/{book_id}/manifest`
- Reader API route `GET /lan/books/{book_id}/chapters/{chapter_index}`
- Reader API route `GET /lan/books/{book_id}/asset/{asset_path:path}`
- Reader API route `POST /lan/audio-notes/transcribe`
- EPUB OPF/spine parsing through Python stdlib
- transformed local EPUB assets served through Reader API
- browser reader UI for hidden drawer book/chapter navigation, full-screen paginated正文, red highlight, notes, and reading position
- iPad page turn support through buttons, keyboard, and horizontal swipe; page state is saved as `lan_reader_paginated`
- iPad voice note support through browser recording upload to Mac-side FunASR, with audio capture/upload and manual-note fallback
- iPad note preview through a bottom note panel when a note-marked sentence is clicked
- iPad bottom sentence action bar after tapping a sentence: red highlight, note, voice note, copy, and cancel
- iPad `Aa` reading settings for font size, line height, and side padding
- iPad `书库` navigation back to `/library?book_id=...`
- iPad compact chrome: shorter top toolbar, arrow previous/next controls, compact bottom action pill, and reduced inactive bottom padding
- live product readiness smoke `scripts/sentence_reader_product_readiness_smoke.py`
- product acceptance document `docs/product_acceptance.md`
- Swift top-bar `iPad` entry that shows/copies the LAN URL and can launch Reader API with `READER_API_HOST=0.0.0.0`
- static smoke `scripts/sentence_reader_ipad_lan_static_smoke.py`
- API smoke `scripts/reader_api_ipad_lan_smoke.py`
- hard acceptance script `scripts/v21_ipad_lan_acceptance.sh`

2026-06-25 iPad LAN hotfix: V2.1 now hides the chapter list by default, uses measured CSS-column pagination plus real element rect measurement to reduce cropped/blank pages, extracts EPUB body content before rendering, opens a readable note panel for saved notes, and exposes a visible `语音` path instead of relying on the Mac note editor.

V2.1 intentionally does not add public internet access, account login, iCloud sync, HTTPS certificate management, WebSocket live sync, or an iPad native app.

Current V2.0E status: passed for explicit reviewed draft promotion.

V2.0E hard acceptance script:

```bash
./scripts/v20e_intake_promotion_acceptance.sh
```

V2.0E adds:

- `scripts/sentence_reader_promote_intake_draft.py`
- `scripts/reader_intake_promotion_smoke.py`
- `scripts/v20e_intake_promotion_acceptance.sh`
- packaged runtime copy of the promotion worker
- product static checks for the promotion worker and package boundary
- diagnostics inventory for draft promotion reports and formal Cognitive OS intakes

V2.0E makes promotion explicit: the worker refuses to write formal intakes unless `--approved` is passed. It can promote selected drafts, optionally rebuild the active Cognitive OS pack, and optionally run the Cognitive OS quality gate. The production dry run found no real drafts, so no production intake was written this round.

Current V2.0F status: passed for reader draft review queue generation.

V2.0F hard acceptance script:

```bash
./scripts/v20f_review_queue_acceptance.sh
```

V2.0F adds:

- `scripts/sentence_reader_review_queue.py`
- `scripts/reader_review_queue_smoke.py`
- `scripts/v20f_review_queue_acceptance.sh`
- packaged runtime copy of the review queue worker
- product static checks for review queue schema and suggested command contract
- JSON and Markdown review queue reports
- diagnostics inventory for the review queue directory

V2.0F turns raw reader-intake drafts into an operator-facing queue. It classifies each draft as `ready_to_approve`, `needs_review`, `blocked`, or `already_promoted`, and writes suggested commands that still require explicit `--approved`. The production run found no real drafts yet, so no real promotion happened.

Current V2.0G status: passed for transaction-style active-pack operator flow.

V2.0G hard acceptance script:

```bash
./scripts/v20g_active_pack_operator_acceptance.sh
```

V2.0G adds:

- `scripts/sentence_reader_active_pack_operator.py`
- `scripts/reader_active_pack_operator_smoke.py`
- `scripts/v20g_active_pack_operator_acceptance.sh`
- packaged runtime copy of the active-pack operator worker
- product static checks for operator report, rollback manifest, approved flag, rebuild, and quality-gate contract
- production dry-run report under `reports/sentence_reader_active_pack_operator_dry_run`

V2.0G turns the previous command pieces into a single operator transaction:

1. build review queue
2. select draft(s)
3. preflight promotion
4. backup current formal intakes and active pack files
5. promote approved draft(s)
6. rebuild active pack
7. run Cognitive OS quality gate when available
8. roll back this run's file changes on failure
9. write a structured operator report

The production dry run found no selected drafts, so it cleanly skipped promotion and rebuild.

Current V2.0H status: passed for safe Reader API and Swift cognitive operator entry.

V2.0H hard acceptance script:

```bash
./scripts/v20h_cognitive_operator_entry_acceptance.sh
```

V2.0H adds:

- Reader API endpoint `POST /cognitive/review-queue`
- Reader API endpoint `POST /cognitive/operator/dry-run`
- API-side reuse of `sentence_reader_review_queue.py` and `sentence_reader_active_pack_operator.py`
- queue and dry-run reports under `~/Library/Application Support/SentenceReader/CognitiveOps`
- Swift top-bar `认知` action
- App-visible queue counts for `ready_to_approve`, `needs_review`, `blocked`, and `already_promoted`
- App-visible dry-run selected count
- smoke test `scripts/reader_api_cognitive_operator_smoke.py`
- product/static checks that lock the API and Swift markers

V2.0H deliberately does not add one-click approval. The app can inspect and dry-run, but it cannot mutate formal intakes or active packs. That remains behind the explicit approved operator path from V2.0G.

Current V2.0I status: passed for single-draft review detail and selected preflight.

V2.0I hard acceptance script:

```bash
./scripts/v20i_review_detail_acceptance.sh
```

V2.0I adds:

- Reader API endpoint `POST /cognitive/review-item`
- Reader API endpoint `POST /cognitive/operator/preflight`
- review-item schema `sentence_reader.cognitive_review_item.v1`
- single-draft Markdown detail report
- default item priority: `ready_to_approve`, `needs_review`, `blocked`
- path guard that only reads drafts under `incoming/sentence_reader_drafts`
- selected dry-run preflight by draft path, draft id, or candidate intake id
- Swift `认知` opens the detail report when available and falls back to the queue report
- smoke coverage for a real temporary ready draft and a selected preflight with no formal-intake writes

V2.0I deliberately still does not add one-click approval. It makes the approval decision inspectable; it does not make active-pack mutation casual.

Current V2.0J status: passed for strongly confirmed backend approval.

V2.0J hard acceptance script:

```bash
./scripts/v20j_explicit_approval_acceptance.sh
```

V2.0J adds:

- Reader API endpoint `POST /cognitive/operator/approve`
- exact confirmation phrase: `APPROVE <candidate_intake_id>`
- one-draft approval only
- ready-draft gate before non-dry-run execution
- mandatory selected preflight before approval
- explicit `skip_quality_gate_reason` when quality gate skipping is requested
- reuse of the V2.0G rollback-on-failure active-pack operator
- smoke coverage for bad confirmation rejection
- smoke coverage for approved temp-root formal intake write, active-pack rebuild, and rollback manifest creation

V2.0J is a backend write contract, not a casual UI button. The app should not expose a one-tap mutation path.

Current V2.0K status: passed for first App-level typed-confirm approval UX.

V2.0K hard acceptance script:

```bash
./scripts/v20k_approval_ux_acceptance.sh
```

V2.0K adds:

- Swift `认知` flow can open the selected detail report
- Swift shows `批准入库...` only for `ready_to_approve` items
- approval requires a second dialog
- the second dialog requires exact `APPROVE <candidate_intake_id>`
- mismatched confirmation is rejected in Swift before any write API call
- successful approval calls the V2.0J endpoint and can open the operator report
- static checks lock the Swift approval markers

Current V2.0L status: passed for the first Cognitive OS operator dashboard.

V2.0L hard acceptance script:

```bash
./scripts/v20l_cognitive_dashboard_acceptance.sh
```

V2.0L adds:

- Reader API endpoint `GET /cognitive/dashboard`
- Reader API endpoint `POST /cognitive/dashboard`
- dashboard schema `sentence_reader.cognitive_dashboard.v1`
- dashboard JSON and Markdown reports under `~/Library/Application Support/SentenceReader/CognitiveOps/dashboard`
- grouped draft status, queue counts, safety policy, approval history, active-pack rebuild result, quality-gate result, and rollback manifest path
- Swift `认知` action now calls the dashboard and can open `打开仪表盘`
- smoke coverage proving a ready draft appears in the dashboard and a successful approval later appears in approval history

V2.0L is intentionally report-first. The next product decision is whether V2.0M should build a native in-window review table, or solve clean-Mac portability by replacing the current machine-bound Python/PostgreSQL assumptions.

Current V2.0M status: passed for native in-App Cognitive OS dashboard review.

V2.0M hard acceptance script:

```bash
./scripts/v20m_native_cognitive_dashboard_acceptance.sh
```

V2.0M adds:

- native Swift `CognitiveDashboardWindowController`
- parsed `CognitiveDashboardDraftRow` and `CognitiveDashboardHistoryRow`
- status-filtered draft review table: `全部`, `可批准`, `待审`, `阻塞`, `已入库`
- approval/operator history panel showing selected count, rebuild result, quality-gate result, skipped state, and rollback path
- `打开Markdown仪表盘` and `打开所选草稿` actions for traceability
- no native approval button inside the dashboard, preserving the typed-confirm approval path
- static smoke `sentence_reader_native_cognitive_dashboard_smoke.py`

V2.0N should now choose one of two directions:

- clean-Mac portability: remove dependence on this machine's Xcode Python symlink and define PostgreSQL/runtime bootstrap
- selected-draft native preview: show source evidence and proposed model in the review window, still without adding one-click approval

Current V2.0N status: passed for runtime portability contract and diagnostics.

V2.0N hard acceptance script:

```bash
./scripts/v20n_runtime_portability_acceptance.sh
```

V2.0N adds:

- runtime portability script `sentence_reader_runtime_portability.py`
- runtime portability report schema `sentence_reader.runtime_portability_report.v1`
- packaged `ReaderRuntime/runtime_manifest.json` using schema `sentence_reader.runtime_manifest.v1`
- product diagnostics integration for runtime portability
- product static checks for portability script and package manifest markers
- documentation at `docs/runtime_portability.md`

Current V2.0N report:

- `current_machine_ready=true`
- `clean_mac_ready=false`
- blockers: `runtime_python_points_to_xcode`, `runtime_python_points_outside_ReaderRuntime`, `postgres_not_bundled`

V2.0O should implement the actual bootstrap/fix:

- replace the Xcode-linked copied venv with a relocatable Python runtime or an installer-created venv
- make PostgreSQL availability a user-visible preflight/bootstrap instead of a hidden assumption
- move FunASR path configuration out of hard-coded user directories

Current V2.0O status: passed for runtime bootstrap/preflight.

V2.0O hard acceptance script:

```bash
./scripts/v20o_runtime_bootstrap_acceptance.sh
```

V2.0O adds:

- runtime bootstrap script `sentence_reader_runtime_bootstrap.py`
- runtime bootstrap report schema `sentence_reader.runtime_bootstrap_report.v1`
- startup Python candidate selection across explicit env, app-support venv, bundled venv, and system Python
- explicit user-level venv repair path through `--repair-python`
- explicit dependency installation gate through `--install-deps`
- `run_reader_api.sh` bootstrap integration
- product diagnostics integration for runtime bootstrap
- static smoke `sentence_reader_runtime_bootstrap_smoke.py`

Current V2.0P status: passed for first-run preflight and configurable FunASR boundary.

V2.0P hard acceptance script:

```bash
./scripts/v20p_first_run_preflight_acceptance.sh
```

V2.0P adds:

- PostgreSQL first-run preflight that is visible to the user instead of buried in logs
- configurable FunASR runtime path
- runtime config schema `sentence_reader.runtime_config.v1`
- first-run preflight schema `sentence_reader.first_run_preflight_report.v1`
- product diagnostics integration for first-run preflight
- packaged ReaderRuntime copies of the config/preflight scripts
- Swift FunASR resolution through UserDefaults, env vars, runtime config, then legacy fallback
- keeping bootstrap/install actions non-destructive and explicit

V2.0Q should now focus on:

- showing first-run preflight status in the Swift app
- adding a small runtime settings surface for FunASR paths
- keeping PostgreSQL install/start actions explicit rather than automatic

Current V2.0Q status: passed for App-level runtime environment visibility and FunASR path settings.

V2.0Q hard acceptance script:

```bash
./scripts/v20q_runtime_settings_acceptance.sh
```

V2.0Q adds:

- native Swift `RuntimeEnvironmentWindowController`
- top-bar `环境` entry
- App-run first-run preflight with `--require-first-run-ready`
- preflight reports under `~/Library/Application Support/SentenceReader/Diagnostics`
- visible PostgreSQL, Reader API, runtime bootstrap, runtime config, and FunASR status
- in-App FunASR path saving to both `UserDefaults` and `runtime_config.json`
- static smoke `sentence_reader_runtime_settings_static_smoke.py`

V2.0R should now focus on:

- a first-run guide that appears only when `first_run_ready=false`
- clearer PostgreSQL repair/start instructions in the App
- preserving the explicit no-destructive-installer policy

Current V2.0R status: passed for failure-only first-run guide and actionable runtime recovery instructions.

V2.0R hard acceptance script:

```bash
./scripts/v20r_first_run_guide_acceptance.sh
```

V2.0R adds:

- background App launch preflight
- automatic runtime environment window only when `first_run_ready=false`
- `首启修复引导` in the runtime environment window
- copyable repair guide
- runtime config folder opening
- static smoke `sentence_reader_first_run_guide_static_smoke.py`

V2.0S should now focus on:

- a reading-related app icon
- Dock-friendly packaging/access
- preserving all runtime and database contracts

Current V2.0S status: passed for product identity and Dock-friendly access.

V2.0S hard acceptance script:

```bash
./scripts/v20s_product_identity_acceptance.sh
```

V2.0S adds:

- generated reading-themed `.icns` app icon
- `CFBundleIconFile=SentenceReader`
- package-time icon embedding
- Dock pin helper with duplicate detection
- identity static smoke `sentence_reader_identity_static_smoke.py`
- current packaged app pinned to the macOS Dock

Current V2.0T status: implemented for native book library management.

V2.0T adds:

- top-bar `书库` entry
- native library management window
- book list backed by `SentenceReader.bookLibrary.v1`
- open selected book
- import EPUB from the library window
- reveal the owned internal EPUB copy in Finder
- non-destructive removal from the library list
- static acceptance markers for the library window and management actions

The important product correction is that Sentence Reader now has a main management surface. The old quick `书籍` menu remains for fast switching, but it is no longer asked to carry full book management.

Current library UI productization status: Library V2 implemented as the primary main interface.

It adds:

- `GET /library` reading-first product home
- `GET /api/library/dashboard`
- dashboard field `ui_version=library_v2`
- `GET /api/library/books/{book_id}/cover`
- EPUB cover extraction with generated fallback covers
- `POST /api/library/import`
- `POST /api/library/books/{book_id}/hide`
- `POST /api/library/books/{book_id}/reveal`
- direct card/cover open into the existing native sentence reader on Mac
- `继续阅读` hero, recent-reading rail, notes center, red-highlight center, details drawer, and basic batch hide/export
- non-destructive PostgreSQL UI state in `reader.library_state`
- Swift `书库` WKWebView entry to `/library`
- iPad `/library` access while preserving `/lan/reader`
- static smoke `sentence_reader_library_ui_static_smoke.py`
- static smoke `sentence_reader_library_v2_smoke.py`
- architecture notes in `docs/library_ui_plan.md`

The App now has one product direction: local durable reading data + sentence-level native reader + Library V2 product shell. It does not embed Komga, Calibre, Kavita, or a second reader system.

Next should focus on:

- manually testing Library V2 with 10+ real EPUBs and unusual cover metadata
- deciding whether the app should be copied to `/Applications/Sentence Reader.app`
- preserving Dock stability across future rebuilds
- release notes for rebuilding without breaking the pinned app

Current Life-study context vocabulary status: Genesis is reviewed and applied; Exodus and Leviticus are no-write candidate sources only.

It adds:

- OpenCC-backed bilingual PDF extraction for `01_Genesis(120).pdf`
- Genesis first-50-pages quality gate
- Genesis full 1,255-page candidate pack
- reviewed Genesis override and explicit apply boundary
- 25 reviewed Genesis A/B entries in the Life-study domain/book-specific lookup boundary
- Exodus full no-write candidate pack
- Leviticus full no-write candidate pack
- corpus inventory for 51 processable Life-study bilingual volumes
- master vocabulary aggregate at `reports/lifestudy_vocab_corpus/lifestudy_master_vocab.csv/json/md`
- all-book English word master at `reports/lifestudy_vocab_corpus/lifestudy_all_words_master.csv/json/md`
- clean all-word master, Top 500 review queue, Top 2000 reserve queue, V1 review pack, and V1 importable pack
- explicit V1 dry-run/apply/hide script for `reader.domain_glossary_entries`
- dictionary-guided full-corpus learning review with 6,321 Chinese-context candidates
- front-end candidate V2 review pack with 500 priority rows
- Codex-adjudicated first front-end candidate batch with 26 no-write ready-for-dry-run rows
- controlled dry-run/apply/hide script plus applied smoke for those 26 adjudicated rows
- Reader API lookup priority fix so Life-study glossary beats dictionary fallback only in Life-study books
- A/B/C/D grading and A/B-only importable report
- dry-run-first controlled import tooling
- phrase-safe Reader API lookup
- Mac selected-phrase lookup handoff

Next should focus on:

- continuing the next reviewed batch after the 26 applied adjudicated words have passed live lookup
- keeping `living` learning-only and holding `sacrifice` until more Chinese evidence distinguishes `牺牲` from `祭牲/祭物/祭`
- expanding the Life-study V1 importable pack only when new meanings have direct Chinese-context evidence
- continuing Numbers first-50 no-write only for phrase/A-B candidate extraction, not for all-word quantity
- resolving meaning conflicts such as `divine word` before exposing later-volume phrase meanings in the reader

## Delayed On Purpose

Do not start these until the relevant earlier stages pass:

- AI summaries
- cloud sync
- account system
- beautiful bookshelf
- advanced PDF annotation
- hidden voice gestures
- global cross-system hub migration beyond the V1.9 Reader API boundary
