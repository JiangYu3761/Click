PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS books (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT,
  file_path TEXT NOT NULL,
  book_hash TEXT NOT NULL UNIQUE,
  file_kind TEXT NOT NULL CHECK (file_kind IN ('epub', 'pdf', 'txt', 'markdown')),
  created_at TEXT NOT NULL,
  last_opened_at TEXT
);

CREATE TABLE IF NOT EXISTS reading_positions (
  book_hash TEXT PRIMARY KEY NOT NULL,
  locator_json TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (book_hash) REFERENCES books(book_hash) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sentences (
  id TEXT PRIMARY KEY,
  book_hash TEXT NOT NULL,
  chapter_locator TEXT NOT NULL,
  chapter_title TEXT,
  sentence_index INTEGER NOT NULL,
  sentence_text_hash TEXT NOT NULL,
  text TEXT NOT NULL,
  range_locator_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (book_hash, chapter_locator, sentence_index, sentence_text_hash),
  FOREIGN KEY (book_hash) REFERENCES books(book_hash) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS annotations (
  id TEXT PRIMARY KEY,
  book_hash TEXT NOT NULL,
  sentence_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('note', 'red_highlight')),
  source_text TEXT NOT NULL,
  note_text TEXT,
  color TEXT,
  chapter_title TEXT,
  chapter_locator TEXT NOT NULL,
  range_locator_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (book_hash) REFERENCES books(book_hash) ON DELETE CASCADE,
  FOREIGN KEY (sentence_id) REFERENCES sentences(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exports (
  id TEXT PRIMARY KEY,
  book_hash TEXT NOT NULL,
  export_kind TEXT NOT NULL CHECK (export_kind IN ('markdown')),
  output_path TEXT NOT NULL,
  annotation_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY (book_hash) REFERENCES books(book_hash) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hermes_sync_queue (
  id TEXT PRIMARY KEY,
  annotation_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'synced', 'failed')) DEFAULT 'pending',
  last_error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (annotation_id) REFERENCES annotations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_annotations_book_chapter ON annotations(book_hash, chapter_locator, created_at);
CREATE INDEX IF NOT EXISTS idx_annotations_sentence ON annotations(sentence_id);
CREATE INDEX IF NOT EXISTS idx_sentences_book_chapter ON sentences(book_hash, chapter_locator, sentence_index);
CREATE INDEX IF NOT EXISTS idx_hermes_sync_status ON hermes_sync_queue(status, updated_at);

