"""Reason Library 权限类 (T03).

双权限策略 (Q1/Q2):
- IsSuperUserOrReadOnly: 用于 system=True 的 scene_rule + 其下级 (rule_category / assignment)
- IsAdminOrReadOnly:    用于 system=False 的 custom 资源
- IsAuthenticatedReadOnly: 通用"登录可读, 写交由上两类"

与项目现有 ``apps.core.permissions`` 不复用 — 因为 core 用 V2 role-based
复杂模型, 本 app 仅依赖"超管/HR/普通用户"三档简单判定, 自己写更轻量。
但 ``is_superuser`` 仍走 ``request.user.is_superuser`` + ``apps.core.permissions.is_super_admin``
两路兜底 (超管优先)。
"""
from __future__ import annotations

from rest_framework import permissions

from apps.core.permissions import is_hr_or_above, is_super_admin


def _is_admin_user(user) -> bool:
    """判定: 超管 OR HR 及以上 (含 hr_specialist / hr_admin)。"""
    return bool(user and user.is_authenticated and (is_super_admin(user) or is_hr_or_above(user)))


class IsAuthenticatedReadOnly(permissions.BasePermission):
    """仅校验登录 — 写权限交由同 view 的其它 permission_classes (如 IsAdminOrReadOnly) 判定。

    设计说明 (P0-2 BugFix):
    - 旧实现按 SAFE_METHODS 分支: 写方法直接 return False, 会让 permission_classes
      与 IsAdminOrReadOnly / IsSuperUserOrReadOnly 形成 AND 拒绝 → 任何写操作 403,
      包括超管。
    - 新语义: 只校验"已登录", 不区分读/写, 让 view 组合里的角色判定类自行决定写权限。
    """

    message = '需要登录; 写接口权限见其它 permission'

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)


class IsAdminOrReadOnly(permissions.BasePermission):
    """custom 资源: admin (超管/HR) 可写, 其它登录用户只读。"""

    message = '需要 HR 及以上权限'

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return _is_admin_user(user)


class IsSuperUserOrReadOnly(permissions.BasePermission):
    """system 资源: 仅超管可写, 其它登录用户只读。"""

    message = '系统预置资源仅超管可改'

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(is_super_admin(user))


class SystemOrAdminPermission(permissions.BasePermission):
    """动态选择权限: 系统资源走 IsSuperUserOrReadOnly, custom 走 IsAdminOrReadOnly。

    用于 scene_rule 的 PATCH / DELETE / wizard: 同一 view 内根据 rule.is_system 切换。
    View 需在 ``has_object_permission`` 中比对, ``has_permission`` 对安全方法全放行。
    """

    message = '权限不足'

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        # list / create: superuser_or_admin 通用入口 (create 创建时无法预知 is_system)
        return _is_admin_user(user)

    def has_object_permission(self, request, view, obj) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        # obj 是 SceneRule 实例
        is_system = getattr(obj, 'is_system', False)
        if is_system:
            return bool(is_super_admin(request.user))
        return _is_admin_user(request.user)
