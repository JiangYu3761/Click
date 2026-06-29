# Sentence Reader Annotation Core V2 Plan

Updated: 2026-06-25

## Goal

Fix the current product-grade annotation gaps before expanding to LAN/iPad access:

- three-finger or drag selection can cover multiple lines, and right-click/two-finger tap should mark every covered sentence red
- colon, semicolon, and ordinary special characters should not split a logical sentence
- saved notes should be visible from the reading page, not only from the notes rail

## File-Level Work

### `Probe/NativeSentenceReader/SentenceReaderNative.swift`

Adjust this file.

Work:

- Extend the WebView annotation bridge from red-only restore to full annotation restore.
- Add `__sentenceReaderApplyAnnotations` with red highlight and note marker payloads.
- Keep `__sentenceReaderApplyRedHighlights` as a compatibility wrapper.
- Add note markers with `.sr-note` styling.
- On single click, focus the sentence and open the note preview when the sentence has a saved note.
- Add Swift handling for `notePreview`.
- Add a small note-preview sheet with an edit path.
- Refresh WebView markers after note create, note edit, note delete, and red highlight restore.
- Add comma-separated multi-sentence locator support without changing the database schema.
- Store multi-sentence red highlights as one annotation while mapping every sentence index to the same annotation ID for deletion.
- Update sentence splitting so colon/semicolon do not become hard sentence boundaries.
- Add selection intersection detection and batch red toggling for multi-line selections.
- Keep `Command-Z` working for single and batch red actions.

Acceptance:

- Swift compiles with Cocoa/WebKit/AVFoundation/Speech.
- Single sentence red highlight still saves/restores.
- Multi-sentence selection posts `indexes` and persists through Reader API.
- Existing `reader.annotations` schema remains unchanged.
- Saved note markers restore when a chapter loads.
- Clicking a note-marked sentence opens the saved note.
- Double-click still opens the note editor.
- Context menu/two-finger tap still prevents the default browser menu.
- Colon and semicolon are not listed as sentence-boundary characters.

### `scripts/sentence_reader_annotation_core_v2_static_smoke.py`

Add this file.

Work:

- Static-check the new contract markers in the native Swift reader.
- Verify batch selection, note preview, full annotation restore, note marker styling, and non-colon sentence boundary markers exist.

Acceptance:

- Running the script prints `annotation core v2 static PASS`.

### `scripts/v18_reading_stability_acceptance.sh`

Adjust this file.

Work:

- Include the Annotation Core V2 static smoke in the V1.8 reading-stability gate.

Acceptance:

- `scripts/v18_reading_stability_acceptance.sh` fails if annotation core markers are removed.

### `scripts/check_native_reader.py`

Adjust this file.

Work:

- Add native reader contract markers for Annotation Core V2.

Acceptance:

- Existing native reader smoke protects note preview, batch red marking, and full annotation restore.

### `scripts/reader_stability_static_smoke.py`

Adjust this file.

Work:

- Add reading-stability markers for the new sentence boundary and selection logic.

Acceptance:

- Reading-stability smoke catches regressions in multi-line marking and note marker restore.

### `scripts/sentence_reader_product_static_smoke.py`

Adjust this file.

Work:

- Add product static markers so V2 product checks include the annotation core.

Acceptance:

- Product static smoke fails if the app falls back to red-only annotation restore or loses note preview.

### `docs/current_status.md`

Adjust this file.

Work:

- Record Annotation Core V2 as a V1.8 product hotfix.
- Be explicit that this fixes reading interaction quality, not iPad/LAN access.

Acceptance:

- Status doc tells the next operator what changed and what is still outside scope.

### `docs/product_roadmap.md`

Adjust this file.

Work:

- Add Annotation Core V2 to the current priority and V1.8 stability section.
- Keep LAN/iPad access as a later stage after local annotation correctness.

Acceptance:

- Roadmap reflects the correct sequence: local reading correctness first, network access second.

## Out of Scope For This Round

- No database schema migration.
- No iPad/LAN web reader.
- No PDF annotation expansion.
- No AI summary changes.
- No Readium engine swap.

## Manual Acceptance Script

After implementation, use a real EPUB and verify:

1. Drag-select multiple wrapped lines, two-finger tap/right-click, and all covered sentences become red.
2. Use `Command-Z`; the batch highlight returns to the previous state.
3. Add a note by double-clicking a sentence.
4. Close and reopen the chapter; the sentence has a note marker.
5. Single-click the note-marked sentence; the saved note appears.
6. Sentences containing `：`, `:`, `；`, `;`, quotes, or brackets are not split in the middle just because of those characters.

