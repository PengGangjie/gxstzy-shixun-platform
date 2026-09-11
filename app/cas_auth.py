# -*- coding: utf-8 -*-
"""学校统一身份认证平台（CAS）单点登录。

协议与《统一身份认证平台单点登录JAVA接口文档》一致（联想 UAP，标准 CAS）：
  1) 浏览器 → GET /cas/login → 302 {CAS_SERVER}login?service={CAS_SERVICE_URL}
  2) 平台认证成功 → 302 {CAS_SERVICE_URL}?ticket=ST-xxx
  3) 服务端 GET {CAS_SERVER}serviceValidate?ticket=..&service=.. → XML <cas:user>工号</cas:user>

平台只返回用户名（工号/学号），无姓名/邮箱/身份类型属性；
角色分配沿用平台既有 RBAC（管理员后台指派）。
"""
from __future__ import annotations

import base64
import logging
import re
import tempfile
from pathlib import Path
from typing import Any

import httpx

from .config import get_settings

logger = logging.getLogger("shixun.cas")

# 只提取 <cas:user> 文本，不引 XML 解析器（避免实体解析面）
_CAS_USER_RE = re.compile(r"<cas:user>\s*([^<>&\"]{1,64})\s*</cas:user>")


def cas_enabled() -> bool:
    return bool(get_settings().cas_server)


def _norm_base(url: str) -> str:
    return url if url.endswith("/") else url + "/"


def cas_login_url() -> str:
    s = get_settings()
    return _norm_base(s.cas_server) + "login"


def cas_logout_url() -> str:
    s = get_settings()
    return _norm_base(s.cas_server) + "logout"


def cas_validate_url() -> str:
    s = get_settings()
    return _norm_base(s.cas_server) + "serviceValidate"


def service_url() -> str:
    """login 与 serviceValidate 的 service 参数必须逐字一致（CAS 标准）。"""
    s = get_settings()
    if s.cas_service_url:
        return s.cas_service_url
    return s.logto_redirect_uri.rsplit("/", 1)[0] + "/cas/callback"


def _tls_verify() -> bool | str:
    s = get_settings()
    raw = (s.cas_tls_verify or "true").strip().lower()
    if raw in {"false", "no", "0"}:
        logger.warning("CAS TLS 证书校验已关闭（仅限自签证书联调期，禁止长期使用）")
        return False
    if s.cas_tls_ca_b64:
        # 自签证书：信息中心提供 yuap.crt，base64 注入环境变量（容器内无挂载路径）
        try:
            pem = base64.b64decode(s.cas_tls_ca_b64)
            path = Path(tempfile.gettempdir()) / "shixun_cas_ca.pem"
            path.write_bytes(pem)
            return str(path)
        except Exception:  # noqa: BLE001
            logger.exception("CAS_TLS_CA_B64 解码失败，回退默认证书校验")
    return True


def validate_ticket(ticket: str) -> str | None:
    """服务端验票，成功返回用户名（工号/学号），失败返回 None。

    ticket 一次性，由认证平台防重放；service 与登录时完全一致。
    """
    params = {"ticket": ticket[:128], "service": service_url()}
    try:
        resp = httpx.get(
            cas_validate_url(),
            params=params,
            verify=_tls_verify(),
            timeout=10.0,
            follow_redirects=False,
        )
    except httpx.HTTPError:
        logger.exception("CAS 验票请求失败（应用服务器到认证平台不可达？）")
        return None
    if resp.status_code != 200:
        logger.error("CAS 验票非 200：status=%s body=%.200s", resp.status_code, resp.text)
        return None
    m = _CAS_USER_RE.search(resp.text)
    if not m:
        # 常见于：应用地址未在平台注册 / 账号未授权 / ticket 已被使用
        logger.warning("CAS 验票未返回 cas:user：body=%.300s", resp.text)
        return None
    return m.group(1).strip()


def build_session_user(username: str) -> dict[str, Any]:
    """CAS 身份写入本地会话的结构（load_db_user / api/me 消费）。"""
    return {
        "sub": f"cas:{username}",
        "username": username,
        "email": None,
        "name": username,
        "source": "cas",
    }
