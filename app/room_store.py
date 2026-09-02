# -*- coding: utf-8 -*-
"""分室可编辑数据：覆盖字段、教室照片、仪器台账（Turso）。"""
from __future__ import annotations

import base64
import io
import json
from datetime import datetime, timezone
from typing import Any

from .db import turso_client

MAX_PHOTO_CHARS = 160_000  # 压缩后 data URL 上限约 120KB JPEG
MAX_PHOTOS_PER_ROOM = 12
MAX_EQUIP_ROWS = 500
PHOTO_MAX_SIDE = 960
PHOTO_TARGET_BYTES = 90_000


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def optimize_photo_data_url(url: str) -> str:
    """纠正方向、缩边、JPEG 复压，避免教室照片撑满 Turso。"""
    raw_url = (url or "").strip()
    if not raw_url.startswith("data:image/"):
        raise ValueError("仅支持图片 data URL")
    _, _, b64 = raw_url.partition(",")
    if not b64:
        raise ValueError("图片数据不完整")
    try:
        blob = base64.b64decode(b64, validate=False)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("图片无法解码") from exc
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        if len(raw_url) > MAX_PHOTO_CHARS:
            raise ValueError("图片过大，请压缩后再传") from exc
        return raw_url
    try:
        img = Image.open(io.BytesIO(blob))
        img = ImageOps.exif_transpose(img)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("不是有效图片") from exc
    if img.mode in {"RGBA", "LA", "P"}:
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    def encode(im: Image.Image, quality: int) -> bytes:
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
        return buf.getvalue()

    w, h = img.size
    side = max(w, h)
    if side > PHOTO_MAX_SIDE:
        scale = PHOTO_MAX_SIDE / side
        img = img.resize(
            (max(1, round(w * scale)), max(1, round(h * scale))),
            Image.Resampling.LANCZOS,
        )

    quality = 72
    jpeg = encode(img, quality)
    while len(jpeg) > PHOTO_TARGET_BYTES and (quality > 42 or max(img.size) > 480):
        if quality > 42:
            quality -= 8
        else:
            nw, nh = img.size
            img = img.resize(
                (max(1, round(nw * 0.82)), max(1, round(nh * 0.82))),
                Image.Resampling.LANCZOS,
            )
        jpeg = encode(img, quality)

    out = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
    if len(out) > MAX_PHOTO_CHARS:
        raise ValueError("图片过大，请换一张稍远一点拍的照片")
    return out


def recompress_existing_photos() -> dict[str, int]:
    with turso_client() as client:
        ensure_room_tables(client)
        rows = client.execute("SELECT id, data_url FROM room_photos").rows
        updated = 0
        saved = 0
        for pid, url in rows:
            new = optimize_photo_data_url(url or "")
            if len(new) < len(url or ""):
                saved += len(url or "") - len(new)
                client.execute(
                    "UPDATE room_photos SET data_url = ? WHERE id = ?",
                    [new, int(pid)],
                )
                updated += 1
        return {"total": len(rows), "updated": updated, "saved_chars": saved}


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
    url = optimize_photo_data_url(data_url)
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
