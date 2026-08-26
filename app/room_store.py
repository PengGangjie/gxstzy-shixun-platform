# -*- coding: utf-8 -*-
"""分室可编辑数据：覆盖字段、教室照片、仪器台账（Turso）。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .db import turso_client

MAX_PHOTO_CHARS = 700_000  # 压缩后 data URL 上限约 700KB
MAX_PHOTOS_PER_ROOM = 12
MAX_EQUIP_ROWS = 500


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_room_tables(client) -> None:
    client.execute(
        """
        CREATE TABLE IF NOT EXISTS room_edits (
          room_id TEXT PRIMARY KEY,
          overrides_json TEXT NOT NULL DEFAULT '{}',
          updated_by TEXT,
          updated_at TEXT
        )
        """
    )
    client.execute(
        """
        CREATE TABLE IF NOT EXISTS room_photos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          room_id TEXT NOT NULL,
          data_url TEXT NOT NULL,
          caption TEXT,
          uploaded_by TEXT,
          created_at TEXT
        )
        """
    )
    client.execute(
        """
        CREATE TABLE IF NOT EXISTS room_equipment (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          room_id TEXT NOT NULL,
          code TEXT,
          name TEXT NOT NULL,
          model TEXT,
          status TEXT,
          risk_note TEXT,
          extra_json TEXT,
          updated_at TEXT
        )
        """
    )
    client.execute(
        "CREATE INDEX IF NOT EXISTS idx_room_photos_room ON room_photos(room_id)"
    )
    client.execute(
        "CREATE INDEX IF NOT EXISTS idx_room_equip_room ON room_equipment(room_id)"
    )


def get_room_state(room_id: str) -> dict[str, Any]:
    rid = (room_id or "").strip()
    with turso_client() as client:
        ensure_room_tables(client)
        edits = client.execute(
            "SELECT overrides_json, updated_by, updated_at FROM room_edits WHERE room_id = ?",
            [rid],
        ).rows
        overrides: dict[str, Any] = {}
        meta = {"updated_by": None, "updated_at": None}
        if edits:
            try:
                overrides = json.loads(edits[0][0] or "{}")
                if not isinstance(overrides, dict):
                    overrides = {}
            except json.JSONDecodeError:
                overrides = {}
            meta = {"updated_by": edits[0][1], "updated_at": edits[0][2]}

        photos = client.execute(
            """
            SELECT id, caption, uploaded_by, created_at, data_url
            FROM room_photos WHERE room_id = ?
            ORDER BY id DESC
            """,
            [rid],
        ).rows
        photo_list = [
            {
                "id": p[0],
                "caption": p[1] or "",
                "uploaded_by": p[2],
                "created_at": p[3],
                "data_url": p[4],
            }
            for p in photos
        ]

        equips = client.execute(
            """
            SELECT id, code, name, model, status, risk_note, extra_json, updated_at
            FROM room_equipment WHERE room_id = ?
            ORDER BY id ASC
            """,
            [rid],
        ).rows
        equip_list = []
        for e in equips:
            extra = {}
            if e[6]:
                try:
                    extra = json.loads(e[6])
                except json.JSONDecodeError:
                    extra = {}
            equip_list.append(
                {
                    "id": e[0],
                    "code": e[1] or "",
                    "name": e[2] or "",
                    "model": e[3] or "",
                    "status": e[4] or "",
                    "risk_note": e[5] or "",
                    "extra": extra if isinstance(extra, dict) else {},
                    "updated_at": e[7],
                }
            )

    return {
        "room_id": rid,
        "overrides": overrides,
        "photos": photo_list,
        "equipment": equip_list,
        "meta": meta,
    }


def save_overrides(room_id: str, overrides: dict[str, Any], by: str | None) -> dict[str, Any]:
    rid = (room_id or "").strip()
    clean = {str(k): v for k, v in (overrides or {}).items() if str(k).strip()}
    payload = json.dumps(clean, ensure_ascii=False)
    ts = _now()
    with turso_client() as client:
        ensure_room_tables(client)
        client.execute(
            """
            INSERT INTO room_edits (room_id, overrides_json, updated_by, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(room_id) DO UPDATE SET
              overrides_json = excluded.overrides_json,
              updated_by = excluded.updated_by,
              updated_at = excluded.updated_at
            """,
            [rid, payload, by, ts],
        )
    return {"room_id": rid, "overrides": clean, "updated_by": by, "updated_at": ts}


def add_photo(
    room_id: str,
    data_url: str,
    caption: str | None,
    by: str | None,
) -> dict[str, Any]:
    rid = (room_id or "").strip()
    url = (data_url or "").strip()
    if not url.startswith("data:image/"):
        raise ValueError("仅支持图片 data URL")
    if len(url) > MAX_PHOTO_CHARS:
        raise ValueError("图片过大，请压缩后再传（建议手机拍照后自动压缩）")
    with turso_client() as client:
        ensure_room_tables(client)
        n = client.execute(
            "SELECT COUNT(1) FROM room_photos WHERE room_id = ?", [rid]
        ).rows[0][0]
        if int(n) >= MAX_PHOTOS_PER_ROOM:
            raise ValueError(f"每间教室最多 {MAX_PHOTOS_PER_ROOM} 张照片")
        ts = _now()
        client.execute(
            """
            INSERT INTO room_photos (room_id, data_url, caption, uploaded_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [rid, url, (caption or "").strip()[:120], by, ts],
        )
        row = client.execute("SELECT last_insert_rowid()").rows[0][0]
    return {
        "id": row,
        "room_id": rid,
        "caption": (caption or "").strip()[:120],
        "uploaded_by": by,
        "created_at": ts,
        "data_url": url,
    }


def delete_photo(room_id: str, photo_id: int) -> bool:
    rid = (room_id or "").strip()
    with turso_client() as client:
        ensure_room_tables(client)
        client.execute(
            "DELETE FROM room_photos WHERE room_id = ? AND id = ?",
            [rid, int(photo_id)],
        )
    return True


def replace_equipment(
    room_id: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rid = (room_id or "").strip()
    if len(rows) > MAX_EQUIP_ROWS:
        raise ValueError(f"单次最多导入 {MAX_EQUIP_ROWS} 行")
    ts = _now()
    cleaned: list[tuple] = []
    for raw in rows:
        name = str(raw.get("name") or raw.get("名称") or "").strip()
        if not name:
            continue
        code = str(raw.get("code") or raw.get("仪器编号") or raw.get("编号") or "").strip()
        model = str(raw.get("model") or raw.get("型号") or raw.get("规格型号") or "").strip()
        status = str(raw.get("status") or raw.get("状态") or raw.get("设备状态") or "").strip()
        risk = str(
            raw.get("risk_note") or raw.get("风险提示") or raw.get("风险") or ""
        ).strip()
        cleaned.append((rid, code, name, model, status, risk, "{}", ts))

    with turso_client() as client:
        ensure_room_tables(client)
        client.execute("DELETE FROM room_equipment WHERE room_id = ?", [rid])
        for row in cleaned:
            client.execute(
                """
                INSERT INTO room_equipment
                  (room_id, code, name, model, status, risk_note, extra_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                list(row),
            )
    return get_room_state(rid)["equipment"]
