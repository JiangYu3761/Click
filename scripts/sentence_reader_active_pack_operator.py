#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_COGNITIVE_OS_DIR = Path(
    str(Path.home() / "Library" / "Application Support" / "SentenceReader" / "CognitiveOS")
)
OPERATOR_RUN_DIR = Path("incoming") / "sentence_reader_drafts" / "operator_runs"
READER_ROOT = Path(__file__).resolve().parents[1]
QUEUE_SCRIPT = READER_ROOT / "scripts" / "sentence_reader_review_queue.py"
PROMOTE_SCRIPT = READER_ROOT / "scripts" / "sentence_reader_promote_intake_draft.py"


class OperatorError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise OperatorError(f"{path} must contain a JSON object")
    return data


def run_command(command: list[str], cwd: Path, timeout: int = 90) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "command": command,
        "cwd": str(cwd),
        "output": result.stdout,
    }


def ensure_scripts() -> None:
    missing = [str(path) for path in [QUEUE_SCRIPT, PROMOTE_SCRIPT] if not path.exists()]
    if missing:
        raise OperatorError(f"missing Sentence Reader operator dependency scripts: {missing}")


def build_queue(root: Path, run_dir: Path, allow_empty: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    queue_report = run_dir / "review_queue.json"
    queue_markdown = run_dir / "review_queue.md"
    command = [
        sys.executable,
        str(QUEUE_SCRIPT),
        "--cognitive-os-dir",
        str(root),
        "--report",
        str(queue_report),
        "--markdown",
        str(queue_markdown),
    ]
    if allow_empty:
        command.append("--allow-empty")
    command_result = run_command(command, READER_ROOT)
    if not command_result["ok"]:
        raise OperatorError(f"review queue failed: {command_result['output']}")
    return load_json(queue_report), command_result


def select_drafts(queue: dict[str, Any], args: argparse.Namespace) -> list[Path]:
    explicit = [Path(item).expanduser() for item in args.draft]
    if explicit:
        return explicit
    if args.all_ready:
        return [
            Path(item["draft_path"]).expanduser()
            for item in queue.get("items", [])
            if item.get("status") == "ready_to_approve"
        ]
    if args.draft_id:
        wanted = set(args.draft_id)
        return [
            Path(item["draft_path"]).expanduser()
            for item in queue.get("items", [])
            if item.get("draft_id") in wanted or item.get("candidate_intake_id") in wanted
        ]
    return []


def promotion_command(
    root: Path,
    drafts: list[Path],
    report_path: Path,
    *,
    approved: bool,
    dry_run: bool,
    allow_needs_review: bool,
    overwrite: bool,
) -> list[str]:
    command = [
        sys.executable,
        str(PROMOTE_SCRIPT),
        "--cognitive-os-dir",
        str(root),
        "--report",
        str(report_path),
    ]
    for draft in drafts:
        command.extend(["--draft", str(draft)])
    if approved:
        command.append("--approved")
    if dry_run:
        command.append("--dry-run")
    if allow_needs_review:
        command.append("--allow-needs-review")
    if overwrite:
        command.append("--overwrite")
    return command


def formal_targets_from_promotion(report: dict[str, Any]) -> list[Path]:
    targets: list[Path] = []
    for item in report.get("results", []):
        target = item.get("target_path")
        if target:
            targets.append(Path(str(target)).expanduser())
    return targets


def backup_file(path: Path, backup_root: Path, cognitive_root: Path) -> dict[str, Any]:
    relative = None
    try:
        relative = path.resolve().relative_to(cognitive_root.resolve())
    except ValueError:
        relative = Path("external") / path.name
    backup_path = backup_root / relative
    item = {
        "path": str(path),
        "backup_path": str(backup_path),
        "existed": path.exists(),
        "kind": "file",
    }
    if path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
    return item


def build_rollback_manifest(root: Path, run_dir: Path, targets: list[Path]) -> dict[str, Any]:
    backup_root = run_dir / "rollback"
    paths = [
        root / "compiled_packs" / "active_cognitive_pack.json",
        root / "compiled_packs" / "merged_active_pack_v1_5.json",
    ]
    paths.extend(targets)
    unique_paths = sorted(dict.fromkeys(path.resolve() for path in paths))
    items = [backup_file(path, backup_root, root) for path in unique_paths]
    manifest = {
        "schema": "sentence_reader.active_pack_operator_rollback.v1",
        "created_at": now_iso(),
        "cognitive_os_dir": str(root),
        "backup_root": str(backup_root),
        "items": items,
    }
    rollback_path = run_dir / "rollback_manifest.json"
    rollback_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["rollback_manifest_path"] = str(rollback_path)
    return manifest


def restore_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    restored: list[dict[str, Any]] = []
    for item in manifest.get("items", []):
        path = Path(item["path"])
        backup_path = Path(item["backup_path"])
        existed = bool(item.get("existed"))
        if existed and backup_path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, path)
            restored.append({"path": str(path), "action": "restored"})
        elif not existed and path.exists():
            path.unlink()
            restored.append({"path": str(path), "action": "removed_created_file"})
        else:
            restored.append({"path": str(path), "action": "unchanged"})
    return {"ok": True, "restored": restored}


def rebuild_active_pack(root: Path) -> dict[str, Any]:
    script = root / "scripts" / "build_active_cognitive_pack.py"
    if not script.exists():
        return {"ok": False, "skipped": True, "reason": f"missing {script}"}
    return run_command([sys.executable, str(script)], root, timeout=90)


def run_quality_gate(root: Path) -> dict[str, Any]:
    script = root / "v2_book_intake_quality_gate.py"
    if not script.exists():
        return {"ok": False, "skipped": True, "reason": f"missing {script}"}
    return run_command([sys.executable, str(script)], root, timeout=90)


def run_operator(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    ensure_scripts()
    root = Path(args.cognitive_os_dir).expanduser()
    current_run_dir = Path(args.run_dir).expanduser() if args.run_dir else root / OPERATOR_RUN_DIR / run_id()
    current_run_dir.mkdir(parents=True, exist_ok=True)

    if not args.dry_run and not args.approved:
        raise OperatorError("missing --approved for non-dry-run active-pack operator run")

    queue, queue_command = build_queue(root, current_run_dir, allow_empty=True)
    drafts = select_drafts(queue, args)
    if not drafts and not args.allow_empty:
        raise OperatorError("no drafts selected; pass --draft, --draft-id, --all-ready, or --allow-empty")

    preflight_report_path = current_run_dir / "preflight_promotion_report.json"
    if drafts:
        preflight_command = promotion_command(
            root,
            drafts,
            preflight_report_path,
            approved=True,
            dry_run=True,
            allow_needs_review=args.allow_needs_review,
            overwrite=args.overwrite,
        )
        preflight = run_command(preflight_command, READER_ROOT)
        preflight_report = load_json(preflight_report_path) if preflight_report_path.exists() else {}
    else:
        preflight = {"ok": True, "skipped": True, "reason": "no drafts selected"}
        preflight_report = {}
    if drafts and not preflight["ok"]:
        report = base_report(args, root, current_run_dir, queue, queue_command, drafts)
        report.update({"status": "preflight_failed", "preflight": preflight, "preflight_report": preflight_report})
        write_report(report, current_run_dir)
        return 1, report

    targets = formal_targets_from_promotion(preflight_report)
    rollback_manifest = build_rollback_manifest(root, current_run_dir, targets) if not args.dry_run else {"skipped": True, "reason": "dry_run"}

    promotion = {"ok": True, "skipped": True, "reason": "dry_run or no drafts"}
    promotion_report: dict[str, Any] = {}
    rebuild = {"ok": True, "skipped": True, "reason": "dry_run or no drafts"}
    quality_gate = {"ok": True, "skipped": True, "reason": "dry_run or skipped"}
    rollback_result = {"ok": True, "skipped": True, "reason": "not needed"}
    status = "dry_run" if args.dry_run else "success"

    if drafts and not args.dry_run:
        promotion_report_path = current_run_dir / "promotion_report.json"
        promotion = run_command(
            promotion_command(
                root,
                drafts,
                promotion_report_path,
                approved=True,
                dry_run=False,
                allow_needs_review=args.allow_needs_review,
                overwrite=args.overwrite,
            ),
            READER_ROOT,
        )
        promotion_report = load_json(promotion_report_path) if promotion_report_path.exists() else {}
        if promotion["ok"]:
            rebuild = rebuild_active_pack(root)
        if promotion["ok"] and rebuild.get("ok"):
            quality_gate = {"ok": True, "skipped": True, "reason": "skip_quality_gate requested"} if args.skip_quality_gate else run_quality_gate(root)

        if not promotion["ok"] or not rebuild.get("ok") or not quality_gate.get("ok"):
            status = "failed"
            if args.rollback_on_failure:
                rollback_result = restore_from_manifest(rollback_manifest)
                status = "rolled_back"
        else:
            status = "success"

    report = base_report(args, root, current_run_dir, queue, queue_command, drafts)
    report.update(
        {
            "status": status,
            "selected_count": len(drafts),
            "selected_drafts": [str(path) for path in drafts],
            "preflight": preflight,
            "preflight_report": preflight_report,
            "rollback_manifest": rollback_manifest,
            "promotion": promotion,
            "promotion_report": promotion_report,
            "active_pack_rebuild": rebuild,
            "quality_gate": quality_gate,
            "rollback_result": rollback_result,
        }
    )
    write_report(report, current_run_dir)
    if status in {"success", "dry_run"}:
        return 0, report
    return 3 if status == "rolled_back" else 2, report


def base_report(args: argparse.Namespace, root: Path, run_dir: Path, queue: dict[str, Any], queue_command: dict[str, Any], drafts: list[Path]) -> dict[str, Any]:
    return {
        "schema": "sentence_reader.active_pack_operator_report.v1",
        "generated_at": now_iso(),
        "cognitive_os_dir": str(root),
        "run_dir": str(run_dir),
        "dry_run": args.dry_run,
        "approved": args.approved,
        "allow_needs_review": args.allow_needs_review,
        "overwrite": args.overwrite,
        "rollback_on_failure": args.rollback_on_failure,
        "queue_counts": queue.get("counts", {}),
        "queue_report_path": queue.get("report_path"),
        "queue_markdown_path": queue.get("markdown_path"),
        "queue_command": queue_command,
        "selected_count": len(drafts),
        "selected_drafts": [str(path) for path in drafts],
    }


def write_report(report: dict[str, Any], run_dir: Path) -> Path:
    path = run_dir / "active_pack_operator_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["report_path"] = str(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an approved Sentence Reader draft -> active Cognitive OS pack operator transaction.")
    parser.add_argument("--cognitive-os-dir", default=str(DEFAULT_COGNITIVE_OS_DIR))
    parser.add_argument("--draft", action="append", default=[], help="Draft JSON path. Can be passed more than once.")
    parser.add_argument("--draft-id", action="append", default=[], help="Select drafts from the review queue by draft_id or candidate_intake_id.")
    parser.add_argument("--all-ready", action="store_true", help="Select all queue items with status ready_to_approve.")
    parser.add_argument("--approved", action="store_true", help="Required for non-dry-run execution.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-needs-review", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-quality-gate", action="store_true")
    parser.add_argument("--no-rollback-on-failure", dest="rollback_on_failure", action="store_false", default=True)
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--run-dir", default="")
    args = parser.parse_args()

    try:
        code, report = run_operator(args)
    except Exception as exc:  # noqa: BLE001 - command-line operator should emit structured-ish failure.
        report = {
            "schema": "sentence_reader.active_pack_operator_report.v1",
            "generated_at": now_iso(),
            "status": "error",
            "error": f"{exc.__class__.__name__}: {exc}",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
