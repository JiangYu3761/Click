#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V2.0R V2.0Q gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20q_runtime_settings_acceptance.sh"

echo "== V2.0R first-run guide static smoke =="
"$PYTHON" "$ROOT/scripts/sentence_reader_first_run_guide_static_smoke.py"

echo "== V2.0R product static contract =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_static_smoke.py"

echo "== V2.0R package app with first-run guide =="
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "== V2.0R Swift native compile =="
swiftc "$ROOT/Probe/NativeSentenceReader/SentenceReaderNative.swift" \
  -o "$ROOT/build/SentenceReaderNative" \
  -framework Cocoa \
  -framework WebKit \
  -framework AVFoundation \
  -framework Speech

echo "V2.0R first-run guide acceptance PASS"
