"""Turso 数据库访问。"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from libsql_client import create_client_sync

from .config import get_settings


@contextmanager
def turso_client() -> Iterator:
    settings = get_settings()
    if not settings.turso_database_url or not settings.turso_auth_token:
        raise RuntimeError("Turso 未配置")
    client = create_client_sync(settings.turso_database_url, auth_token=settings.turso_auth_token)
    try:
        yield client
    finally:
        client.close()


def ping_db() -> str:
    with turso_client() as client:
        _ensure_phone_column(client)
        row = client.execute("SELECT value FROM meta WHERE key = 'schema_version'").rows
        return row[0][0] if row else "unknown"


def _ensure_phone_column(client) -> None:
    cols = [r[1] for r in client.execute("PRAGMA table_info(users)").rows]
    if "phone" not in cols:
        client.execute("ALTER TABLE users ADD COLUMN phone TEXT")


def upsert_user(sub: str, email: str | None, name: str | None, phone: str | None = None) -> None:
    with turso_client() as client:
        _ensure_phone_column(client)
        client.execute(
            """
            INSERT INTO users (id, logto_sub, email, name, phone, role)
            VALUES (?, ?, ?, ?, ?, 'staff')
            ON CONFLICT(logto_sub) DO UPDATE SET
              email = COALESCE(excluded.email, users.email),
              name = COALESCE(excluded.name, users.name),
              phone = COALESCE(excluded.phone, users.phone),
              updated_at = datetime('now')
            """,
            [sub, sub, email, name, phone],
        )
