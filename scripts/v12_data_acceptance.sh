#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${READER_API_PYTHON:-$ROOT/.venv-reader-api/bin/python}"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

echo "== V1.2 static/API contract =="
python3 "$ROOT/scripts/reader_api_static_smoke.py"
"$PYTHON" -m compileall "$ROOT/reader_api" "$ROOT/scripts" "$ROOT/tests"
"$PYTHON" -m pytest "$ROOT/tests/test_reader_api_mock.py" -q

echo "== V1.2 PostgreSQL server readiness =="
"$PYTHON" "$ROOT/scripts/reader_pg_status.py" --server-only

echo "== V1.2 migration =="
"$PYTHON" "$ROOT/scripts/reader_pg_migrate.py" --create-database

echo "== V1.2 PostgreSQL schema readiness =="
"$PYTHON" "$ROOT/scripts/reader_pg_status.py"

echo "== V1.2 direct PostgreSQL CRUD smoke =="
"$PYTHON" "$ROOT/scripts/reader_pg_smoke.py"

echo "== V1.2 live API + PostgreSQL smoke =="
"$PYTHON" "$ROOT/scripts/reader_api_live_smoke.py"

echo "V1.2 data acceptance PASS"
