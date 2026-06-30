from __future__ import annotations

import os


DEFAULT_DATABASE_URL = "postgresql://localhost/sentence_reader"


def database_url() -> str:
    return os.getenv("READER_DATABASE_URL") or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


def api_host() -> str:
    return os.getenv("READER_API_HOST", "127.0.0.1")


def api_port() -> int:
    return int(os.getenv("READER_API_PORT", "18180"))
