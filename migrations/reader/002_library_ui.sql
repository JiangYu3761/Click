-- Sentence Reader library UI state.
-- Safe to re-run: non-destructive UI state only; does not delete books, files, notes, or positions.

CREATE TABLE IF NOT EXISTS reader.library_state (
  book_id TEXT PRIMARY KEY REFERENCES reader.books(id) ON DELETE CASCADE,
  hidden BOOLEAN NOT NULL DEFAULT false,
  source TEXT NOT NULL DEFAULT 'reader_api',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reader_library_state_hidden ON reader.library_state(hidden, updated_at);
