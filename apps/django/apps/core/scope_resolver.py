"""4 层 scope 堆栈解析器 (L1 user级 > L2 role级 > L3 tenant级 > L4 SELF兜底)."""
from django.db.utils import OperationalError, ProgrammingError

from .models_permission_v2 import UserRoleV2, RoleV2, TenantConfig
from .models import Department


def resolve_scope(user, resource_code: str = None) -> dict:
    """返回 {'management_unit_ids': list[int]} 或 {'all': True}.

    4 层堆栈 (从高到低优先级):
      L1: user_role.management_unit_ids (非 NULL + 非空)
      L2: role.default_data_scope_type (DB default NULL)
      L3: tenant_config 'GLOBAL_DEFAULT_DATA_SCOPE'
      L4: 硬编码兜底 'SELF'

    T17 schema 未应用前: user_roles/roles 表缺 V2 列, 任何 .filter() 都会抛
    OperationalError. catch 后降级到 L3/L4 (保守兜底, 不放行 ALL scope)."""
    if not (user and user.is_authenticated):
        return {'management_unit_ids': []}

    # L1: user 级显式配置
    explicit_units = []
    role_codes = []
    try:
        user_roles = list(UserRoleV2.objects.filter(user_id=user.pk))
        for ur in user_roles:
            # management_unit_ids 在 T17 之前是 V2-only column, try/except 守护
            try:
                units = ur.management_unit_ids
            except Exception:
                units = None
            if units:
                explicit_units.extend(units or [])
            try:
                role_codes.append(ur.role_code)
            except Exception:
                pass
    except (OperationalError, ProgrammingError):
        # V2 schema 未应用 → user_roles 表缺 V2 列. 跳到 L3.
        pass
    if explicit_units:
        return {'management_unit_ids': list(set(explicit_units))}

    # L2: role 级默认 scope (同样 try/except 守护 default_data_scope_type)
    if role_codes:
        try:
            roles = RoleV2.objects.filter(role_code__in=role_codes, status=1)
            for r in roles:
                scope_type = getattr(r, 'default_data_scope_type', None)
                if scope_type == 'ALL':
                    return {'all': True}
                if scope_type == 'DEPT':
                    _ = _dept_ids(user)
                    return {'management_unit_ids': []}
                # SELF/DEPT_AND_SUB 走 L3/L4
        except (OperationalError, ProgrammingError):
            pass
        except Exception:
            pass

    # L3: tenant 全局
    cfg = TenantConfig.objects.filter(
        config_key='GLOBAL_DEFAULT_DATA_SCOPE', system_code='recruit').first()
    if cfg and cfg.config_value == 'ALL':
        return {'all': True}

    # L4: 兜底 SELF
    return {'management_unit_ids': []}


def _dept_ids(user) -> list:
    """返回 user.department + 所有 ancestor (含自身)."""
    if not getattr(user, 'department_id', None):
        return []
    dept = Department.objects.filter(id=user.department_id).first()
    if not dept:
        return []
    ids = {dept.id}
    node = dept.parent
    while node:
        ids.add(node.id)
        node = node.parent
    return list(ids)