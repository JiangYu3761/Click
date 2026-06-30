#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V2.0K V2.0J gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20j_explicit_approval_acceptance.sh"

echo "== V2.0K Swift approval UX compile =="
swiftc "$ROOT/Probe/NativeSentenceReader/SentenceReaderNative.swift" \
  -o /tmp/SentenceReaderNativeV20KAcceptance \
  -framework Cocoa \
  -framework WebKit \
  -framework AVFoundation \
  -framework Speech

echo "== V2.0K explicit approval API smoke =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_api_cognitive_operator_smoke.py"

echo "== V2.0K product static contract =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_static_smoke.py"

echo "V2.0K approval UX acceptance PASS"
