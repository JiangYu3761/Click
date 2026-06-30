#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V2.0L V2.0K gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20k_approval_ux_acceptance.sh"

echo "== V2.0L dashboard API smoke =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_api_cognitive_operator_smoke.py"

echo "== V2.0L Swift dashboard compile =="
swiftc "$ROOT/Probe/NativeSentenceReader/SentenceReaderNative.swift" \
  -o /tmp/SentenceReaderNativeV20LAcceptance \
  -framework Cocoa \
  -framework WebKit \
  -framework AVFoundation \
  -framework Speech

echo "== V2.0L Reader API static contract =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_api_static_smoke.py"

echo "== V2.0L product static contract =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_static_smoke.py"

echo "V2.0L cognitive dashboard acceptance PASS"
