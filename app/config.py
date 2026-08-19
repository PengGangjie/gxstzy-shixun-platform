"""应用配置（从环境变量读取，密钥勿入库）。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
# 本地开发：优先加载 workspace 内 secrets（Docker / Space 用注入的环境变量）
for candidate in (
    ROOT / "secrets" / "shixun-platform" / ".env",
    Path(r"c:\00CS\text\secrets\shixun-platform\.env"),
):
    if candidate.is_file():
        load_dotenv(candidate, override=False)
        break
load_dotenv(ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    app_name: str
    session_secret: str
    auth_required: bool
    logto_endpoint: str
    logto_app_id: str
    logto_app_secret: str
    logto_redirect_uri: str
    logto_post_logout_uri: str
    turso_database_url: str
    turso_auth_token: str
    static_dir: Path
    port: int


@lru_cache
def get_settings() -> Settings:
    static = ROOT / "static"
    redirect = os.getenv("LOGTO_REDIRECT_URI", "").strip()
    post_logout = os.getenv("LOGTO_POST_LOGOUT_URI", "").strip()
    if not redirect:
        base = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        redirect = f"{base}/callback"
    if not post_logout:
        base = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        post_logout = f"{base}/"
    turso_url = os.getenv("TURSO_DATABASE_URL", "").strip()
    if turso_url.startswith("libsql://"):
        turso_url = turso_url.replace("libsql://", "https://", 1)
    return Settings(
        app_name="gxstzy-shixun-platform",
        session_secret=os.getenv("SESSION_SECRET", "dev-change-me-in-production"),
        auth_required=os.getenv("AUTH_REQUIRED", "true").lower() in {"1", "true", "yes"},
        logto_endpoint=os.getenv("LOGTO_ENDPOINT", "").strip(),
        logto_app_id=os.getenv("LOGTO_APP_ID", "").strip(),
        logto_app_secret=os.getenv("LOGTO_APP_SECRET", "").strip(),
        logto_redirect_uri=redirect,
        logto_post_logout_uri=post_logout,
        turso_database_url=turso_url,
        turso_auth_token=os.getenv("TURSO_AUTH_TOKEN", "").strip(),
        static_dir=static,
        port=int(os.getenv("PORT", "8000")),
    )
