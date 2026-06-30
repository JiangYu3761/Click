#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V2.1 V2.0S gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20s_product_identity_acceptance.sh"

echo "== V2.1 iPad LAN static contract =="
python3 "$ROOT/scripts/sentence_reader_ipad_lan_static_smoke.py"
python3 "$ROOT/scripts/sentence_reader_interaction_contract_smoke.py"
python3 "$ROOT/scripts/sentence_reader_vocab_lookup_static_smoke.py"
python3 "$ROOT/scripts/check_native_reader.py"
python3 "$ROOT/scripts/sentence_reader_product_static_smoke.py"
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_api_static_smoke.py"

echo "== V2.1 iPad LAN API smoke =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_api_ipad_lan_smoke.py"

echo "== V2.1 Python compile/static =="
"$PYTHON" -m compileall "$ROOT/reader_api" "$ROOT/scripts" "$ROOT/tests"

echo "== V2.1 Swift compile/package =="
swiftc "$ROOT/Probe/NativeSentenceReader/SentenceReaderNative.swift" \
  -o /tmp/SentenceReaderNativeV21Check \
  -framework Cocoa \
  -framework WebKit \
  -framework AVFoundation \
  -framework Speech
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "V2.1 iPad LAN reader acceptance PASS"
