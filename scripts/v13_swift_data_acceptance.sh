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

echo "== V1.3 V1.2 data foundation gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v12_data_acceptance.sh"

echo "== V1.3 native reader static contract =="
python3 "$ROOT/scripts/check_native_reader.py"

echo "== V1.3 Swift compile =="
swiftc "$ROOT/Probe/NativeSentenceReader/SentenceReaderNative.swift" \
  -o /tmp/SentenceReaderNativeV13Check \
  -framework Cocoa \
  -framework WebKit \
  -framework AVFoundation \
  -framework Speech

echo "== V1.3 package app =="
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "== V1.3 Reader API HTTP runtime =="
if ! api_health; then
  PATH="$PG_BIN:$PATH" "$ROOT/scripts/run_reader_api.sh" >/tmp/sentence-reader-v13-api.log 2>&1 &
  API_PID="$!"
  for _ in $(seq 1 30); do
    if api_health; then
      break
    fi
    sleep 0.2
  done
fi
api_health
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_api_http_smoke.py"

echo "V1.3 Swift data acceptance PASS"
