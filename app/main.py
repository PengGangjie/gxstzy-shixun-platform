# -*- coding: utf-8 -*-
"""实训科管理平台 · FastAPI（Logto + Turso + 静态站点）。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Union

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from logto import LogtoClient, LogtoConfig, Storage, UserInfoScope
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .db import ping_db, upsert_user

PUBLIC_PREFIXES = (
    "/health",
    "/sign-in",
    "/callback",
    "/sign-out",
    "/assets/",
    "/lab-grade-boards/",
)

settings = get_settings()
app = FastAPI(title="广西生态工程职业技术学院 · 实训科管理平台")


class SessionStorage(Storage):
    def __init__(self, session: dict) -> None:
        self._session = session

    def get(self, key: str) -> Union[str, None]:
        val = self._session.get(key)
        return None if val is None else str(val)

    def set(self, key: str, value: Union[str, None]) -> None:
        if value is None:
            self._session.pop(key, None)
        else:
            self._session[key] = value

    def delete(self, key: str) -> None:
        self._session.pop(key, None)


def logto_client(request: Request) -> LogtoClient:
    return LogtoClient(
        LogtoConfig(
            endpoint=settings.logto_endpoint,
            appId=settings.logto_app_id,
            appSecret=settings.logto_app_secret,
            scopes=[UserInfoScope.email, UserInfoScope.phone],
        ),
        storage=SessionStorage(request.session),
    )


def auth_configured() -> bool:
    return bool(settings.logto_endpoint and settings.logto_app_id and settings.logto_app_secret)


@app.middleware("http")
async def require_auth(request: Request, call_next):
    if not settings.auth_required or not auth_configured():
        return await call_next(request)
    path = request.url.path
    if path.startswith(PUBLIC_PREFIXES):
        return await call_next(request)
    if path.endswith((".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".json")):
        return await call_next(request)
    client = logto_client(request)
    if client.isAuthenticated():
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "未登录"}, status_code=401)
    return RedirectResponse("/sign-in")


# SessionMiddleware 须后注册（更靠外层），保证 require_auth 内可读写 request.session
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="shixun_session",
    https_only=settings.logto_redirect_uri.startswith("https://"),
    same_site="lax",
    max_age=14 * 24 * 3600,
)


@app.get("/health")
async def health():
    body = {"status": "ok", "app": settings.app_name}
    try:
        body["db_schema_version"] = ping_db()
    except Exception as exc:  # noqa: BLE001
        body["db_error"] = str(exc)
    return body


@app.get("/sign-in")
async def sign_in(request: Request):
    if not auth_configured():
        return RedirectResponse("/")
    client = logto_client(request)
    url = await client.signIn(redirectUri=settings.logto_redirect_uri)
    return RedirectResponse(url)


@app.get("/callback")
async def callback(request: Request):
    """OIDC 回调。无 code/state 或会话丢失时返回说明页，避免裸 500。"""
    if not request.query_params.get("code"):
        return RedirectResponse("/sign-in")
    client = logto_client(request)
    try:
        await client.handleSignInCallback(str(request.url))
    except Exception as exc:  # noqa: BLE001
        detail = str(exc)
        return JSONResponse(
            {
                "detail": "登录回调失败",
                "reason": detail,
                "hint": "请从平台首页重新登录。若出现 invalid_client，请在 Logto 控制台核对 App ID/Secret 后重新部署。",
                "sign_in": "/sign-in",
            },
            status_code=400,
        )
    claims = client.getIdTokenClaims()
    if claims and claims.sub:
        upsert_user(
            claims.sub,
            getattr(claims, "email", None),
            getattr(claims, "name", None),
            getattr(claims, "phone_number", None),
        )
    return RedirectResponse("/")


@app.get("/sign-out")
async def sign_out(request: Request):
    client = logto_client(request)
    url = await client.signOut(postLogoutRedirectUri=settings.logto_post_logout_uri)
    return RedirectResponse(url)


@app.get("/api/me")
async def me(request: Request):
    client = logto_client(request)
    if not client.isAuthenticated():
        return JSONResponse({"authenticated": False}, status_code=401)
    claims = client.getIdTokenClaims()
    return {
        "authenticated": True,
        "sub": claims.sub if claims else None,
        "email": getattr(claims, "email", None) if claims else None,
        "phone": getattr(claims, "phone_number", None) if claims else None,
        "name": getattr(claims, "name", None) if claims else None,
    }


static_dir = settings.static_dir
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
else:

    @app.get("/")
    async def missing_static():
        return JSONResponse(
            {"detail": f"static 目录不存在: {static_dir}，请先运行 sync_shixun_platform_static.py"},
            status_code=503,
        )


def main() -> None:
    import uvicorn

    port = int(os.getenv("PORT", settings.port))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
