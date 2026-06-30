#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"
API_PID=""

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

cleanup() {
  if [ -n "$API_PID" ]; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

api_health() {
  "$PYTHON" - <<'PY'
import httpx
try:
    r = httpx.get("http://127.0.0.1:18180/health", timeout=1.0)
    raise SystemExit(0 if r.status_code == 200 and r.json().get("ok") else 1)
except Exception:
    raise SystemExit(1)
PY
}

echo "== V1.7 V1.6 gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v16_export_acceptance.sh"

echo "== V1.7 static voice-note contract =="
python3 "$ROOT/scripts/check_native_reader.py"
python3 "$ROOT/scripts/sentence_reader_funasr_warmup_static_smoke.py"
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_api_static_smoke.py"

echo "== V1.7 Swift compile/package =="
swiftc "$ROOT/Probe/NativeSentenceReader/SentenceReaderNative.swift" \
  -o /tmp/SentenceReaderNativeV17Check \
  -framework Cocoa \
  -framework WebKit \
  -framework AVFoundation \
  -framework Speech
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "== V1.7 audio-note API runtime =="
if ! api_health; then
  PATH="$PG_BIN:$PATH" "$ROOT/scripts/run_reader_api.sh" >/tmp/sentence-reader-v17-api.log 2>&1 &
  API_PID="$!"
  for _ in $(seq 1 30); do
    if api_health; then
      break
    fi
    sleep 0.2
  done
fi
api_health
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_api_audio_notes_smoke.py"

echo "V1.7 voice-note acceptance PASS"
