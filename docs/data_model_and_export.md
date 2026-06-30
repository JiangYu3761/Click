# Data Model and Export Contract

## Why This Exists

The reading engine can change, but the user's reading assets must not.

V1 therefore treats annotations as app-owned data:

- The original EPUB/PDF is never modified.
- Sentence identity is stable enough for reopen and export.
- Hermes sync is a payload queue, not a live dependency.

## Storage Contract

Schema:

```text
schema/v1_schema.sql
```

Tables:

- `books`
- `reading_positions`
- `sentences`
- `annotations`
- `exports`
- `hermes_sync_queue`

The schema is written as SQLite DDL. GRDB should implement this schema in the Mac app stage.

## Sentence Identity

Stable sentence ID:

```text
book_hash + chapter_locator + sentence_index + sentence_text_hash
```

This is not perfect if the book file changes, but it is strong enough for V1 local annotations.

## Annotation Types

V1 supports only:

- `note`
- `red_highlight`

Do not add more colors, AI summaries, or selected-range annotation types until EPUB sentence annotation is stable.

## Markdown Export Contract

Markdown export must be deterministic:

1. Book title.
2. Optional author.
3. Chapter groups sorted by chapter title/locator.
4. Annotations sorted by chapter locator and creation time.
5. Each annotation contains source sentence before commentary.
6. Metadata remains available for re-import or Hermes sync.

Shape:

```markdown
# Book Title

Author: Author Name

## Chapter Title

> Source sentence

Note:
User note text

Hermes hint:
- Preserve the source sentence before drawing conclusions.
- Extract reusable mental model only when the note contains a real judgment.

Metadata:
- id: ...
- kind: note
- chapter_locator: ...
- locator: ...
```

## Hermes Sync Contract

Hermes receives structured payloads using:

```text
sentence_reader.hermes_sync.v1
```

The reader should enqueue sync payloads locally first. It should not require Hermes to be online while reading.

## Current Swift Core Coverage

Implemented in `Probe/Sources/ReadiumProbe`:

- `SentenceBoundaryService`
- `AnnotationPayload`
- `HermesSyncPayload`
- `ReaderEngineAdapter`
- `ReaderAnnotation`
- `AnnotationRepository`
- `InMemoryAnnotationRepository`
- `MarkdownExporter`

Validated by:

```bash
cd Probe
swift run readium-probe
```

