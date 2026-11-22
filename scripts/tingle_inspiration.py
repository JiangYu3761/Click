#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:18180"
TINGLE_CAPABILITY = "tingle.inspirations.v1"


def runtime_root() -> Path:
    root = Path(__file__).resolve().parents[1]
    installed = Path.home() / "Applications" / "Tingle.app" / "Contents" / "Resources" / "ReaderRuntime"
    return installed if installed.is_dir() else root


def ensure_runtime(base_url: str) -> None:
    if base_url.rstrip("/") != DEFAULT_BASE_URL:
        return
    manager = Path(__file__).resolve().with_name("click_runtime_manager.py")
    if not manager.is_file():
        raise RuntimeError("找不到 Click Runtime 管理器")
    result = subprocess.run(
        [
            sys.executable,
            str(manager),
            "ensure",
            "--runtime",
            str(runtime_root()),
            "--capability",
            TINGLE_CAPABILITY,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stdout.strip() or f"exit {result.returncode}"
        raise RuntimeError(f"Tingle Runtime 未就绪：{detail}")


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Tingle API {exc.code}：{detail}") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Tingle API 不可用：{exc}") from exc
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise RuntimeError(f"Tingle API 未确认成功：{result}")
    return result


def command_add(args: argparse.Namespace) -> dict[str, Any]:
    external_ref = args.external_ref.strip() if args.external_ref else f"hermes-cli:{uuid.uuid4().hex}"
    payload: dict[str, Any] = {
        "title": args.title.strip(),
        "content": args.content.strip(),
        "external_ref": external_ref,
    }
    if args.source_created_at:
        payload["source_created_at"] = args.source_created_at
    return request_json(args.base_url, "/tingle/inspirations", method="POST", payload=payload)


def command_list(args: argparse.Namespace) -> dict[str, Any]:
    query = urlencode({"archived": str(bool(args.archived)).lower(), "query": args.query, "limit": args.limit})
    return request_json(args.base_url, f"/tingle/inspirations?{query}")


def command_get(args: argparse.Namespace) -> dict[str, Any]:
    return request_json(args.base_url, f"/tingle/inspirations/{args.inspiration_id}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Read and write the shared Tingle inspiration library.")
    root.add_argument("--base-url", default=DEFAULT_BASE_URL)
    root.add_argument("--skip-ensure", action="store_true", help="Do not start the shared Click Runtime.")
    commands = root.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="Create one Hermes text inspiration.")
    add.add_argument("--title", required=True)
    add.add_argument("--content", required=True)
    add.add_argument("--external-ref")
    add.add_argument("--source-created-at")
    add.set_defaults(handler=command_add)

    listing = commands.add_parser("list", help="List Tingle inspirations.")
    listing.add_argument("--archived", action="store_true")
    listing.add_argument("--query", default="")
    listing.add_argument("--limit", type=int, default=100, choices=range(1, 501), metavar="1..500")
    listing.set_defaults(handler=command_list)

    detail = commands.add_parser("get", help="Read one Tingle inspiration.")
    detail.add_argument("inspiration_id")
    detail.set_defaults(handler=command_get)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if not args.skip_ensure:
            ensure_runtime(args.base_url)
        result = args.handler(args)
    except (RuntimeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
