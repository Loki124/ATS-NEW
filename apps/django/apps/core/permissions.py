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


def is_super_admin(user) -> bool:
    """统一判断超级管理员（is_superuser 或 SUPER_ADMIN 角色）"""
    if not (user and user.is_authenticated):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return user.user_roles.filter(role__code='SUPER_ADMIN').exists()


def is_hr_or_above(user) -> bool:
    """统一判断 HR 及以上"""
    if not (user and user.is_authenticated):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return user.user_roles.filter(
        role__code__in=['SUPER_ADMIN', 'HRBP', 'HR']
    ).exists()


def user_department_ids(user) -> set:
    """返回用户所属部门 + 所有祖先部门的 ID 集合（含自己所在部门）。

    用于按部门树过滤业务记录。
    """
    if not (user and user.is_authenticated):
        return set()
    if not getattr(user, 'department_id', None):
        return set()
    from apps.core.models import Department  # 避免循环
    dept = Department.objects.filter(id=user.department_id).first()
    if not dept:
        return set()
    ids = {dept.id}
    parent = dept.parent
    while parent:
        ids.add(parent.id)
        parent = parent.parent
    return ids


class ScopedQuerysetMixin:
    """通用 queryset scope 过滤。

    在 get_queryset() 阶段按以下优先级过滤:
    1. 超级管理员: 不限
    2. HR/HRBP: 仅同部门 + 子部门（按 path 前缀匹配）创建/负责的记录
    3. 其它角色（用人经理/面试官/推荐人）: 仅自己创建或被分配的记录

    用法：ViewSet 在 get_queryset() 末尾调用 `qs = self.scope_queryset(qs, scope_field='department')`.
    其中 scope_field 是模型上的 ForeignKey 字段名（如 'department', 'position__department'）。
    """

    scope_field: str = ''  # 子类覆盖：'department' / 'position__department' / '' 等
    scope_creator_field: str = 'created_by'  # 创建人字段

    def scope_queryset(self, qs, scope_field: str = '', creator_field: str = ''):
        user = self.request.user
        if is_super_admin(user):
            return qs
        scope_field = scope_field or self.scope_field
        creator_field = creator_field or self.scope_creator_field

        if is_hr_or_above(user):
            # HR 范围: 自己部门 + 自己部门的子部门（向下爬 tree, 不向上到祖先的兄弟分支）
            # 例: hr_sales 在 sales (path=/总部/销售部) → 范围 [sales, sales_team1], 不含 eng (hq 的另一个子)
            # 例: hr 在 hq (path=/总部) → 范围 = 全公司
            from apps.core.models import Department
            user_dept = Department.objects.filter(id=getattr(user, 'department_id', None)).first()
            if not user_dept:
                # HR 没有部门: 仅看自己创建的
                return qs.filter(**{creator_field: user})
            user_path = user_dept.path or f'/{user_dept.name}'
            # 收: 自己部门 + 自己 path 的所有后代 (path 严格前缀匹配)
            sub_dept_ids = set()
            for d in Department.objects.filter(is_active=True).values('id', 'path'):
                p = d['path'] or ''
                if p == user_path or p.startswith(user_path.rstrip('/') + '/'):
                    sub_dept_ids.add(d['id'])
            sub_dept_ids.add(user_dept.id)
            return qs.filter(**{f'{scope_field}__id__in': sub_dept_ids})
        # 普通用户（用人经理/面试官/推荐人）：仅自己创建或被分配
        return qs.filter(**{creator_field: user})


class UserViewPermission(permissions.BasePermission):
    """User ViewSet 权限:
    - 列表 / 搜索 / active: HRBP+
    - 详情: 自己 OR HRBP+
    - 修改/删除: SUPER_ADMIN
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return is_hr_or_above(request.user)
        return is_super_admin(request.user)

    def has_object_permission(self, request, view, obj):
        if is_super_admin(request.user):
            return True
        if request.method in permissions.SAFE_METHODS:
            return obj.pk == request.user.pk or is_hr_or_above(request.user)
        return False


class MOUVIEWSetPermission(permissions.BasePermission):
    """MOU / 自动化规则 ViewSet 权限: 仅 HRBP+ 可读写。
    普通用户不可见 MOU 协议与容器。
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return is_hr_or_above(request.user)
        return request.user.is_superuser or request.user.user_roles.filter(
            role__code__in=['SUPER_ADMIN', 'HRBP']
        ).exists()
