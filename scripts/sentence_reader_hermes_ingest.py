#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:18180"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest pending Sentence Reader sync events into Hermes Cognitive OS incoming assets.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--cognitive-os-dir", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--sync-event-id", action="append", default=[], help="Restrict ingestion to one sync event id. Can be passed more than once.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    body: dict[str, object] = {"limit": args.limit, "dry_run": args.dry_run}
    if args.cognitive_os_dir:
        body["cognitive_os_dir"] = args.cognitive_os_dir
    if args.sync_event_id:
        body["sync_event_ids"] = args.sync_event_id

    with httpx.Client(base_url=args.base_url, timeout=10.0) as client:
        response = client.post("/sync/hermes/ingest", json=body)
    if response.status_code < 200 or response.status_code >= 300:
        print(f"hermes ingest FAIL status={response.status_code} body={response.text}")
        return 1

    payload = response.json()
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
