# Sentence Reader Mac V1 Design

## Product Definition

Sentence Reader is a Mac local reading app for sentence-level close reading and cognitive note capture.

The core job is:

1. Read EPUB books comfortably.
2. Treat a sentence as the default annotation unit.
3. Save every highlight and note as durable local data.
4. Export the reading result as Markdown.
5. Prepare structured payloads for future Hermes Cognitive OS ingestion.

## Non-Goals

V1 does not build:

- DRM import.
- Apple Books modification.
- Cloud sync.
- Mobile apps.
- AI summary buttons.
- A decorative bookshelf.
- Full PDF sentence-level annotation.
- Multiple reading engine experiments.

These are deliberately excluded because they distract from the product's core: sentence-level close reading.

## Technology Direction

- UI shell: SwiftUI + AppKit.
- Reading engine: Readium Swift Toolkit.
- Local storage: SQLite through GRDB.
- PDF basic support: Apple PDFKit, later phase.
- Hermes sync: adapter layer after V1 local loop is solid.

The stack should stay stable across V1/V2. Stages change feature depth, not the core architecture.

## Core Interaction

| Gesture | Unit | Result |
| --- | --- | --- |
| Single click | Sentence | Focus sentence, no persistent change |
| Double click | Sentence | Open note editor for the whole sentence |
| Secondary click / two-finger tap | Sentence | Toggle red highlight |
| Text selection | User-selected range | Reserved for later advanced annotation |

## Data Model

Books:

- `id`
- `title`
- `author`
- `file_path`
- `book_hash`
- `created_at`
- `last_opened_at`

Reading positions:

- `book_id`
- `locator_json`
- `updated_at`

Sentences:

- `id`
- `book_id`
- `chapter_locator`
- `sentence_index`
- `sentence_text_hash`
- `text`
- `locator_json`

Annotations:

- `id`
- `book_id`
- `sentence_id`
- `kind`: `note`, `red_highlight`
- `note_text`
- `color`
- `source_text`
- `locator_json`
- `created_at`
- `updated_at`

Hermes sync queue:

- `id`
- `annotation_id`
- `payload_json`
- `status`
- `last_error`
- `created_at`
- `updated_at`

## Stable Sentence ID

Sentence IDs must survive normal reopen operations.

Use:

`book_hash + chapter_locator + sentence_index + sentence_text_hash`

Do not rely only on chapter index and sentence number; EPUB content can be reflowed or corrected.

## V1 Acceptance

V1 is acceptable only when:

- An EPUB can be opened.
- The reader can restore the last position.
- Double-click can add a note to the whole sentence.
- Secondary click can toggle whole-sentence red highlight.
- Notes and highlights survive app restart.
- A note list shows all annotations for the current book.
- Markdown export is deterministic.
- The app can be used for a real 30-minute reading session without losing notes.

## Risk Register

| Risk | Why It Matters | V1 Response |
| --- | --- | --- |
| Readium click-to-range mapping is hard | It is the core interaction | Build probe before full app |
| EPUB sentence splitting is language-dependent | Chinese and English punctuation differ | Keep sentence boundary service isolated |
| PDF text order is unreliable | PDF is not natural sentence flow | PDF basic only in V1 |
| Hermes coupling can make reader fragile | Reading must work offline | Export/sync payload only in V1 |

