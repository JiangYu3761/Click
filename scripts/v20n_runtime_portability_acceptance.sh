#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V2.0N V2.0M gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20m_native_cognitive_dashboard_acceptance.sh"

echo "== V2.0N package with runtime manifest =="
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "== V2.0N runtime portability report =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_runtime_portability.py" \
  --require-current-machine-ready \
  --require-clean-mac-decision \
  --output "$ROOT/reports/sentence_reader_runtime_portability_report.json" \
  --markdown "$ROOT/reports/sentence_reader_runtime_portability_report.md"

echo "== V2.0N packaged runtime launch smoke =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_runtime_launch_smoke.py"

echo "== V2.0N product diagnostics with portability =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_diagnostics.py" \
  --require-package \
  --output "$ROOT/reports/sentence_reader_product_diagnostics_report.json"

echo "== V2.0N product static contract =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_static_smoke.py"

echo "V2.0N runtime portability acceptance PASS"
