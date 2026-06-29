-- Sentence Reader vocabulary and context lookup foundation.
-- Safe to re-run: creates vocabulary tables/indexes if they do not exist.

CREATE TABLE IF NOT EXISTS reader.lexemes (
  id TEXT PRIMARY KEY,
  lemma TEXT NOT NULL,
  surface TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'en',
  part_of_speech TEXT,
  phonetic TEXT,
  short_definition TEXT,
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (language, lemma, surface)
);

CREATE TABLE IF NOT EXISTS reader.book_word_occurrences (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES reader.books(id) ON DELETE CASCADE,
  sentence_id TEXT REFERENCES reader.sentences(id) ON DELETE SET NULL,
  lexeme_id TEXT REFERENCES reader.lexemes(id) ON DELETE SET NULL,
  surface TEXT NOT NULL,
  lemma TEXT,
  english_sentence TEXT NOT NULL,
  chinese_sentence TEXT,
  chapter_title TEXT,
  chapter_locator TEXT NOT NULL,
  sentence_index INTEGER NOT NULL DEFAULT 0,
  occurrence_index INTEGER NOT NULL DEFAULT 0,
  position JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (book_id, chapter_locator, sentence_index, surface, occurrence_index)
);

CREATE TABLE IF NOT EXISTS reader.book_vocab_items (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES reader.books(id) ON DELETE CASCADE,
  lexeme_id TEXT REFERENCES reader.lexemes(id) ON DELETE SET NULL,
  surface TEXT NOT NULL,
  lemma TEXT,
  context_meaning TEXT,
  meaning_source TEXT NOT NULL DEFAULT 'none',
  alignment_status TEXT NOT NULL DEFAULT 'unknown',
  alignment_reason TEXT,
  representative_sentence_en TEXT,
  representative_sentence_zh TEXT,
  occurrence_count INTEGER NOT NULL DEFAULT 0,
  chapter_count INTEGER NOT NULL DEFAULT 0,
  score DOUBLE PRECISION NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'candidate'
    CHECK (status IN ('candidate', 'saved', 'reviewing', 'known', 'ignored')),
  user_note TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (book_id, lemma, surface)
);

CREATE TABLE IF NOT EXISTS reader.user_vocab_items (
  id TEXT PRIMARY KEY,
  lexeme_id TEXT REFERENCES reader.lexemes(id) ON DELETE SET NULL,
  surface TEXT NOT NULL,
  lemma TEXT,
  mastery_level INTEGER NOT NULL DEFAULT 0,
  next_review_at TIMESTAMPTZ,
  last_reviewed_at TIMESTAMPTZ,
  review_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (lemma, surface)
);

CREATE TABLE IF NOT EXISTS reader.book_glossary (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES reader.books(id) ON DELETE CASCADE,
  term TEXT NOT NULL,
  meaning_zh TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'user',
  confidence DOUBLE PRECISION NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (book_id, term)
);

CREATE TABLE IF NOT EXISTS reader.lookup_events (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES reader.books(id) ON DELETE CASCADE,
  sentence_id TEXT REFERENCES reader.sentences(id) ON DELETE SET NULL,
  surface TEXT NOT NULL,
  lemma TEXT,
  event_kind TEXT NOT NULL
    CHECK (event_kind IN ('lookup', 'play_word', 'play_sentence', 'save', 'mark_known', 'mark_unknown', 'edit_meaning')),
  context JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reader_lexemes_lemma ON reader.lexemes(language, lemma);
CREATE INDEX IF NOT EXISTS idx_reader_word_occurrences_book_lemma ON reader.book_word_occurrences(book_id, lemma);
CREATE INDEX IF NOT EXISTS idx_reader_word_occurrences_sentence ON reader.book_word_occurrences(book_id, chapter_locator, sentence_index);
CREATE INDEX IF NOT EXISTS idx_reader_book_vocab_book_score ON reader.book_vocab_items(book_id, score DESC, occurrence_count DESC);
CREATE INDEX IF NOT EXISTS idx_reader_book_vocab_book_status ON reader.book_vocab_items(book_id, status, score DESC);
CREATE INDEX IF NOT EXISTS idx_reader_book_glossary_book_term ON reader.book_glossary(book_id, term);
CREATE INDEX IF NOT EXISTS idx_reader_lookup_events_book_created ON reader.lookup_events(book_id, created_at DESC);

ALTER TABLE reader.book_vocab_items ADD COLUMN IF NOT EXISTS alignment_status TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE reader.book_vocab_items ADD COLUMN IF NOT EXISTS alignment_reason TEXT;
