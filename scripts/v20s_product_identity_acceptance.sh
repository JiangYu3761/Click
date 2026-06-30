#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"
PG_BIN="${POSTGRES_APP_BIN:-/Applications/Postgres.app/Contents/Versions/latest/bin}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V2.0S V2.0R gate =="
PATH="$PG_BIN:$PATH" "$ROOT/scripts/v20r_first_run_guide_acceptance.sh"

echo "== V2.0S generate reading app icon =="
python3 "$ROOT/scripts/generate_sentence_reader_icon.py" --quiet

echo "== V2.0S package app with icon =="
python3 "$ROOT/scripts/package_sentence_reader_app.py"

echo "== V2.0S dock dry-run =="
"$PYTHON" "$ROOT/scripts/pin_sentence_reader_to_dock.py" --dry-run

echo "== V2.0S identity static smoke =="
"$PYTHON" "$ROOT/scripts/sentence_reader_identity_static_smoke.py"

echo "== V2.0S product static contract =="
PATH="$PG_BIN:$PATH" "$PYTHON" "$ROOT/scripts/sentence_reader_product_static_smoke.py"

echo "V2.0S product identity acceptance PASS"
