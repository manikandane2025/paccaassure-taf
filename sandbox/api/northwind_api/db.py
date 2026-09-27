"""Tiny pg8000 helper: one connection per request, rows as dicts, named parameters."""

from collections.abc import Iterator
from typing import Annotated, Any

import pg8000.native
from fastapi import Depends

from northwind_api.settings import get_settings

type Row = dict[str, Any]

UNIQUE_VIOLATION = "23505"


def connect() -> pg8000.native.Connection:
    settings = get_settings()
    return pg8000.native.Connection(
        user=settings.db_user,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        timeout=10,
    )


def get_db() -> Iterator[pg8000.native.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


Db = Annotated[pg8000.native.Connection, Depends(get_db)]


def rows(conn: pg8000.native.Connection, sql: str, **params: object) -> list[Row]:
    result = conn.run(sql, **params) or []
    names = [column["name"] for column in conn.columns or []]
    return [dict(zip(names, values, strict=True)) for values in result]


def one(conn: pg8000.native.Connection, sql: str, **params: object) -> Row | None:
    found = rows(conn, sql, **params)
    return found[0] if found else None


def sql_state(error: Exception) -> str | None:
    details = error.args[0] if error.args else None
    return details.get("C") if isinstance(details, dict) else None
