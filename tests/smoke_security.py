# -*- coding: utf-8 -*-
"""安全加固冒烟测试（脚本式运行，不触网、不依赖真实 Logto/Turso）。

用法：cd output/gxstzy-shixun-platform && ../../venv/Scripts/python.exe tests/smoke_security.py
"""
from __future__ import annotations

import os
import secrets as pysecrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 必须在 import app 之前设置（load_dotenv override=False 不会覆盖已有 env）
os.environ.update(
    {
        "AUTH_REQUIRED": "true",
        "SESSION_SECRET": "test-session-secret-" + pysecrets.token_urlsafe(24),
        "LOGTO_ENDPOINT": "https://logto.test.example",
        "LOGTO_APP_ID": "test-app-id",
        "LOGTO_APP_SECRET": "test-app-secret",
        "PUBLIC_BASE_URL": "http://testserver",
    }
)
os.environ.pop("TURSO_DATABASE_URL", None)
os.environ.pop("TURSO_AUTH_TOKEN", None)

import app.main as m  # noqa: E402
from app.config import get_settings  # noqa: E402

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


def test_safe_next():
    print("[safe_next]")
    check("拒绝 //evil.com", m._safe_next("//evil.com") is None)
    check("拒绝 /\\evil.com（反斜杠协议相对）", m._safe_next("/\\evil.com") is None)
    check("拒绝 https://evil.com", m._safe_next("https://evil.com") is None)
    check("拒绝空值", m._safe_next("") is None and m._safe_next(None) is None)
    check("放行站内路径", m._safe_next("/rooms/index.html") == "/rooms/index.html")


def test_rate_limit():
    print("[write rate limit]")
    m._write_hits.clear()
    key = "w:test-user"
    for _ in range(m.WRITE_RATE_MAX):
        limited = m._rate_limited(key)
        if limited:
            break
    check(f"前 {m.WRITE_RATE_MAX} 次放行", not limited)
    check("超限后返回 True（429）", m._rate_limited(key) is True)
    m._write_hits.clear()


def test_settings_fail_fast():
    print("[session secret fail-fast]")
    saved = {k: os.environ.get(k) for k in ("SESSION_SECRET", "AUTH_REQUIRED")}
    try:
        get_settings.cache_clear()
        os.environ["SESSION_SECRET"] = "dev-change-me-in-production"
        os.environ["AUTH_REQUIRED"] = "true"
        try:
            get_settings()
            check("弱默认 secret + AUTH_REQUIRED=true 应拒绝启动", False)
        except RuntimeError as e:
            check("弱默认 secret + AUTH_REQUIRED=true 应拒绝启动", "SESSION_SECRET" in str(e))

        get_settings.cache_clear()
        os.environ["SESSION_SECRET"] = ""
        os.environ["AUTH_REQUIRED"] = "true"
        try:
            get_settings()
            check("空 secret + AUTH_REQUIRED=true 应拒绝启动", False)
        except RuntimeError:
            check("空 secret + AUTH_REQUIRED=true 应拒绝启动", True)

        get_settings.cache_clear()
        os.environ["SESSION_SECRET"] = "dev-change-me-in-production"
        os.environ["AUTH_REQUIRED"] = "false"
        try:
            get_settings()
            check("AUTH_REQUIRED=false（本地免登录）可启动", True)
        except RuntimeError as e:
            check("AUTH_REQUIRED=false（本地免登录）可启动", False, str(e))
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        get_settings.cache_clear()
        get_settings()  # 恢复正常缓存


def test_http():
    print("[http middleware / headers / auth wall]")
    # 拦截 ping_db，注入「含内部信息的异常」，验证不回显
    inner_detail = "libsql: connect ECONNREFUSED db.turso.example.com:443 token=eyJhbGci"

    def fake_ping():
        raise RuntimeError(inner_detail)

    m.ping_db = fake_ping
    from fastapi.testclient import TestClient

    with TestClient(m.app) as client:
        r = client.get("/health")
        check("/health 200", r.status_code == 200)
        body = r.text
        check("/health 不回显异常详情", "ECONNREFUSED" not in body and "token=" not in body and "Traceback" not in body)
        check("/health 报 degraded", '"degraded"' in body and '"unreachable"' in body)

        r = client.get("/platform-01-regulations.html", follow_redirects=False)
        check("未登录模块页 307 跳登录", r.status_code == 307 and r.headers["location"].startswith("/sign-in"))

        r = client.get("/lab_docs_index.json")
        check("未登录 JSON 401", r.status_code == 401)

        r = client.get("/api/me")
        check("游客 /api/me 返回未登录态", r.status_code == 200 and '"authenticated":false' in r.text)

        r = client.get("/")
        check("游客首页 200", r.status_code == 200)

        r = client.get("/assets/guest-gate.js")
        check("公开 assets 200", r.status_code == 200)
        check("nosniff 头", r.headers.get("x-content-type-options") == "nosniff")
        check("X-Frame-Options 头", r.headers.get("x-frame-options") == "SAMEORIGIN")
        check("Referrer-Policy 头", "strict-origin" in (r.headers.get("referrer-policy") or ""))

        r = client.get("/admin/", follow_redirects=False)
        check("未登录 /admin/ 跳登录", r.status_code == 307 and "/sign-in" in r.headers.get("location", ""))

        # callback 异常不回显原始内容
        r = client.get("/callback?code=x&state=y")
        check("坏 callback 400", r.status_code == 400)
        check("坏 callback 不回显内部异常", "Traceback" not in r.text)


def test_static_escapes():
    print("[前端转义]")
    admin_html = (ROOT / "static" / "admin" / "index.html").read_text(encoding="utf-8")
    check("admin 页定义 esc()", "function esc(" in admin_html)
    check("admin 页 email 转义", "${esc(u.email" in admin_html)
    check("admin 页 name 转义", "${esc(u.name" in admin_html)
    check("admin 页 phone 转义", "${esc(u.phone" in admin_html)
    for rel in ("static-overlay/guest-gate.js", "static/assets/guest-gate.js"):
        js = (ROOT / rel).read_text(encoding="utf-8")
        check(f"{rel} 定义 escHtml", "function escHtml(" in js)
        check(f"{rel} 文本转义", "escHtml(name)" in js)
        check(f"{rel} 无裸拼 name", "· \" + name" not in js and '+ name : ""' not in js.replace("escHtml(name)", ""))


def test_body_limits():
    print("[体积/行数上限]")
    check("导入体积上限 <= 3MB", m.MAX_IMPORT_BYTES == 3 * 1024 * 1024)
    # CSV 超行数截断
    big_csv = ("name,model\n" + "\n".join(f"设备{i},M{i}" for i in range(2000))).encode()
    rows = m._parse_equip_upload("equip.csv", big_csv)
    check(f"CSV 解析截断到 {m.MAX_EQUIP_ROWS if hasattr(m, 'MAX_EQUIP_ROWS') else 500} 行", len(rows) <= 500, f"got {len(rows)}")
    from app import room_store

    check("设备字段截断配置", room_store.EQUIP_FIELD_LIMITS["name"] == 200)
    try:
        room_store.save_overrides("x", {"k": "v" * 200_000}, "tester")
        check("超大 overrides 应抛 ValueError", False)
    except ValueError:
        check("超大 overrides 应抛 ValueError", True)
    except Exception as e:  # Turso 未配置时也会抛错——须是 ValueError 才对
        check("超大 overrides 应抛 ValueError", False, f"raised {type(e).__name__}: {e}")


if __name__ == "__main__":
    test_safe_next()
    test_rate_limit()
    test_settings_fail_fast()
    test_http()
    test_static_escapes()
    test_body_limits()
    print(f"\n结果：{PASS} 通过，{FAIL} 失败")
    sys.exit(1 if FAIL else 0)
