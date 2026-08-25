"""Turso 数据库访问。"""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator

from libsql_client import create_client_sync

from .config import get_settings
from .roles import normalize_role


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
        _ensure_schema(client)
        row = client.execute("SELECT value FROM meta WHERE key = 'schema_version'").rows
        return row[0][0] if row else "unknown"


def _ensure_schema(client) -> None:
    cols = {r[1]: r for r in client.execute("PRAGMA table_info(users)").rows}
    if "phone" not in cols:
        client.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "lab_rooms" not in cols:
        client.execute("ALTER TABLE users ADD COLUMN lab_rooms TEXT")


def _parse_lab_rooms(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except (TypeError, json.JSONDecodeError):
        pass
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def _row_to_user(row: Any) -> dict[str, Any]:
    # id, logto_sub, email, name, phone, role, college, created_at, updated_at, lab_rooms?
    keys = (
        "id",
        "logto_sub",
        "email",
        "name",
        "phone",
        "role",
        "college",
        "created_at",
        "updated_at",
    )
    data = {k: row[i] for i, k in enumerate(keys)}
    lab_raw = row[9] if len(row) > 9 else None
    data["role"] = normalize_role(data.get("role"))
    data["lab_rooms"] = _parse_lab_rooms(lab_raw)
    return data


def get_user_by_sub(sub: str) -> dict[str, Any] | None:
    with turso_client() as client:
        _ensure_schema(client)
        rows = client.execute(
            """
            SELECT id, logto_sub, email, name, phone, role, college,
                   created_at, updated_at, lab_rooms
            FROM users WHERE logto_sub = ?
            """,
            [sub],
        ).rows
        if not rows:
            return None
        return _row_to_user(rows[0])


def list_users(*, college: str | None = None) -> list[dict[str, Any]]:
    with turso_client() as client:
        _ensure_schema(client)
        if college:
            rows = client.execute(
                """
                SELECT id, logto_sub, email, name, phone, role, college,
                       created_at, updated_at, lab_rooms
                FROM users WHERE college = ?
                ORDER BY updated_at DESC
                """,
                [college],
            ).rows
        else:
            rows = client.execute(
                """
                SELECT id, logto_sub, email, name, phone, role, college,
                       created_at, updated_at, lab_rooms
                FROM users
                ORDER BY updated_at DESC
                """
            ).rows
        return [_row_to_user(r) for r in rows]


def upsert_user(
    sub: str,
    email: str | None,
    name: str | None,
    phone: str | None = None,
    *,
    default_role: str = "student",
    promote_to_jw_admin: bool = False,
) -> dict[str, Any]:
    role = "jw_admin" if promote_to_jw_admin else normalize_role(default_role)
    with turso_client() as client:
        _ensure_schema(client)
        existing = client.execute(
            "SELECT role FROM users WHERE logto_sub = ?",
            [sub],
        ).rows
        if existing:
            # 已存在：不覆盖 role/college；仅更新资料。若需引导升权且当前非 jw_admin
            if promote_to_jw_admin and normalize_role(existing[0][0]) != "jw_admin":
                client.execute(
                    """
                    UPDATE users SET
                      email = COALESCE(?, email),
                      name = COALESCE(?, name),
                      phone = COALESCE(?, phone),
                      role = 'jw_admin',
                      updated_at = datetime('now')
                    WHERE logto_sub = ?
                    """,
                    [email, name, phone, sub],
                )
            else:
                client.execute(
                    """
                    UPDATE users SET
                      email = COALESCE(?, email),
                      name = COALESCE(?, name),
                      phone = COALESCE(?, phone),
                      updated_at = datetime('now')
                    WHERE logto_sub = ?
                    """,
                    [email, name, phone, sub],
                )
        else:
            client.execute(
                """
                INSERT INTO users (id, logto_sub, email, name, phone, role)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [sub, sub, email, name, phone, role],
            )
    user = get_user_by_sub(sub)
    assert user is not None
    return user


def set_user_role(
    sub: str,
    role: str,
    college: str | None,
    lab_rooms: list[str] | None,
    *,
    actor_sub: str | None = None,
) -> dict[str, Any]:
    role = normalize_role(role)
    rooms_json = json.dumps(lab_rooms or [], ensure_ascii=False)
    college_val = (college or "").strip() or None
    with turso_client() as client:
        _ensure_schema(client)
        rows = client.execute("SELECT logto_sub FROM users WHERE logto_sub = ?", [sub]).rows
        if not rows:
            raise KeyError("用户不存在，须先登录一次平台")
        client.execute(
            """
            UPDATE users SET
              role = ?,
              college = ?,
              lab_rooms = ?,
              updated_at = datetime('now')
            WHERE logto_sub = ?
            """,
            [role, college_val, rooms_json, sub],
        )
        client.execute(
            """
            INSERT INTO audit_log (actor_sub, action, resource, payload_json)
            VALUES (?, 'set_user_role', ?, ?)
            """,
            [
                actor_sub,
                sub,
                json.dumps(
                    {"role": role, "college": college_val, "lab_rooms": lab_rooms or []},
                    ensure_ascii=False,
                ),
            ],
        )
    user = get_user_by_sub(sub)
    assert user is not None
    return user
