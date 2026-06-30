-- Sentence Reader lightweight dictionary fallback.
-- This is intentionally small: book context and user corrections still win.

CREATE TABLE IF NOT EXISTS reader.dictionary_entries (
  id TEXT PRIMARY KEY,
  language TEXT NOT NULL DEFAULT 'en',
  term TEXT NOT NULL,
  lemma TEXT,
  phonetic TEXT,
  part_of_speech TEXT,
  definition_zh TEXT NOT NULL,
  definition_en TEXT,
  source TEXT NOT NULL DEFAULT 'seed',
  priority INTEGER NOT NULL DEFAULT 100,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (language, term, source)
);

CREATE INDEX IF NOT EXISTS idx_reader_dictionary_entries_term
  ON reader.dictionary_entries(language, lower(term));

CREATE INDEX IF NOT EXISTS idx_reader_dictionary_entries_lemma
  ON reader.dictionary_entries(language, lower(coalesce(lemma, '')));

INSERT INTO reader.dictionary_entries (
  id, language, term, lemma, part_of_speech, definition_zh, source, priority, metadata, created_at, updated_at
)
VALUES
  ('dict_seed_economy', 'en', 'economy', 'economy', 'noun', '经纶；安排', 'seed_minimal', 10, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_dispensing', 'en', 'dispensing', 'dispense', 'noun/verb', '分赐；分配', 'seed_minimal', 10, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_ministry', 'en', 'ministry', 'ministry', 'noun', '职事；服事', 'seed_minimal', 10, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_fellowship', 'en', 'fellowship', 'fellowship', 'noun', '交通；相交', 'seed_minimal', 10, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_fellowshipped', 'en', 'fellowshipped', 'fellowship', 'verb', '交通；商量', 'seed_minimal', 20, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_organic', 'en', 'organic', 'organic', 'adjective', '生机的；有机的', 'seed_minimal', 20, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_constitute', 'en', 'constitute', 'constitute', 'verb', '构成；组成', 'seed_minimal', 20, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_constituted', 'en', 'constituted', 'constitute', 'verb', '构成；组成', 'seed_minimal', 20, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_constituting', 'en', 'constituting', 'constitute', 'verb', '构成；组成', 'seed_minimal', 20, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_mingle', 'en', 'mingle', 'mingle', 'verb', '调和；混合', 'seed_minimal', 20, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_indwell', 'en', 'indwell', 'indwell', 'verb', '内住', 'seed_minimal', 20, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_transformation', 'en', 'transformation', 'transformation', 'noun', '变化；转变', 'seed_minimal', 30, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_transforming', 'en', 'transforming', 'transform', 'verb', '变化；转变', 'seed_minimal', 30, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_transforms', 'en', 'transforms', 'transform', 'verb', '变化；改变', 'seed_minimal', 30, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_expression', 'en', 'expression', 'expression', 'noun', '彰显；表达', 'seed_minimal', 30, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_expressions', 'en', 'expressions', 'expression', 'noun', '表达；说法', 'seed_minimal', 40, '{"domain":"general"}'::jsonb, now(), now()),
  ('dict_seed_consummation', 'en', 'consummation', 'consummation', 'noun', '终极完成；完成', 'seed_minimal', 30, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_righteousness', 'en', 'righteousness', 'righteousness', 'noun', '公义；义', 'seed_minimal', 30, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_grace', 'en', 'grace', 'grace', 'noun', '恩典', 'seed_minimal', 30, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_saint', 'en', 'saint', 'saint', 'noun', '圣徒；圣者', 'seed_minimal', 40, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_eternal', 'en', 'eternal', 'eternal', 'adjective', '永远的；永恒的', 'seed_minimal', 40, '{"domain":"general"}'::jsonb, now(), now()),
  ('dict_seed_divine', 'en', 'divine', 'divine', 'adjective', '神圣的', 'seed_minimal', 40, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_prayer', 'en', 'prayer', 'prayer', 'noun', '祷告', 'seed_minimal', 40, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_spirit', 'en', 'spirit', 'spirit', 'noun', '灵；精神', 'seed_minimal', 50, '{"domain":"book_term"}'::jsonb, now(), now()),
  ('dict_seed_body', 'en', 'body', 'body', 'noun', '身体；主体', 'seed_minimal', 50, '{"domain":"book_term"}'::jsonb, now(), now())
ON CONFLICT (language, term, source) DO UPDATE
SET lemma = EXCLUDED.lemma,
    phonetic = EXCLUDED.phonetic,
    part_of_speech = EXCLUDED.part_of_speech,
    definition_zh = EXCLUDED.definition_zh,
    definition_en = EXCLUDED.definition_en,
    priority = EXCLUDED.priority,
    metadata = EXCLUDED.metadata,
    updated_at = now();
