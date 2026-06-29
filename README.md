# Sentence Reader Mac V1

Mac reading app plan for sentence-level close reading.

The product goal is not to clone Apple Books. The goal is a local-first reading workspace where one sentence can be annotated, marked, exported, and later synced into Hermes Cognitive OS.

## V1 Scope

- EPUB first.
- PDF basic opening only; PDF sentence-level annotation is not a V1 promise.
- Double-click a sentence to add a note.
- Secondary click / two-finger tap a sentence to toggle red highlight.
- Save annotations locally without modifying the original book file.
- Export notes as Markdown.
- Reserve a Hermes sync payload, but do not couple the reader to Hermes runtime availability.

## Current Stage

This repository is still in V1 probe stage, not a finished reader app.

The local sentence/annotation/export core is buildable. Xcode is now active, Readium dependencies resolve, `ReadiumNavigator` builds for Mac Catalyst, the project has a minimal `ReadiumCatalystAdapterProbe` that compiles against Readium's public navigator, locator, and decoration APIs, and `ReadiumPublicationOpenProbe` opens the Desktop EPUB fixture through Readium Streamer.

The visual reader probe compiles a SwiftUI wrapper around `EPUBNavigatorViewController`, but SwiftPM currently produces a Mach-O executable rather than a launchable `.app` bundle. The next hard step is a real Xcode application target that renders the Desktop EPUB fixture and verifies pointer event -> locator/range -> decoration.

See:

- `docs/v1_design.md`
- `docs/v1_ui_interaction_design.md`
- `docs/readium_probe_acceptance.md`
- `docs/reader_engine_adapter.md`
- `docs/data_model_and_export.md`
- `schema/v1_schema.sql`
- `prototypes/v1_reader_wireframe.html`
- `Probe/`
- `reports/project_status_2026-06-24.md`
