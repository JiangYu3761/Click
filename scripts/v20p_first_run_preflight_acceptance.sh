#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V2.0P V2.0O gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20o_runtime_bootstrap_acceptance.sh"

echo "== V2.0P package with first-run scripts =="
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "== V2.0P runtime config smoke =="
"$PYTHON" "$ROOT/scripts/sentence_reader_runtime_config.py" --print-funasr >/tmp/sentence-reader-runtime-config-smoke.json

echo "== V2.0P first-run preflight smoke =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_first_run_preflight_smoke.py"

echo "== V2.0P first-run preflight report =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_first_run_preflight.py" \
  --require-postgres-decision \
  --require-runtime-bootstrap \
  --require-first-run-ready \
  --require-funasr-configurable \
  --output "$ROOT/reports/sentence_reader_first_run_preflight_report.json" \
  --markdown "$ROOT/reports/sentence_reader_first_run_preflight_report.md"

echo "== V2.0P product diagnostics with first-run preflight =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_diagnostics.py" \
  --require-package \
  --output "$ROOT/reports/sentence_reader_product_diagnostics_report.json"

echo "== V2.0P product static contract =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_static_smoke.py"

echo "== V2.0P Swift native compile =="
swiftc "$ROOT/Probe/NativeSentenceReader/SentenceReaderNative.swift" \
  -o "$ROOT/build/SentenceReaderNative" \
  -framework Cocoa \
  -framework WebKit \
  -framework AVFoundation \
  -framework Speech

echo "V2.0P first-run preflight acceptance PASS"
