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

echo "== V2.0C V2.0B gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20b_runtime_acceptance.sh"

echo "== V2.0C ensure Reader API runtime =="
if ! api_health; then
  PATH="$PG_BIN:$PATH" "$ROOT/scripts/run_reader_api.sh" >/tmp/sentence-reader-v20c-api.log 2>&1 &
  API_PID="$!"
  for _ in $(seq 1 30); do
    if api_health; then
      break
    fi
    sleep 0.2
  done
fi
api_health

echo "== V2.0C Hermes ingestion runtime =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_api_hermes_ingest_smoke.py"

echo "V2.0C Hermes ingestion acceptance PASS"
