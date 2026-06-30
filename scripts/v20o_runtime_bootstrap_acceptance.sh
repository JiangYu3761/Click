#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V2.0O V2.0N gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20n_runtime_portability_acceptance.sh"

echo "== V2.0O package with runtime bootstrap =="
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "== V2.0O runtime bootstrap smoke =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_runtime_bootstrap_smoke.py"

echo "== V2.0O runtime bootstrap report =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_runtime_bootstrap.py" \
  --require-startup-ready \
  --require-postgres-decision \
  --output "$ROOT/reports/sentence_reader_runtime_bootstrap_report.json" \
  --markdown "$ROOT/reports/sentence_reader_runtime_bootstrap_report.md"

echo "== V2.0O packaged runtime launch smoke =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_runtime_launch_smoke.py"

echo "== V2.0O product diagnostics with bootstrap =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_diagnostics.py" \
  --require-package \
  --output "$ROOT/reports/sentence_reader_product_diagnostics_report.json"

echo "== V2.0O product static contract =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_static_smoke.py"

echo "V2.0O runtime bootstrap acceptance PASS"
