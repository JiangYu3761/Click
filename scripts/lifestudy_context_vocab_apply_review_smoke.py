#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifestudy_context_vocab_apply_review.py"
REVIEW_PACK = ROOT / "reports" / "lifestudy_vocab_review" / "Genesis-review-pack.json"
TEMPLATE = ROOT / "reports" / "lifestudy_vocab_review" / "Genesis-review-overrides.template.json"


def fail(message: str) -> int:
    print(f"lifestudy context vocab apply review smoke FAIL: {message}")
    return 1


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def build_override(path: Path, *, reject_count: int = 0) -> None:
    pack = json.loads(REVIEW_PACK.read_text(encoding="utf-8"))
    items = []
    for index, item in enumerate(pack.get("items") or []):
        term = item["term"]
        if index < reject_count:
            items.append(
                {
                    "term": term,
                    "current_meaning_zh": item.get("current_meaning_zh") or "",
                    "decision": "reject",
                    "corrected_meaning_zh": "",
                    "note": "smoke test rejected item; dry-run only",
                }
            )
        elif index == 1:
            items.append(
                {
                    "term": term,
                    "current_meaning_zh": item.get("current_meaning_zh") or "",
                    "decision": "correct",
                    "corrected_meaning_zh": str(item.get("current_meaning_zh") or "") + "（烟测修正）",
                    "note": "smoke test correction; dry-run only",
                }
            )
        else:
            items.append(
                {
                    "term": term,
                    "current_meaning_zh": item.get("current_meaning_zh") or "",
                    "decision": "approve",
                    "corrected_meaning_zh": "",
                    "note": "smoke test approval; dry-run only",
                }
            )
    path.write_text(
        json.dumps(
            {
                "schema": "sentence_reader.lifestudy_vocab_review_overrides.v1",
                "source_review_pack": str(REVIEW_PACK),
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if not SCRIPT.exists():
        return fail(f"missing script: {SCRIPT}")
    if not REVIEW_PACK.exists():
        return fail(f"missing review pack: {REVIEW_PACK}")
    if not TEMPLATE.exists():
        return fail(f"missing override template: {TEMPLATE}")
    source = SCRIPT.read_text(encoding="utf-8")
    markers = [
        "sentence_reader.lifestudy_vocab_review_apply.v1",
        "database_write_performed",
        "status = 'hidden'",
        "status = 'ignored'",
        "source = 'lifestudy_rejected'",
        "source = 'user'",
        "can_expand_next_volume",
    ]
    missing = [marker for marker in markers if marker not in source]
    if missing:
        return fail(f"missing static markers: {missing}")

    pending = run([sys.executable, str(SCRIPT), "--review-pack", str(REVIEW_PACK), "--overrides", str(TEMPLATE)], check=False)
    if pending.returncode == 0:
        return fail("pending template should not be applicable")
    if "must be approve/correct/reject" not in pending.stderr:
        return fail(f"pending failure did not explain decision gate: {pending.stderr.strip()}")

    with tempfile.TemporaryDirectory(prefix="lifestudy-review-smoke-") as tmp:
        approved_override = Path(tmp) / "all-reviewed.json"
        rejected_override = Path(tmp) / "one-rejected.json"
        build_override(approved_override, reject_count=0)
        build_override(rejected_override, reject_count=4)

        approved_proc = run(
            [
                sys.executable,
                str(SCRIPT),
                "--review-pack",
                str(REVIEW_PACK),
                "--overrides",
                str(approved_override),
            ]
        )
        approved = json.loads(approved_proc.stdout)
        if approved.get("database_write_performed") is not False:
            return fail("dry-run must not write database")
        if approved.get("term_count") != 25:
            return fail(f"expected 25 reviewed terms, got {approved.get('term_count')}")
        if approved.get("decision_counts", {}).get("correct") != 1:
            return fail(f"expected one synthetic correction, got {approved.get('decision_counts')}")
        if approved.get("human_reviewed_precision") != 1:
            return fail(f"all-approved precision should be 1, got {approved.get('human_reviewed_precision')}")
        if approved.get("can_expand_next_volume") is not True:
            return fail(f"all approved/corrected dry-run should pass expansion preflight: {approved.get('can_expand_note')}")

        rejected_proc = run(
            [
                sys.executable,
                str(SCRIPT),
                "--review-pack",
                str(REVIEW_PACK),
                "--overrides",
                str(rejected_override),
            ]
        )
        rejected = json.loads(rejected_proc.stdout)
        if rejected.get("database_write_performed") is not False:
            return fail("rejected dry-run must not write database")
        if rejected.get("decision_counts", {}).get("reject") != 4:
            return fail(f"expected four synthetic rejections, got {rejected.get('decision_counts')}")
        if rejected.get("human_reviewed_precision", 0) >= 0.85:
            return fail(f"four rejects should fall below precision gate, got {rejected.get('human_reviewed_precision')}")
        if rejected.get("can_expand_next_volume") is not False:
            return fail("below-target reviewed precision must block next-volume expansion")

    print("lifestudy context vocab apply review smoke PASS dry_run_terms=25 pending_gate=blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
