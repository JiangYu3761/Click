#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "sentence_reader.backup_manifest.v1":
        raise ValueError(f"unsupported backup manifest schema: {payload.get('schema')}")
    return payload


def verify_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    backup_dir = Path(manifest["backup_dir"])
    database_path = Path(manifest["database"]["output_path"])
    failures: list[str] = []

    if not backup_dir.exists():
        failures.append("backup_dir_missing")
    if not database_path.exists() or database_path.stat().st_size <= 0:
        failures.append("database_dump_missing")
    if not manifest.get("restore_policy", {}).get("destructive_restore_requires_explicit_user_approval"):
        failures.append("restore_policy_missing")
    if "file_inventory" not in manifest:
        failures.append("file_inventory_missing")

    copied = manifest.get("copied_files") or {}
    for name, item in copied.items():
        if item.get("copied") and not Path(item["target"]).exists():
            failures.append(f"copied_dir_missing:{name}")

    return {
        "ok": not failures,
        "schema": "sentence_reader.restore_verify.v1",
        "backup_dir": str(backup_dir),
        "database_dump": str(database_path),
        "failures": failures,
        "mode": "verify_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Sentence Reader backup without restoring it.")
    parser.add_argument("manifest", help="Path to manifest.json or a backup report JSON.")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser()
    result = verify_manifest(load_manifest(manifest_path))

    if args.report:
        report = Path(args.report).expanduser()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    print(f"restore_verify ok={result['ok']} failures={result['failures']}")
    print(f"backup_dir={result['backup_dir']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
