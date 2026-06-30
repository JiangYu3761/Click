# Life-study Frontend Glossary Integration

Updated: 2026-06-30

## What Works Now

Sentence Reader can show Life-study-specific meanings like normal word lookup when the current book is recognized as Life-study/生命读经.

The latest needs-review-derived batch applied 15 B-grade terms:

- `authority -> 权柄`
- `vision -> 异象`
- `ascension -> 升天`
- `parable -> 比喻`
- `misused -> 误用`
- `holy -> 神圣的`
- `building -> 建筑`
- `riches -> 财富`
- `pray -> 祈祷`
- `peace -> 和平`
- `prayer -> 祈祷`
- `testify -> 作证`
- `function -> 功能`
- `local -> 地方性的`
- `preach -> 讲道`

## Data Source

This batch comes only from the 2,205 `needs_manual_review` adjudication outputs:

- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_corrected_learning_candidate.csv`
- `reports/lifestudy_vocab_corpus/lifestudy_needs_review_learning_only.csv`

It does not use:

- the old 26 front-end terms
- the 4,116 auto-accepted learning rows
- rejected rows
- ordinary dictionary meanings as final meanings
- statistical candidates as final meanings

## Storage

Applied terms are stored in:

`reader.domain_glossary_entries`

Important fields:

- `domain = 'lifestudy'`
- `volume = 'All'`
- `quality_grade = 'B'`
- `source_title = 'Life-study Needs-review Frontend V1'`
- `evidence_en`
- `evidence_zh`
- `metadata.source = 'lifestudy_needs_review_frontend_v1'`

The batch never writes to:

`reader.dictionary_entries`

## Lookup Order

For Life-study/生命读经 books:

1. user correction
2. current book glossary
3. Life-study domain glossary
4. ordinary local dictionary
5. online or other fallback

For ordinary books:

- Life-study domain glossary is skipped.

## Frontend Display

Mac native lookup and iPad/LAN lookup display:

- word
- Chinese meaning
- source as Life-study vocabulary
- source title / volume / page when available
- English evidence
- Chinese evidence

The LAN card also includes a copy action for the lookup card.

## Verification

Run:

- `.venv-reader-api/bin/python scripts/lifestudy_needs_review_frontend_smoke.py`
- `.venv-reader-api/bin/python scripts/lifestudy_needs_review_frontend_applied_smoke.py`
- `.venv-reader-api/bin/python scripts/lifestudy_needs_review_frontend_live_lookup_smoke.py`
- `.venv-reader-api/bin/python scripts/lifestudy_needs_review_frontend_ui_static_smoke.py`

Expected current result:

- Top300 queue from the 2,205 adjudication result
- 15 applied B-grade terms
- 0 writes to `reader.dictionary_entries`
- Life-study book lookup uses `lifestudy_domain_glossary`
- ordinary book lookup does not use `lifestudy_domain_glossary`
