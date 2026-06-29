#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_SUPPORT = Path.home() / "Library" / "Application Support" / "SentenceReader"
DEFAULT_BACKUP_ROOT = APP_SUPPORT / "Backups"
DEFAULT_DATABASE_URL = os.getenv("READER_DATABASE_URL") or os.getenv("DATABASE_URL") or "postgresql://localhost/jiangyu_os"
PG_BIN = Path(os.getenv("POSTGRES_APP_BIN", "/Applications/Postgres.app/Contents/Versions/latest/bin"))
FILE_DIRS = ["Books", "AudioNotes", "Exports", "HermesSync"]


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def inventory(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "files": 0, "bytes": 0}
    files = [item for item in path.rglob("*") if item.is_file()]
    return {
        "path": str(path),
        "exists": True,
        "files": len(files),
        "bytes": sum(item.stat().st_size for item in files),
    }


def copy_tree_if_exists(source: Path, target: Path) -> dict[str, Any]:
    if not source.exists():
        return {"source": str(source), "target": str(target), "copied": False, "reason": "missing"}
    shutil.copytree(source, target, dirs_exist_ok=True)
    copied = inventory(target)
    copied.update({"source": str(source), "target": str(target), "copied": True})
    return copied


def run_pg_dump(database_url: str, output: Path) -> dict[str, Any]:
    pg_dump = shutil.which("pg_dump")
    if not pg_dump and (PG_BIN / "pg_dump").exists():
        pg_dump = str(PG_BIN / "pg_dump")
    if not pg_dump:
        return {"ok": False, "error": "pg_dump not found"}

    env = os.environ.copy()
    if PG_BIN.exists():
        env["PATH"] = f"{PG_BIN}:{env.get('PATH', '')}"
    result = subprocess.run(
        [pg_dump, "--format=custom", "--schema=reader", "--file", str(output), database_url],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        timeout=60,
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "output_path": str(output),
        "bytes": output.stat().st_size if output.exists() else 0,
        "log": result.stdout.strip(),
    }


def build_manifest(backup_dir: Path, database_url: str, skip_files: bool) -> dict[str, Any]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    db_dump = backup_dir / "reader_schema.dump"
    database = run_pg_dump(database_url, db_dump)

    file_inventory = {name: inventory(APP_SUPPORT / name) for name in FILE_DIRS}
    copied_files: dict[str, Any] = {}
    if not skip_files:
        files_root = backup_dir / "files"
        for name in FILE_DIRS:
            copied_files[name] = copy_tree_if_exists(APP_SUPPORT / name, files_root / name)

    manifest = {
        "schema": "sentence_reader.backup_manifest.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "backup_dir": str(backup_dir),
        "database_url": database_url,
        "database": database,
        "app_support": str(APP_SUPPORT),
        "file_inventory": file_inventory,
        "copied_files": copied_files,
        "skip_files": skip_files,
        "restore_policy": {
            "safe_default": "verify_only",
            "destructive_restore_requires_explicit_user_approval": True,
        },
    }
    manifest["ok"] = bool(database["ok"])
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a non-destructive Sentence Reader backup artifact.")
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--output-dir", default=str(DEFAULT_BACKUP_ROOT))
    parser.add_argument("--name", default="")
    parser.add_argument("--skip-files", action="store_true", help="Only dump PostgreSQL and record file inventory.")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    backup_root = Path(args.output_dir).expanduser()
    backup_name = args.name or f"sentence-reader-backup-{now_stamp()}"
    backup_dir = backup_root / backup_name
    manifest = build_manifest(backup_dir, args.database_url, args.skip_files)

    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    if args.report:
        report = Path(args.report).expanduser()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    print(f"backup_dir={backup_dir}")
    print(f"manifest={manifest_path}")
    print(f"ok={manifest['ok']} database_dump={manifest['database'].get('output_path')}")
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
