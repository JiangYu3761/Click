#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_DATABASE_URL = "postgresql://localhost/sentence_reader"
REQUIRED_TABLES = [
    "reader.books",
    "reader.book_files",
    "reader.chapters",
    "reader.sentences",
    "reader.annotations",
    "reader.reading_positions",
    "reader.audio_notes",
    "reader.exports",
    "reader.sync_events",
]
COMMON_POSTGRES_PATHS = [
    "/Applications/Postgres.app",
    "/Applications/Postgres.app/Contents/Versions/latest/bin/psql",
    "/opt/homebrew/bin/psql",
    "/usr/local/bin/psql",
]


def parse_host_port(database_url: str) -> tuple[str, int]:
    parsed = urlparse(database_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    return host, port


def check_tcp(host: str, port: int, timeout: float = 1.0) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "host": host, "port": port}
    except OSError as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc)}


def check_binaries() -> dict[str, Any]:
    found = {
        name: shutil.which(name)
        for name in ("psql", "postgres", "pg_ctl", "initdb", "brew", "docker")
    }
    common_paths = [path for path in COMMON_POSTGRES_PATHS if Path(path).exists()]
    return {"found": found, "common_paths": common_paths}


def check_python_deps() -> dict[str, Any]:
    try:
        import psycopg  # noqa: F401
    except Exception as exc:
        return {"psycopg": False, "error": f"{exc.__class__.__name__}: {exc}"}
    return {"psycopg": True}


def check_database(database_url: str) -> dict[str, Any]:
    deps = check_python_deps()
    if not deps["psycopg"]:
        return {"ok": False, "deps": deps}

    import psycopg
    from psycopg.rows import dict_row

    try:
        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            db_row = conn.execute(
                "SELECT current_database() AS database, current_schema() AS schema"
            ).fetchone()
            table_rows = conn.execute(
                """
                SELECT table_schema || '.' || table_name AS name
                FROM information_schema.tables
                WHERE table_schema = 'reader'
                ORDER BY name
                """
            ).fetchall()
    except psycopg.OperationalError as exc:
        return {"ok": False, "deps": deps, "error": str(exc)}

    existing = [row["name"] for row in table_rows]
    missing = [table for table in REQUIRED_TABLES if table not in existing]
    return {
        "ok": not missing,
        "deps": deps,
        "database": db_row["database"],
        "schema": db_row["schema"],
        "existing_tables": existing,
        "missing_tables": missing,
    }


def render_human(report: dict[str, Any]) -> None:
    print(f"reader pg status database_url={report['database_url']}")
    print(f"tcp ok={report['tcp']['ok']} host={report['tcp']['host']} port={report['tcp']['port']}")
    if not report["tcp"]["ok"]:
        print(f"tcp error={report['tcp']['error']}")
    print(f"binaries={report['binaries']['found']}")
    if report["binaries"]["common_paths"]:
        print(f"common_postgres_paths={report['binaries']['common_paths']}")
    print(f"database ok={report['database']['ok']}")
    if report["database"].get("missing_tables"):
        print(f"missing_tables={report['database']['missing_tables']}")
    if report["database"].get("error"):
        print(f"database error={report['database']['error']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Sentence Reader PostgreSQL readiness.")
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--json", action="store_true", help="Print a JSON report.")
    parser.add_argument(
        "--server-only",
        action="store_true",
        help="Only require PostgreSQL TCP readiness and local Python driver availability.",
    )
    args = parser.parse_args()

    host, port = parse_host_port(args.database_url)
    report = {
        "ok": False,
        "database_url": args.database_url,
        "binaries": check_binaries(),
        "tcp": check_tcp(host, port),
        "database": check_database(args.database_url),
    }
    if args.server_only:
        report["ok"] = bool(report["tcp"]["ok"] and report["database"]["deps"].get("psycopg"))
        report["server_only"] = True
    else:
        report["ok"] = bool(report["tcp"]["ok"] and report["database"]["ok"])

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        render_human(report)

    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
