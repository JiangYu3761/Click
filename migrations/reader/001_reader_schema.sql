-- Sentence Reader V1.2 PostgreSQL data foundation.
-- Safe to re-run: creates schema/tables/indexes if they do not exist.

CREATE SCHEMA IF NOT EXISTS reader;

CREATE TABLE IF NOT EXISTS reader.books (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT,
  source_kind TEXT NOT NULL CHECK (source_kind IN ('epub', 'pdf', 'txt', 'markdown')),
  book_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_opened_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS reader.book_files (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES reader.books(id) ON DELETE CASCADE,
  file_path TEXT NOT NULL,
  file_kind TEXT NOT NULL CHECK (file_kind IN ('epub', 'pdf', 'txt', 'markdown', 'audio', 'export')),
  file_hash TEXT,
  byte_size BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (book_id, file_path)
);

CREATE TABLE IF NOT EXISTS reader.chapters (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES reader.books(id) ON DELETE CASCADE,
  chapter_index INTEGER NOT NULL,
  title TEXT,
  locator TEXT NOT NULL,
  href TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (book_id, chapter_index),
  UNIQUE (book_id, locator)
);

CREATE TABLE IF NOT EXISTS reader.sentences (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES reader.books(id) ON DELETE CASCADE,
  chapter_id TEXT REFERENCES reader.chapters(id) ON DELETE SET NULL,
  chapter_locator TEXT NOT NULL,
  sentence_index INTEGER NOT NULL,
  sentence_text_hash TEXT NOT NULL,
  text TEXT NOT NULL,
  range_locator JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (book_id, chapter_locator, sentence_index, sentence_text_hash)
);

CREATE TABLE IF NOT EXISTS reader.annotations (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES reader.books(id) ON DELETE CASCADE,
  sentence_id TEXT REFERENCES reader.sentences(id) ON DELETE SET NULL,
  kind TEXT NOT NULL CHECK (kind IN ('note', 'red_highlight')),
  source_text TEXT NOT NULL,
  note_text TEXT,
  color TEXT,
  chapter_title TEXT,
  chapter_locator TEXT NOT NULL,
  range_locator JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reader.reading_positions (
  book_id TEXT PRIMARY KEY REFERENCES reader.books(id) ON DELETE CASCADE,
  chapter_id TEXT REFERENCES reader.chapters(id) ON DELETE SET NULL,
  chapter_locator TEXT NOT NULL,
  page_index INTEGER NOT NULL DEFAULT 0,
  total_pages INTEGER NOT NULL DEFAULT 1,
  page_ratio DOUBLE PRECISION NOT NULL DEFAULT 0,
  locator JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reader.audio_notes (
  id TEXT PRIMARY KEY,
  annotation_id TEXT REFERENCES reader.annotations(id) ON DELETE SET NULL,
  book_id TEXT NOT NULL REFERENCES reader.books(id) ON DELETE CASCADE,
  audio_path TEXT NOT NULL,
  audio_hash TEXT,
  duration_seconds DOUBLE PRECISION,
  provider TEXT NOT NULL DEFAULT 'funasr',
  transcript TEXT,
  raw_result JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL CHECK (status IN ('pending', 'transcribed', 'failed')) DEFAULT 'pending',
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reader.exports (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES reader.books(id) ON DELETE CASCADE,
  export_kind TEXT NOT NULL CHECK (export_kind IN ('markdown', 'json')),
  output_path TEXT NOT NULL,
  annotation_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reader.sync_events (
  id TEXT PRIMARY KEY,
  source_kind TEXT NOT NULL CHECK (source_kind IN ('annotation', 'book', 'position', 'audio_note', 'export')),
  source_id TEXT NOT NULL,
  target_system TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL CHECK (status IN ('pending', 'synced', 'failed')) DEFAULT 'pending',
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reader_book_files_book ON reader.book_files(book_id);
CREATE INDEX IF NOT EXISTS idx_reader_chapters_book_index ON reader.chapters(book_id, chapter_index);
CREATE INDEX IF NOT EXISTS idx_reader_sentences_book_chapter ON reader.sentences(book_id, chapter_locator, sentence_index);
CREATE INDEX IF NOT EXISTS idx_reader_annotations_book_chapter ON reader.annotations(book_id, chapter_locator, created_at);
CREATE INDEX IF NOT EXISTS idx_reader_annotations_sentence ON reader.annotations(sentence_id);
CREATE INDEX IF NOT EXISTS idx_reader_audio_notes_book_status ON reader.audio_notes(book_id, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_reader_sync_events_status ON reader.sync_events(target_system, status, updated_at);
