-- Sentence Reader Life-study/domain glossary boundary.
-- Safe to re-run: stores only quality-gated A/B domain meanings and never touches the general dictionary.

CREATE TABLE IF NOT EXISTS reader.domain_glossary_entries (
  id TEXT PRIMARY KEY,
  domain TEXT NOT NULL,
  volume TEXT,
  language TEXT NOT NULL DEFAULT 'en',
  term TEXT NOT NULL,
  lemma TEXT,
  meaning_zh TEXT NOT NULL,
  quality_grade TEXT NOT NULL CHECK (quality_grade IN ('A', 'B')),
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.9,
  source_title TEXT,
  source_pdf TEXT,
  source_page INTEGER,
  evidence_en TEXT NOT NULL,
  evidence_zh TEXT NOT NULL,
  occurrence_count INTEGER NOT NULL DEFAULT 0,
  score DOUBLE PRECISION NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'reviewing', 'hidden')),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (domain, volume, language, term)
);

CREATE INDEX IF NOT EXISTS idx_reader_domain_glossary_term
  ON reader.domain_glossary_entries(domain, language, lower(term), status);

CREATE INDEX IF NOT EXISTS idx_reader_domain_glossary_lemma
  ON reader.domain_glossary_entries(domain, language, lower(coalesce(lemma, '')), status);

CREATE INDEX IF NOT EXISTS idx_reader_domain_glossary_compact_term
  ON reader.domain_glossary_entries(domain, language, regexp_replace(lower(term), '[^a-z]', '', 'g'), status);
