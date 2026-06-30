#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V2.0Q V2.0P gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20p_first_run_preflight_acceptance.sh"

echo "== V2.0Q runtime settings static smoke =="
"$PYTHON" "$ROOT/scripts/sentence_reader_runtime_settings_static_smoke.py"

echo "== V2.0Q package app with runtime settings =="
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "== V2.0Q first-run preflight report =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_first_run_preflight.py" \
  --require-postgres-decision \
  --require-runtime-bootstrap \
  --require-first-run-ready \
  --require-funasr-configurable \
  --output "$ROOT/reports/sentence_reader_first_run_preflight_report.json" \
  --markdown "$ROOT/reports/sentence_reader_first_run_preflight_report.md"

echo "== V2.0Q product static contract =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_static_smoke.py"

echo "== V2.0Q Swift native compile =="
swiftc "$ROOT/Probe/NativeSentenceReader/SentenceReaderNative.swift" \
  -o "$ROOT/build/SentenceReaderNative" \
  -framework Cocoa \
  -framework WebKit \
  -framework AVFoundation \
  -framework Speech

echo "V2.0Q runtime settings acceptance PASS"
