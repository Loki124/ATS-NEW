"""Core DRF 权限类

按 PRD §4 实现的权限矩阵 + 字段级 ACL 接口
"""
from rest_framework import permissions


class IsAuthenticated(permissions.IsAuthenticated):
    """基础已认证"""
    pass


class IsSuperAdmin(permissions.BasePermission):
    """超级管理员"""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        # Django superuser 始终通过
        if getattr(request.user, 'is_superuser', False):
            return True
        return request.user.user_roles.filter(role__code='SUPER_ADMIN').exists()


class IsHRBP(permissions.BasePermission):
    """HRBP 及以上"""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.is_superuser or request.user.user_roles.filter(
            role__code__in=['SUPER_ADMIN', 'HRBP']
        ).exists()


class IsHROrAbove(permissions.BasePermission):
    """HR 及以上"""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.is_superuser or request.user.user_roles.filter(
            role__code__in=['SUPER_ADMIN', 'HRBP', 'HR']
        ).exists()


class IsPositionRelated(permissions.BasePermission):
    """基于职位角色的候选人查看权限（简化版）"""
    message = '仅职位相关人员（用人经理/面试官/HR）可查看候选人'

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False

        # 超级管理员 / HRBP / HR：可看所有
        if request.user.user_roles.filter(
            role__code__in=['SUPER_ADMIN', 'HRBP', 'HR']
        ).exists():
            return True

        # 用人经理 / 面试官：仅本部门职位
        user_dept = request.user.department
        if user_dept and hasattr(obj, 'position') and obj.position.department_id == user_dept.id:
            return True

        return False


class HasProcessPermission(permissions.BasePermission):
    """流程配置权限 - HRBP 及以上可配置"""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser or request.user.user_roles.filter(
            role__code__in=['SUPER_ADMIN', 'HRBP']
        ).exists()
