#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V1.8 V1.7 gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v17_voice_acceptance.sh"

echo "== V1.8 static reading-stability contract =="
python3 "$ROOT/scripts/check_native_reader.py"
python3 "$ROOT/scripts/reader_stability_static_smoke.py"
python3 "$ROOT/scripts/sentence_reader_immersive_chrome_static_smoke.py"
python3 "$ROOT/scripts/sentence_reader_annotation_core_v2_static_smoke.py"

echo "== V1.8 Python compile/static =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_api_static_smoke.py"
"$PYTHON" -m compileall "$ROOT/reader_api" "$ROOT/scripts" "$ROOT/tests"

echo "== V1.8 Swift compile/package =="
swiftc "$ROOT/Probe/NativeSentenceReader/SentenceReaderNative.swift" \
  -o /tmp/SentenceReaderNativeV18Check \
  -framework Cocoa \
  -framework WebKit \
  -framework AVFoundation \
  -framework Speech
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "V1.8 reading stability acceptance PASS"
