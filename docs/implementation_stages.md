# Implementation Stages

## Stage 0: Readium Technical Probe

Input:

- SwiftPM project.
- Readium dependency candidate.
- Small sentence-level annotation model.

Output:

- Buildable probe package.
- Tests for sentence splitting and annotation payload round trip.
- Decision on whether Readium is acceptable.

Acceptance:

- `swift test` passes for local models.
- Readium dependency resolution result is documented.
- Core risk is classified as low, medium, or high.

## Stage 1: EPUB Reader Shell

Input:

- Accepted reading engine.
- Mac app project.

Output:

- Open EPUB.
- Show reading surface.
- Show table of contents.
- Save reading position.

Acceptance:

- A real EPUB can be read for 15 minutes.
- Reopening restores the location.

## Stage 2: Sentence-Level Annotation

Input:

- EPUB reader shell.
- Sentence range adapter.

Output:

- Double-click note.
- Secondary-click red highlight.
- Restart-safe annotation restore.

Acceptance:

- 50 annotations remain stable after restart.
- Highlight and note edits do not modify the original EPUB.

## Stage 3: Notes and Export

Input:

- Local annotation database.

Output:

- Notes sidebar.
- Markdown export.
- Hermes sync payload shape.

Acceptance:

- Export order is chapter-stable.
- Markdown contains source sentence, note, tags, and locator metadata.

## Stage 4: Real Reading Test

Input:

- One real EPUB book.

Output:

- Bug list and polish pass.

Acceptance:

- 30-minute reading session.
- No lost notes.
- No severe UI interruption.

