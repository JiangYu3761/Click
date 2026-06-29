from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Optional, Union

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from reader_api.config import database_url


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        yield conn


def health() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT current_database() AS database, current_schema() AS schema").fetchone()
    return {"ok": True, "database": row["database"], "schema": row["schema"]}


def jsonb(value: Optional[Union[dict[str, Any], list[Any]]]) -> Jsonb:
    return Jsonb(value or {})
