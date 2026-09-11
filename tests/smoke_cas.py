# -*- coding: utf-8 -*-
"""CAS 统一身份认证对接冒烟测试（不触网：mock 验票与数据库）。

用法：cd output/gxstzy-shixun-platform && ../../venv/Scripts/python.exe tests/smoke_cas.py
"""
from __future__ import annotations

import os
import secrets as pysecrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE_ENV = {
    "AUTH_REQUIRED": "true",
    "SESSION_SECRET": "test-session-secret-" + pysecrets.token_urlsafe(24),
    "LOGTO_ENDPOINT": "https://logto.test.example",
    "LOGTO_APP_ID": "test-app-id",
    "LOGTO_APP_SECRET": "test-app-secret",
    "PUBLIC_BASE_URL": "http://testserver",
    # 必须显式设置：否则 secrets/.env 的生产 https 回调会被 dotenv 注入，
    # 使 SessionMiddleware https_only=true（http 测试域存不了 Secure cookie）
    "LOGTO_REDIRECT_URI": "http://testserver/callback",
}

PASS = 0
FAIL = 0


def check(name: str, cond: bool, extra: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {extra}")


def set_env(**kv):
    os.environ.update(BASE_ENV)
    for k in ("CAS_SERVER", "CAS_SERVICE_URL", "ADMIN_CAS_ACCOUNTS"):
        os.environ.pop(k, None)
    os.environ.update({k: v for k, v in kv.items() if v is not None})
    for k, v in kv.items():
        if v is None and k in os.environ:
            os.environ.pop(k)


def fresh_app():
    from app.config import get_settings

    get_settings.cache_clear()
    import importlib

    import app.main as m

    importlib.reload(m)
    return m


def fake_users(m):
    """替换数据库层：内存用户表。"""
    store: dict[str, dict] = {}

    def get_user_by_sub(sub):
        return store.get(sub)

    def upsert_user(sub, email, name, phone=None, *, default_role="student", promote_to_jw_admin=False):
        if sub not in store:
            store[sub] = {
                "logto_sub": sub,
                "email": email,
                "name": name,
                "phone": phone,
                "role": "jw_admin" if promote_to_jw_admin else default_role,
                "college": None,
                "lab_rooms": [],
            }
        elif promote_to_jw_admin:
            store[sub]["role"] = "jw_admin"
        return store[sub]

    m.get_user_by_sub = get_user_by_sub
    m.upsert_user = upsert_user
    return store


def test_disabled_by_default():
    print("[CAS 未配置：行为不变]")
    set_env()
    m = fresh_app()
    fake_users(m)
    from fastapi.testclient import TestClient

    with TestClient(m.app) as client:
        r = client.get("/api/me")
        check("/api/me cas_login=null", r.json().get("cas_login") is None)
        r = client.get("/cas/login", follow_redirects=False)
        check("/cas/login 404", r.status_code == 404)
        r = client.get("/cas/callback?ticket=ST-1", follow_redirects=False)
        check("/cas/callback 404", r.status_code == 404)
        # 原登录墙不受影响
        r = client.get("/lab_docs_index.json")
        check("JSON 仍 401", r.status_code == 401)


def test_enabled_flow():
    print("[CAS 已配置：完整登录流程]")
    set_env(CAS_SERVER="https://cas.test.edu.cn/lyuapServer", ADMIN_CAS_ACCOUNTS="102627184")
    m = fresh_app()
    store = fake_users(m)
    from fastapi.testclient import TestClient

    with TestClient(m.app) as client:
        # 1) 登录入口
        r = client.get("/cas/login", follow_redirects=False)
        loc = r.headers.get("location", "")
        check("/cas/login 302 到认证平台", r.status_code == 307 and loc.startswith("https://cas.test.edu.cn/lyuapServer/login?service="))
        check("service 指向回调", "service=http%3A%2F%2Ftestserver%2Fcas%2Fcallback" in loc, loc)

        r = client.get("/api/me")
        check("/api/me 返回 cas_login 入口", r.json().get("cas_login") == "/cas/login")

        # 2) 验票成功 → 建户 → 落会话 → 回跳
        m.cas_auth.validate_ticket = lambda t: "102627184" if t == "ST-OK" else None
        r = client.get("/cas/callback?ticket=ST-OK", follow_redirects=False)
        check("验票成功 307 回首页", r.status_code == 307 and r.headers["location"] == "/")
        check("用户入库（cas:工号）", "cas:102627184" in store)
        check("ADMIN_CAS_ACCOUNTS 引导为 jw_admin", store["cas:102627184"]["role"] == "jw_admin")

        r = client.get("/api/me")
        body = r.json()
        check("会话已登录 source=cas", body.get("authenticated") is True and body.get("source") == "cas")
        check("sub=cas:102627184", body.get("sub") == "cas:102627184")
        check("管理员后台入口出现", body.get("admin_panel") == "/admin/")

        # 3) 登录墙对 CAS 会话放行
        r = client.get("/lab_docs_index.json")
        check("CAS 会话访问 JSON 200", r.status_code == 200)

        # 4) next 回跳
        client2 = TestClient(m.app)
        client2.get("/cas/login?next=/platform-08-rooms.html", follow_redirects=False)
        client2.get("/cas/callback?ticket=ST-OK", follow_redirects=False)
        # 上面同一票据复用在此 mock 下不防重放（真实平台一次性），只验证 next 逻辑：
        r = client2.get("/cas/login?next=//evil.com", follow_redirects=False)
        check("next=//evil.com 仍正常跳 CAS（next 被丢弃）", r.status_code == 307 and r.headers["location"].startswith("https://cas.test.edu.cn"))

        # 5) 验票失败 → 401 提示
        client3 = TestClient(m.app)
        client3.get("/cas/login", follow_redirects=False)
        r = client3.get("/cas/callback?ticket=ST-BAD", follow_redirects=False)
        check("验票失败 401", r.status_code == 401)
        check("失败提示含原因指引", "注册" in r.text and "授权" in r.text)
        r = client3.get("/cas/callback", follow_redirects=False)
        check("无 ticket 302 回 /cas/login", r.status_code == 307 and r.headers["location"] == "/cas/login")

        # 6) 登出：CAS 用户清会话并跳平台登出
        r = client.get("/sign-out", follow_redirects=False)
        loc = r.headers.get("location", "")
        check("CAS 登出跳认证平台 logout", r.status_code in (302, 307) and loc.startswith("https://cas.test.edu.cn/lyuapServer/logout"))
        client.cookies.clear()
        r = client.get("/api/me")
        check("登出后会话失效", r.json().get("authenticated") is False)


def test_validate_ticket_unit():
    print("[validate_ticket 单元：XML/HTTP 异常分支]")
    set_env(CAS_SERVER="https://cas.test.edu.cn/lyuapServer")
    m = fresh_app()
    import importlib

    from app import cas_auth

    # 前一阶段把 validate_ticket mock 成了 lambda，reload 恢复原实现再测
    importlib.reload(cas_auth)

    class FakeResp:
        def __init__(self, status_code=200, text=""):
            self.status_code = status_code
            self.text = text

    def run_with(resp=None, exc=None):
        captured = {}

        def fake_get(url, params=None, **kw):
            captured["url"] = url
            captured["params"] = params
            if exc:
                raise exc
            return resp

        cas_auth.httpx.get = fake_get
        out = cas_auth.validate_ticket("ST-X")
        return out, captured

    ok_xml = '<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas"><cas:authenticationSuccess><cas:user>20190001</cas:user></cas:authenticationSuccess></cas:serviceResponse>'
    out, cap = run_with(resp=FakeResp(text=ok_xml))
    check("成功解析 cas:user", out == "20190001")
    check("service 参数与 login 一致", cap["params"]["service"].endswith("/cas/callback"))
    check("ticket 透传", cap["params"]["ticket"] == "ST-X")

    fail_xml = '<cas:serviceResponse><cas:authenticationFailure code="INVALID_TICKET">ticket 不合法</cas:authenticationFailure></cas:serviceResponse>'
    out, _ = run_with(resp=FakeResp(text=fail_xml))
    check("失败 XML 返回 None", out is None)

    out, _ = run_with(resp=FakeResp(status_code=500, text="err"))
    check("非 200 返回 None", out is None)

    import httpx as _hx

    out, _ = run_with(exc=_hx.ConnectError("refused"))
    check("网络异常返回 None", out is None)

    # XSS 尝试：user 字段带标签应被正则拒绝
    evil = "<cas:user><script>alert(1)</script></cas:user>"
    out, _ = run_with(resp=FakeResp(text=evil))
    check("cas:user 含标签被拒绝", out is None)


if __name__ == "__main__":
    test_disabled_by_default()
    test_enabled_flow()
    test_validate_ticket_unit()
    print(f"\n结果：{PASS} 通过，{FAIL} 失败")
    sys.exit(1 if FAIL else 0)
