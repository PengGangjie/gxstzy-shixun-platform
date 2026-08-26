# -*- coding: utf-8 -*-
"""五类使用群体：角色码、中文名、能力与指派规则。"""
from __future__ import annotations

from typing import Any

ROLES = (
    "jw_admin",
    "college_admin",
    "lab_tech",
    "teacher",
    "student",
)

ROLE_LABELS: dict[str, str] = {
    "jw_admin": "教务处管理员",
    "college_admin": "学院管理员",
    "lab_tech": "实验员",
    "teacher": "教师",
    "student": "学生",
}

# 旧库遗留值 → 五类
ROLE_ALIASES: dict[str, str] = {
    "admin": "jw_admin",
    "staff": "student",
    "viewer": "student",
    "college": "college_admin",
}

COLLEGES = (
    "林学院",
    "经贸学院",
    "园林学院",
    "设计学院",
    "旅游学院",
    "汽信学院",
    "建工学院",
    "环保学院",
    "智造学院",
    "通识学院",
)

# 学院管理员可指派的角色（不可造教务处管理员）
COLLEGE_ADMIN_ASSIGNABLE = frozenset({"lab_tech", "teacher", "student"})


def normalize_role(role: str | None) -> str:
    raw = (role or "student").strip()
    if raw in ROLE_ALIASES:
        return ROLE_ALIASES[raw]
    if raw in ROLES:
        return raw
    return "student"


def role_label(role: str | None) -> str:
    return ROLE_LABELS.get(normalize_role(role), "学生")


def capabilities(user: dict[str, Any] | None) -> set[str]:
    if not user:
        return set()
    role = normalize_role(user.get("role"))
    caps: set[str] = {"home.read", "regs.read", "xnfz.read", "future.read"}
    if role == "jw_admin":
        caps |= {
            "inspect.read",
            "yishi.read",
            "ledger.read",
            "ledger.write",
            "shixun_ke.read",
            "cockpit.read",
            "users.manage_all",
            "admin.panel",
            "rooms.write",
        }
    elif role == "college_admin":
        caps |= {
            "inspect.read",
            "yishi.read",
            "ledger.read",
            "ledger.write",
            "shixun_ke.read",
            "cockpit.read",
            "users.manage_college",
            "rooms.write",
        }
    elif role == "lab_tech":
        caps |= {"yishi.read", "ledger.read", "ledger.write", "cockpit.read", "rooms.write"}
    elif role == "teacher":
        caps |= {"yishi.read", "ledger.read", "cockpit.read", "rooms.write"}
    # student：仅基础学习向
    return caps


def data_scope(user: dict[str, Any] | None) -> dict[str, Any]:
    if not user:
        return {"mode": "none", "college": None, "rooms": None}
    role = normalize_role(user.get("role"))
    college = (user.get("college") or "").strip() or None
    rooms = user.get("lab_rooms")
    if role == "jw_admin":
        return {"mode": "all", "college": None, "rooms": None}
    if role in {"college_admin", "teacher"}:
        return {"mode": "college" if college else "none", "college": college, "rooms": None}
    if role == "lab_tech":
        if isinstance(rooms, list) and rooms:
            return {"mode": "rooms", "college": college, "rooms": rooms}
        return {"mode": "college" if college else "none", "college": college, "rooms": None}
    return {"mode": "none", "college": college, "rooms": None}


def can_assign_role(
    actor: dict[str, Any],
    target_role: str,
    target_college: str | None,
) -> tuple[bool, str]:
    """返回 (是否允许, 错误说明)。"""
    actor_role = normalize_role(actor.get("role"))
    target_role = normalize_role(target_role)
    if target_role not in ROLES:
        return False, "无效角色"
    if actor_role == "jw_admin":
        if target_role != "jw_admin" and not (target_college or "").strip():
            # 非教务处管理员建议带学院，但不强制 jw_admin
            pass
        return True, ""
    if actor_role == "college_admin":
        if target_role not in COLLEGE_ADMIN_ASSIGNABLE:
            return False, "学院管理员只能指派：实验员 / 教师 / 学生"
        actor_college = (actor.get("college") or "").strip()
        if not actor_college:
            return False, "请先完善您的所属学院"
        if (target_college or "").strip() != actor_college:
            return False, "只能管理本院用户"
        return True, ""
    return False, "无用户管理权限"


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    role = normalize_role(user.get("role"))
    return {
        "sub": user.get("logto_sub") or user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "phone": user.get("phone"),
        "role": role,
        "role_label": role_label(role),
        "college": user.get("college"),
        "lab_rooms": user.get("lab_rooms") or [],
        "capabilities": sorted(capabilities(user)),
        "scope": data_scope(user),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }
