# -*- coding: utf-8 -*-
"""本地 SQLite 模式建表（与 secrets/shixun-platform/turso.schema.sql 同构）。"""
from __future__ import annotations


def ensure_sqlite_schema(client) -> None:
    """幂等建表；种子数据参数化写入。语句为静态 DDL 字面量。"""
    client.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY,
          logto_sub TEXT UNIQUE NOT NULL,
          email TEXT UNIQUE,
          name TEXT,
          phone TEXT,
          role TEXT NOT NULL DEFAULT 'student',
          college TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    client.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          actor_sub TEXT,
          action TEXT NOT NULL,
          resource TEXT,
          payload_json TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    client.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        )
        """
    )
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
    client.execute("CREATE INDEX IF NOT EXISTS idx_room_photos_room ON room_photos(room_id)")
    client.execute("CREATE INDEX IF NOT EXISTS idx_room_equip_room ON room_equipment(room_id)")
    client.execute(
        "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)", ["schema_version", "1"]
    )
    client.execute(
        "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)", ["app", "gxstzy-shixun-platform"]
    )
