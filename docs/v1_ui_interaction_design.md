# Sentence Reader Mac V1 UI and Interaction Design

## UI Principle

Sentence Reader is a close-reading workspace, not a decorative bookshelf.

The first screen should immediately support reading, sentence focus, annotation, and export. Every visible control should help one of these jobs:

1. Open a book.
2. Navigate the current book.
3. Annotate the current sentence.
4. Review notes.
5. Export notes.

## Window Structure

The V1 window has four stable regions:

| Region | Purpose | V1 Contents |
| --- | --- | --- |
| Top toolbar | Book-level actions and status | Open, pinned reader entry, export, sync status |
| Left sidebar | Navigation | Books, table of contents, notes tabs |
| Center reader | Primary reading surface | EPUB text, sentence focus, highlight decoration |
| Right notes rail | Current book annotations | Notes list, selected sentence detail, export preview |

The right notes rail can collapse. The left sidebar should stay available because table of contents and notes are core workflows.

## Layout

Recommended desktop dimensions:

- Minimum window width: 1040 px.
- Left sidebar: 240 px.
- Center reader: flexible, minimum 520 px.
- Right notes rail: 300 px, collapsible.
- Toolbar height: 42 px in the current probe; keep it compact so the reader uses vertical space.

Compact width behavior:

- Collapse the right notes rail first.
- Keep left sidebar as a narrow icon/tab rail when needed.
- Never squeeze the reader below comfortable line length.

## Top Toolbar

Controls:

- Open: import EPUB/PDF.
- Contents: open a compact chapter picker without permanently taking reading width.
- Pinned reader entry: always visible, returns to the current reading surface.
- Export: export Markdown notes for the current book.
- Notes rail toggle.
- Sync status: local only / queued for Hermes / synced / failed.
- Current book title.

Do not add AI summary, cloud sync, library marketing, or decorative counters in V1.

## Left Sidebar

Tabs:

1. Books
2. Contents
3. Notes

Books tab:

- Recently opened books.
- File status: available / missing.

Contents tab:

- EPUB table of contents.
- Current chapter indicator.

Notes tab:

- Filters: all, notes, red highlights.
- Search within current book notes.

## Center Reader

Reader behavior:

- Single click: focus sentence without persistent changes.
- Double click: open note editor for the whole sentence.
- Secondary click / two-finger tap: toggle red highlight for the whole sentence.
- `Command+Z`: undo the latest persistent reading action, starting with red highlight toggle in V1.
- Contents button: show EPUB table of contents and jump to the selected chapter.
- Reading position: remember the latest chapter and page locally, then restore it on next launch.
- Voice note input: the note editor includes a record button. It records a short WAV, tries local FunASR first, then falls back to system Chinese speech recognition when needed.
- Horizontal swipe: turn page.
- Horizontal swipe must lock direction per gesture and ignore post-turn trackpad inertia, so one physical swipe cannot accidentally turn back.
- Reaching the last page of the current EPUB spine item and turning forward enters the next spine item.
- Reaching the first page of the current EPUB spine item and turning backward enters the previous spine item at its last page.
- Vertical swipe / wheel: ignored in the reader; V1 should not use continuous vertical scrolling for EPUB reading.
- Text selection: preserve default selection; advanced selected-range annotations are later.

Reader visual baseline:

- Background: black.
- Text font request: Microsoft YaHei / 微软雅黑 first, then PingFang SC / Heiti SC fallback when the font is unavailable on macOS.
- Top and bottom chrome should stay thin; the reading text should occupy nearly the full vertical workspace with minimal margins.
- The bottom bar is status only, not a large control panel.
- Full-screen / wide windows should use a two-column paged layout so both left and right sides contain text instead of empty black space.
- EPUB image blocks should stay inside the page viewport, keep aspect ratio, and avoid splitting across page columns when possible.
- Page turn animation should feel book-like: directional light/shadow, page-edge motion, and a controlled easing curve. It should not be an instant slide.

Visual states:

| State | Visual Treatment |
| --- | --- |
| Normal sentence | Light text on black background |
| Focused sentence | Quiet blue background tint |
| Red highlight | Soft red background, readable on black mode |
| Sentence with note | Small margin dot or note indicator |
| Hovered sentence | Very subtle background, no layout shift |

The reader must not reflow text when focus, hover, or highlight changes.

## Note Editor

Triggered by double-clicking a sentence.

Fields:

- Source sentence: read-only.
- Note text: editable.
- Voice input button: start recording, stop and transcribe, then insert recognized text into the note field without auto-saving.
- Optional tags.
- Save and cancel.

Behavior:

- Save with Command+Return.
- Escape cancels.
- Empty note on an existing note asks for delete confirmation later; V1 can simply keep the old note until explicit delete exists.
- Voice transcription must stay inside this note editor in V1. Do not add hidden reading-surface gestures until permission, recording, and error states are stable.

## Secondary Click Menu

Triggered by right click or two-finger tap on a sentence.

V1 menu:

- Toggle red highlight.
- Add/edit note.
- Copy sentence.
- Copy sentence and note, if a note exists.

Do not overload the menu with AI actions in V1.

## Right Notes Rail

Contents:

- Current book annotation list.
- Each item shows type, short source sentence, note excerpt, chapter.
- Selecting a note scrolls the reader to the sentence.
- Export preview button can show the generated Markdown later.

The rail is for working memory while reading. It is not a full knowledge base in V1.

## Markdown Export Shape

```markdown
# Book Title

## Chapter Title

> Source sentence

Note:
User note text.

Tags:
#tag

Metadata:
- kind: note
- locator: ...
```

## Keyboard Shortcuts

V1:

- `Command+O`: open book.
- `Command+R`: return to reading surface.
- `Command+E`: export Markdown.
- `Command+Return`: save note editor.
- `Escape`: close note editor or menu.
- `Command+Option+N`: toggle notes rail.

## Accessibility and Input Rules

- The context menu must also be reachable through Control-click.
- Highlight colors must keep text readable.
- Keyboard navigation should be possible later, but V1 prioritizes mouse/trackpad reading.

## V1 UI Acceptance

The UI is acceptable when:

- The first screen is the reading workspace, not a landing page.
- A user can infer where to open a book, read, annotate, review notes, and export.
- Single-click focus, double-click note, and secondary-click red highlight are represented in the prototype and wired in the Readium probe.
- Notes rail can be conceptually collapsed.
- No V1 screen depends on Hermes being online.
- The bundled sample EPUB opens without asking for Desktop permission.
- The native reader shell reads EPUB `spine` order from OPF first, then falls back to HTML filename order.
- The native reader shell reads EPUB `toc.ncx` for the chapter picker first, then falls back to generated spine entries.
- The native reader shell persists reading position as chapter relative path, page index, and page ratio, so reopening the app returns near the last page.
- Horizontal swipe at the page edge moves to the previous/next spine item.
- Image-heavy pages keep images contained within the visible page instead of forcing oversized blank or broken text layout.

## Current Engine Boundary

The packaged app currently uses a native AppKit/WKWebView shell for the visible reading surface while the Readium probe remains a dependency and feasibility track. This is acceptable for V1 interaction validation, but the final EPUB engine should move chapter navigation, locators, and decorations onto Readium's official spine/locator APIs once the Mac Catalyst navigator interaction layer is stable.
