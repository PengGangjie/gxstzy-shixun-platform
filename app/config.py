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
    admin_emails: frozenset[str]
    # 学校统一身份认证（CAS）。cas_server 留空 = 未启用，行为与现在完全一致
    cas_server: str
    cas_service_url: str
    cas_tls_verify: str
    cas_tls_ca_b64: str
    admin_cas_accounts: frozenset[str]
    static_dir: Path
    port: int


def _parse_admin_emails(raw: str) -> frozenset[str]:
    return frozenset(e.strip().lower() for e in raw.split(",") if e.strip())


# 已知默认值：被猜到即可伪造会话 Cookie，生产（AUTH_REQUIRED=true）绝不允许使用
_INSECURE_SESSION_SECRETS = frozenset({"", "dev-change-me-in-production", "changeme", "secret"})


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
    auth_required = os.getenv("AUTH_REQUIRED", "true").lower() in {"1", "true", "yes"}
    session_secret = os.getenv("SESSION_SECRET", "").strip()
    if auth_required and session_secret.lower() in _INSECURE_SESSION_SECRETS:
        # fail closed：宁可拒绝启动，也不带着可预测的会话签名密钥上线
        raise RuntimeError(
            "SESSION_SECRET 未配置或使用了不安全的默认值——拒绝启动。"
            "请在环境变量（本地为 secrets/shixun-platform/.env）设置至少 32 位随机值，"
            "例如 python -c \"import secrets; print(secrets.token_urlsafe(48))\"。"
            "仅本地无登录调试可设 AUTH_REQUIRED=false。"
        )
    return Settings(
        app_name="gxstzy-shixun-platform",
        session_secret=session_secret,
        auth_required=auth_required,
        logto_endpoint=os.getenv("LOGTO_ENDPOINT", "").strip(),
        logto_app_id=os.getenv("LOGTO_APP_ID", "").strip(),
        logto_app_secret=os.getenv("LOGTO_APP_SECRET", "").strip(),
        logto_redirect_uri=redirect,
        logto_post_logout_uri=post_logout,
        turso_database_url=turso_url,
        turso_auth_token=os.getenv("TURSO_AUTH_TOKEN", "").strip(),
        admin_emails=_parse_admin_emails(os.getenv("ADMIN_EMAILS", "")),
        cas_server=os.getenv("CAS_SERVER", "").strip(),
        cas_service_url=os.getenv("CAS_SERVICE_URL", "").strip(),
        cas_tls_verify=os.getenv("CAS_TLS_VERIFY", "true").strip(),
        cas_tls_ca_b64=os.getenv("CAS_TLS_CA_B64", "").strip(),
        admin_cas_accounts=_parse_admin_emails(os.getenv("ADMIN_CAS_ACCOUNTS", "")),
        static_dir=static,
        port=int(os.getenv("PORT", "8000")),
    )
