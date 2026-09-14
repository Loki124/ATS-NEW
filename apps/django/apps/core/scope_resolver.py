"""4 层 scope 堆栈解析器 (L1 user级 > L2 role级 > L3 tenant级 > L4 SELF兜底)."""
import logging

from django.db.utils import OperationalError, ProgrammingError

from .models_permission_v2 import UserRoleV2, RoleV2, TenantConfig
from .models import Department

logger = logging.getLogger(__name__)


def resolve_scope(user, resource_code: str = None) -> dict:
    """返回下列三种形态之一:

      - {'all': True}                        全量可见
      - {'department_ids': list[str]}        按部门可见 (DEPT / DEPT_AND_SUB)
      - {'management_unit_ids': list[int]}   按管理单元可见 (空 list = SELF 兜底)

    4 层堆栈 (从高到低优先级):
      L1: user_role.management_unit_ids (非 NULL + 非空)
      L2: role.default_data_scope_type (DB default NULL)
      L3: tenant_config 'GLOBAL_DEFAULT_DATA_SCOPE'
      L4: 硬编码兜底 'SELF'

    T17 schema 未应用前: user_roles/roles 表缺 V2 列, 任何 .filter() 都会抛
    OperationalError. catch 后降级到 L3/L4 (保守兜底, 不放行 ALL scope).

    2026-08-03 R8 (寇豆码):
      原 L2 的 DEPT 分支写成 `_ = _dept_ids(user); return {'management_unit_ids': []}`
      —— 部门算出来直接丢进下划线扔掉, 返回空 list, 下游 ScopeQuerysetMixin
      看到空 list 就判 SELF。结果任何配了 DEPT 数据范围的角色实际只能看到自己
      创建的数据, 部门主管看不到组员的候选人。
      修复: DEPT 返回本部门 id 集合, DEPT_AND_SUB 返回本部门 + 所有子部门,
      并用独立的 'department_ids' key —— 因为 management_unit_ids 是
      ManagementUnit 的主键 (BigAuto int), 而部门主键是 CharField(32),
      两者不是一个 id 空间, 混用会被 ManagementUnit.objects.filter(id__in=...)
      静默过滤成空集。"""
    if not (user and user.is_authenticated):
        return {'management_unit_ids': []}

    # L1: user 级显式配置 + 收集 role_codes
    # ⚠️ P0-3 (CODE_QUALITY_AUDIT P0-3): V2 查询异常必须 fail-closed 到 SELF,
    #    不可静默 pass 后落到 L3 租户配置 (若 GLOBAL_DEFAULT_DATA_SCOPE=='ALL' 会放行全量)。
    explicit_units = []
    role_codes = []
    try:
        user_roles = list(UserRoleV2.objects.filter(user_id=user.pk))
        for ur in user_roles:
            # management_unit_ids 在 T17 之前是 V2-only column, try/except 守护
            try:
                units = ur.management_unit_ids
            except Exception:
                logger.warning('V2 user_roles.management_unit_ids 缺失 user_role_id=%s', getattr(ur, 'id', '?'))
                units = None
            if units:
                explicit_units.extend(units or [])
            try:
                role_codes.append(ur.role_code)
            except Exception:
                logger.warning('UserRole.role_code 缺失 user_role_id=%s', getattr(ur, 'id', '?'))
    except (OperationalError, ProgrammingError) as e:
        logger.exception('[scope_resolver] L1 user_roles 查询失败, fail-closed 到 SELF: %s', e)
        return {'management_unit_ids': []}

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
                    # R8: 本部门 (不含祖先 —— 含祖先等于向上越权)
                    own = _own_dept_ids(user)
                    if own:
                        return {'department_ids': own}
                    # 用户没挂部门 → 无法按部门圈范围, 落 L3/L4 保守兜底
                    continue
                if scope_type == 'DEPT_AND_SUB':
                    # R8: 本部门 + 所有子部门 (按 Department.path 前缀匹配)
                    sub = _dept_and_sub_ids(user)
                    if sub:
                        return {'department_ids': sub}
                    continue
                # SELF 走 L3/L4
        except (OperationalError, ProgrammingError) as e:
            logger.exception('[scope_resolver] L2 roles 查询失败, fail-closed 到 SELF: %s', e)
            return {'management_unit_ids': []}
        except Exception as e:
            # 非 DB 异常 (逻辑错误等) 同样 fail-closed, 不可静默放行
            logger.exception('[scope_resolver] L2 role scope 计算异常, fail-closed 到 SELF: %s', e)
            return {'management_unit_ids': []}

    # L3: tenant 全局 —— 仅当 L1/L2 正常完成才可达 (异常路径已在上方 fail-closed 返回)
    cfg = TenantConfig.objects.filter(
        config_key='GLOBAL_DEFAULT_DATA_SCOPE', system_code='recruit').first()
    if cfg and cfg.config_value == 'ALL':
        return {'all': True}

    # L4: 兜底 SELF
    return {'management_unit_ids': []}


def _own_dept_ids(user) -> list:
    """R8: DEPT 范围 —— 只包含用户自己所在部门.

    不含祖先: 祖先部门是"上级", 把上级塞进可见范围等于向上越权。
    不含子部门: 那是 DEPT_AND_SUB 的语义。
    """
    dept_id = getattr(user, 'department_id', None)
    if not dept_id:
        return []
    if not Department.objects.filter(id=dept_id).exists():
        return []
    return [dept_id]


def _dept_and_sub_ids(user) -> list:
    """R8: DEPT_AND_SUB 范围 —— 用户所在部门 + 其所有子孙部门.

    用 Department.path 前缀匹配向下爬树 (与 V1
    apps/core/permissions.py:ScopedQuerysetMixin 的 HR 范围口径一致)。
    path 为空时退化成只返回本部门。
    """
    dept_id = getattr(user, 'department_id', None)
    if not dept_id:
        return []
    dept = Department.objects.filter(id=dept_id).first()
    if not dept:
        return []
    ids = {dept.id}
    if dept.path:
        ids.update(
            Department.objects.filter(path__startswith=dept.path)
            .values_list('id', flat=True)
        )
    return list(ids)


def _dept_ids(user) -> list:
    """返回 user.department + 所有 ancestor (含自身).

    注意: 这是"向上"的集合, 语义上用于"我属于哪几层组织", 不适合直接当
    数据可见范围 (会向上越权)。R8 之后 resolve_scope 不再使用它,
    保留是因为 scripts/ 和历史调用方可能还依赖。
    """
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