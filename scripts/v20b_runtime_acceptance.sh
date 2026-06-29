#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V2.0B V2.0A gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20_product_packaging_acceptance.sh"

echo "== V2.0B packaged ReaderRuntime launch smoke =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/reader_runtime_launch_smoke.py"

echo "V2.0B bundled runtime acceptance PASS"
