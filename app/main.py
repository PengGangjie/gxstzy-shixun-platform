# -*- coding: utf-8 -*-
"""实训科管理平台 · FastAPI（Logto + Turso + 静态站点 + 教务处权限后台）。"""
from __future__ import annotations

import os
from typing import Any, Union

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from logto import LogtoClient, LogtoConfig, Storage, UserInfoScope
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .db import get_user_by_sub, list_users, ping_db, set_user_role, upsert_user
from .roles import (
    COLLEGES,
    ROLE_LABELS,
    ROLES,
    can_assign_role,
    capabilities,
    normalize_role,
    public_user,
)

PUBLIC_PREFIXES = (
    "/health",
    "/sign-in",
    "/callback",
    "/sign-out",
    "/assets/",
)

# 静态资源扩展名：须已登录会话（中间件在 isAuthenticated 后放行）
STATIC_ASSET_SUFFIXES = (
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
    ".map",
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


def _email_is_bootstrap_admin(email: str | None) -> bool:
    if not email or not settings.admin_emails:
        return False
    return email.strip().lower() in settings.admin_emails


def load_db_user(request: Request) -> dict[str, Any] | None:
    client = logto_client(request)
    if not client.isAuthenticated():
        return None
    claims = client.getIdTokenClaims()
    if not claims or not claims.sub:
        return None
    return get_user_by_sub(claims.sub)


def require_capability(user: dict[str, Any] | None, cap: str) -> JSONResponse | None:
    if not user:
        return JSONResponse({"detail": "未登录"}, status_code=401)
    if cap not in capabilities(user):
        return JSONResponse({"detail": "无权限"}, status_code=403)
    return None


class SetRoleBody(BaseModel):
    role: str
    college: str | None = None
    lab_rooms: list[str] = Field(default_factory=list)


@app.middleware("http")
async def require_auth(request: Request, call_next):
    if not settings.auth_required or not auth_configured():
        return await call_next(request)
    path = request.url.path
    if path.startswith(PUBLIC_PREFIXES):
        return await call_next(request)

    client = logto_client(request)
    authenticated = client.isAuthenticated()

    # 敏感 JSON 必须登录；纯静态资源扩展名也须登录（防未登录直链）
    if path.endswith(STATIC_ASSET_SUFFIXES) or path.endswith(".json"):
        if authenticated:
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "未登录"}, status_code=401)
        return RedirectResponse("/sign-in")

    if not authenticated:
        if path.startswith("/api/"):
            return JSONResponse({"detail": "未登录"}, status_code=401)
        return RedirectResponse("/sign-in")

    # 教务处后台页：仅 jw_admin；管理 API：jw_admin 或学院管理员（本院）
    if path.startswith("/admin"):
        user = load_db_user(request)
        if not user or "admin.panel" not in capabilities(user):
            return JSONResponse(
                {
                    "detail": "需要教务处管理员权限",
                    "hint": "请联系已授权管理员，或将 ADMIN_EMAILS 设为您的邮箱后重新登录。",
                    "home": "/",
                },
                status_code=403,
            )
    elif path.startswith("/api/admin"):
        user = load_db_user(request)
        caps = capabilities(user) if user else set()
        if "admin.panel" not in caps and "users.manage_college" not in caps:
            return JSONResponse({"detail": "需要管理员权限"}, status_code=403)

    return await call_next(request)


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
        email = getattr(claims, "email", None)
        upsert_user(
            claims.sub,
            email,
            getattr(claims, "name", None),
            getattr(claims, "phone_number", None),
            default_role="student",
            promote_to_jw_admin=_email_is_bootstrap_admin(email),
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
    sub = claims.sub if claims else None
    user = get_user_by_sub(sub) if sub else None
    if not user and claims and sub:
        email = getattr(claims, "email", None)
        user = upsert_user(
            sub,
            email,
            getattr(claims, "name", None),
            getattr(claims, "phone_number", None),
            default_role="student",
            promote_to_jw_admin=_email_is_bootstrap_admin(email),
        )
    body: dict[str, Any] = {
        "authenticated": True,
        "sub": sub,
        "email": getattr(claims, "email", None) if claims else None,
        "phone": getattr(claims, "phone_number", None) if claims else None,
        "name": getattr(claims, "name", None) if claims else None,
    }
    if user:
        body.update(public_user(user))
        body["admin_panel"] = "/admin/" if "admin.panel" in capabilities(user) else None
    return body


@app.get("/api/meta/roles")
async def meta_roles(request: Request):
    user = load_db_user(request)
    err = require_capability(user, "admin.panel")
    if err:
        # 学院管理员也需要角色列表时放开只读元数据：已登录即可
        if not user:
            return err
    return {
        "roles": [{"id": r, "label": ROLE_LABELS[r]} for r in ROLES],
        "colleges": list(COLLEGES),
    }


@app.get("/api/admin/users")
async def admin_list_users(request: Request):
    user = load_db_user(request)
    err = require_capability(user, "users.manage_all")
    if err:
        # 学院管理员：本院列表
        err2 = require_capability(user, "users.manage_college")
        if err2:
            return err2
        college = (user or {}).get("college")
        if not college:
            return JSONResponse({"detail": "请先完善所属学院"}, status_code=400)
        rows = list_users(college=college)
        return {"users": [public_user(u) for u in rows], "scope": "college"}
    rows = list_users()
    return {"users": [public_user(u) for u in rows], "scope": "all"}


@app.post("/api/admin/users/{sub}/role")
async def admin_set_role(sub: str, body: SetRoleBody, request: Request):
    actor = load_db_user(request)
    if not actor:
        return JSONResponse({"detail": "未登录"}, status_code=401)
    if "users.manage_all" not in capabilities(actor) and "users.manage_college" not in capabilities(
        actor
    ):
        return JSONResponse({"detail": "无权限"}, status_code=403)

    role = normalize_role(body.role)
    college = body.college
    ok, msg = can_assign_role(actor, role, college)
    if not ok:
        return JSONResponse({"detail": msg}, status_code=403)

    # 教务处管理员可不填学院；其他角色建议填写
    if role != "jw_admin" and not (college or "").strip():
        return JSONResponse({"detail": "请选择所属学院"}, status_code=400)
    if college and college not in COLLEGES and role != "jw_admin":
        return JSONResponse({"detail": f"学院须为：{', '.join(COLLEGES)}"}, status_code=400)

    try:
        updated = set_user_role(
            sub,
            role,
            None if role == "jw_admin" else college,
            body.lab_rooms if role == "lab_tech" else [],
            actor_sub=actor.get("logto_sub"),
        )
    except KeyError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=404)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"detail": f"更新失败：{exc}"}, status_code=500)

    return {"ok": True, "user": public_user(updated)}


@app.get("/admin")
@app.get("/admin/")
async def admin_panel():
    """教务处权限后台（中间件已校验 jw_admin）。"""
    page = settings.static_dir / "admin" / "index.html"
    if not page.is_file():
        return JSONResponse({"detail": "后台页面缺失"}, status_code=503)
    return FileResponse(page)


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
