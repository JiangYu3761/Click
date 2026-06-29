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

echo "== V2.0A V1.9 gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v19_hermes_sync_acceptance.sh"

echo "== V2.0A product static contract =="
python3 "$ROOT/scripts/check_native_reader.py"
python3 "$ROOT/scripts/sentence_reader_product_static_smoke.py"
"$PYTHON" -m compileall "$ROOT/reader_api" "$ROOT/scripts" "$ROOT/tests"

echo "== V2.0A package app with ReaderRuntime =="
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "== V2.0A ensure Reader API runtime =="
if ! api_health; then
  PATH="$PG_BIN:$PATH" "$ROOT/scripts/run_reader_api.sh" >/tmp/sentence-reader-v20-api.log 2>&1 &
  API_PID="$!"
  for _ in $(seq 1 30); do
    if api_health; then
      break
    fi
    sleep 0.2
  done
fi
api_health

echo "== V2.0A product diagnostics =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_diagnostics.py" \
  --require-api \
  --require-postgres \
  --require-package \
  --output "$ROOT/reports/sentence_reader_product_diagnostics_report.json"

echo "== V2.0A backup and restore verification =="
BACKUP_ROOT="$(mktemp -d /tmp/sentence-reader-v20-backup.XXXXXX)"
BACKUP_REPORT="$ROOT/reports/sentence_reader_backup_smoke_report.json"
RESTORE_REPORT="$ROOT/reports/sentence_reader_restore_verify_report.json"
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_backup.py" \
  --output-dir "$BACKUP_ROOT" \
  --name smoke \
  --skip-files \
  --report "$BACKUP_REPORT"
"$PYTHON" "$ROOT/scripts/sentence_reader_restore_verify.py" "$BACKUP_REPORT" --report "$RESTORE_REPORT"

echo "V2.0A product packaging acceptance PASS"
