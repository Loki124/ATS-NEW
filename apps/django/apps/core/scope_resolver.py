"""4 层 scope 堆栈解析器 (L1 user级 > L2 role级 > L3 tenant级 > L4 SELF兜底)."""
import logging

from django.db.utils import OperationalError, ProgrammingError

from .models import Department
from .models_permission_v2 import RoleV2, TenantConfig, UserRoleV2

logger = logging.getLogger(__name__)


def resolve_scope(user, resource_code: str = None, app_code: str = None) -> dict:
    """返回下列三种形态之一:

      - {'all': True}                        全量可见
      - {'department_ids': list[str]}        按部门可见 (DEPT / DEPT_AND_SUB)
      - {'management_unit_ids': list[int]}   按管理单元可见 (空 list = SELF 兜底)

    4 层堆栈 (从高到低优先级):
      L1: user_role.management_unit_ids (非 NULL + 非空); 方案 A(2026-09-15) 起,
          若传入 app_code 且 UserRoleV2.app_data_scopes 有该应用的范围, 优先用 per-app 范围
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
            except (AttributeError, TypeError):  # V2 字段缺失兜底 None, 不阻断 scope 计算 (向前兼容迁移期)
                logger.warning('V2 user_roles.management_unit_ids 缺失 user_role_id=%s', getattr(ur, 'id', '?'))
                units = None
            if units:
                explicit_units.extend(units or [])
            try:
                role_codes.append(ur.role_code)
            except (AttributeError, TypeError):  # V2 字段缺失兜底 (role_code 也是 V2-only column, 同 management_unit_ids)
                logger.warning('UserRole.role_code 缺失 user_role_id=%s', getattr(ur, 'id', '?'))
    except (OperationalError, ProgrammingError) as e:
        logger.exception('[scope_resolver] L1 user_roles 查询失败, fail-closed 到 SELF: %s', e)
        return {'management_unit_ids': []}

    # --- 方案 A(2026-09-15): 按应用范围优先 ---
    # app_code 命中 UserRoleV2.app_data_scopes(per-app) 时优先返回其 management_unit_ids;
    # 否则回退到下方全局兜底(UserRoleV2.management_unit_ids).
    # 数据源已合并进 UserRoleV2.app_data_scopes(独立 user_app_data_scope 表已删除).
    if app_code:
        try:
            app_units = []
            for ur in UserRoleV2.objects.filter(user_id=user.pk):
                scopes = ur.app_data_scopes or {}
                ids = scopes.get(app_code)
                if ids:
                    app_units.extend(ids or [])
            if app_units:
                return {'management_unit_ids': list(set(app_units))}
        except (OperationalError, ProgrammingError):
            # 表缺失/不可读 → 落在全局兜底
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
        except Exception as e:  # noqa: BLE001 — 非 DB 异常 (逻辑错误等) 同样 fail-closed, 不可静默放行
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


# 整公司级管理单元 (org_scope 形如 {"name":..., "level":"ROOT"}) 的标记 ——
# 表示"可见全量数据", 由 _sync_user_data_rule 转成 ALL 规则.
ALL_UNIT_SENTINEL = '__ALL__'

# org_scope 为 dict 时, 可能内嵌部门列表的子键
_DEPT_LIST_KEYS = ('department_ids', 'dept_ids', 'departments', 'org_ids')


def _expand_org_scope(os_, unit_include_children):
    """把 ManagementUnit.org_scope 展开为部门 id 集合(字符串化).

    支持三种写法(北森「组织范围」节点级包含下级 + 历史兼容):
      - 结构化列表 [{deptId, includeChildren}]: 每节点独立决定含不含子级;
      - 纯字符串列表 ['D1','D2']: 向后兼容, 统一套用单元级 include_children;
      - dict: 部门列表子键(department_ids/dept_ids/...) 或 ROOT|ALL 整公司哨兵.
    返回集合(命中整公司时含 ALL_UNIT_SENTINEL). 任何无法解析的形状 -> 忽略(不泄漏 key).
    """
    out = set()
    if isinstance(os_, list):
        structured = [x for x in os_ if isinstance(x, dict)]
        plain = [x for x in os_ if isinstance(x, str)]
        for item in structured:
            did = item.get('deptId') or item.get('departmentId') or item.get('department_id')
            inc = bool(item.get('includeChildren', item.get('include_children', False)))
            if did is None:
                continue
            if inc:
                out.update(_subtree_ids_from_dept(str(did)))
            else:
                out.add(str(did))
        if plain:
            # 向后兼容: 纯字符串列表 = 仅本级. 旧 resolver 对 org_scope 纯列表不做子树展开,
            # unit.include_children 仅作用于 ManagementUnitMember.DEPT, 不作用于 org_scope 纯列表.
            for d in plain:
                out.add(str(d))
    elif isinstance(os_, dict):
        sub = None
        for k in _DEPT_LIST_KEYS:
            if k in os_ and isinstance(os_[k], list):
                sub = os_[k]
                break
        if sub is not None:
            out.update(str(d) for d in sub)
        elif (str(os_.get('level', '')).upper() in ('ROOT', 'ALL')
              or str(os_.get('type', '')).upper() == 'ALL'):
            out.add(ALL_UNIT_SENTINEL)
        # 其它 dict 形状: 无法解析, 跳过 (不泄漏 key)
    # 其它类型: 跳过
    return out


def unit_ids_to_dept_ids(unit_ids) -> list:
    """方案 A M4(2026-09-15): 把 management_unit_ids 解析成部门 id 集合.

    org_scope 解析统一交由 `_expand_org_scope`(支持节点级 includeChildren 结构化写法
    与历史纯字符串列表 / dict 兼容). 详见 `_expand_org_scope`.

    - 空输入返回 [];
    - ManagementUnit 查询异常 (V2 schema 未应用) 时 fail-safe 返回 [], 不静默放行;
    - 返回字符串化 dept id (与 department_id CharField 一致), 整公司单元返回 [ALL_UNIT_SENTINEL].
    """
    if not unit_ids:
        return []
    try:
        from .models_permission_v2 import ManagementUnit
        dept_ids = set()
        has_all = False
        for u in ManagementUnit.objects.filter(id__in=list(unit_ids), status=1):
            expanded = _expand_org_scope(u.org_scope, u.include_children)
            if ALL_UNIT_SENTINEL in expanded:
                has_all = True
            dept_ids.update(d for d in expanded if d != ALL_UNIT_SENTINEL)
        # 新增(2026-09-16): 管理单元成员 DEPT 类型真实生效到部门集合 (加法, 不破坏 org_scope 解析)
        try:
            dept_ids.update(collect_unit_member_depts(list(unit_ids)))
        except (OperationalError, ProgrammingError):
            logger.warning('[unit_ids_to_dept_ids] 成员 DEPT 解析失败, 跳过该部分')
        if has_all:
            return [ALL_UNIT_SENTINEL]
        return [str(d) for d in dept_ids]
    except (OperationalError, ProgrammingError) as e:
        logger.warning('[unit_ids_to_dept_ids] ManagementUnit 查询失败, fail-safe 返回空: %s', e)
        return []


def _subtree_ids_from_dept(dept_id):
    """返回某部门自身 + 其所有子孙部门 id (按 Department.path 前缀匹配)."""
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


def collect_unit_member_depts(unit_ids):
    """汇总若干管理单元下 DEPT 类型成员的部门 id (含子级按 include_children)."""
    from .models_permission_v2 import ManagementUnitMember
    out = set()
    for m in ManagementUnitMember.objects.filter(unit_id__in=list(unit_ids), member_type='DEPT', status=1):
        if m.include_children:
            out.update(_subtree_ids_from_dept(m.department_id))
        elif m.department_id:
            out.add(m.department_id)
    return [str(d) for d in out if d]


def collect_unit_member_users(unit_ids):
    """汇总若干管理单元下 USER / PERSON 类型成员的用户 id (供执行面 created_by__in).

    - USER 成员: 直接取其 user_id;
    - PERSON 成员: 经 campus_control.Person.user_id 映射成登录用户 id
      (2026-09-16 补全 PERSON 执行面: 把校招人员主数据关联到其登录用户,
       使该用户创建的候选人数据对其管理单元可见, 支持交叉管理).
    """
    from .models_permission_v2 import ManagementUnitMember
    out = set()
    members = list(
        ManagementUnitMember.objects.filter(unit_id__in=list(unit_ids), status=1)
    )
    user_ids = [m.user_id for m in members if m.member_type == 'USER' and m.user_id]
    out.update(user_ids)
    person_ids = [m.person_id for m in members if m.member_type == 'PERSON' and m.person_id]
    if person_ids:
        try:
            from apps.campus_control.models import Person
            for uid in Person.objects.filter(
                pk__in=person_ids, user_id__isnull=False
            ).values_list('user_id', flat=True):
                if uid is not None:
                    out.add(uid)
        except (OperationalError, ProgrammingError, ImportError):
            # campus_control 表缺失 / app 未装载 -> 跳过 PERSON 部分, 不阻断 USER 解析
            logger.warning('[collect_unit_member_users] PERSON->user_id 解析失败, 跳过该部分')
    return list(out)


def _combine_qs(qs, op):
    """合并 Q 列表: op='or'|'and'; 空列表返回 Q() (no-op)."""
    from django.db.models import Q
    if not qs:
        return Q()
    q = qs[0]
    for nxt in qs[1:]:
        q = (q | nxt) if op == 'or' else (q & nxt)
    return q


def _compile_one_data_range_condition(c, scope_field, creator_field):
    """编译单条数据范围条件 -> Q 或 None(不支持维度 no-op).

    首版支持 dimension in {dept, department, 部门}: 按部门(含子级由子树展开)等于/不等于过滤.
    其它维度 fail-safe 返回 None(记录 warning, 不放行也不报错), 避免越权放行.
    """
    from django.db.models import Q
    dimension = str(c.get('dimension') or c.get('dimensionCode') or '').lower()
    operator = str(c.get('operator') or c.get('op') or 'eq').lower()
    value = c.get('value')
    include_sub = bool(c.get('includeSub', c.get('includeSub', False)))
    if dimension in ('dept', 'department', '部门', '部门id'):
        if value is None or value == '':
            return None
        target = f'{scope_field}__in' if scope_field else f'{creator_field}__department_id__in'
        vids = [str(value)]
        if include_sub:
            sub = _subtree_ids_from_dept(str(value))
            if sub:
                vids = sub
        if operator in ('neq', '!=', 'not_eq'):
            return ~Q(**{target: vids})
        return Q(**{target: vids})
    logger.warning('[compile_data_range_q] 未支持维度 "%s", 该条件 no-op(fail-safe)', dimension)
    return None


def compile_data_range_q(data_range, scope_field='department_id', creator_field='created_by'):
    """北森「数据范围」条件表达式 -> Q.

    data_range 结构(首版):
      { op: 'or'|'and',                              # 组间关系(默认 or)
        groups: [ { op:'or'|'and',                  # 组内条件关系(默认 or)
                    conditions: [ { dimension, field, operator, value, includeSub } ] } ] }
    例: 两组 OR -> "1 or 2":
        { op:'or', groups:[ {conditions:[c1]}, {conditions:[c2]} ] }

    语义: 组内条件先按组 op 合并, 各组结果再按顶层 op 合并.
    首版仅 department 维度真实生效; 其它维度 no-op(记录 warning, 不放行也不报错).
    空/非法 -> Q() (no-op).
    """
    from django.db.models import Q
    if not isinstance(data_range, dict):
        return Q()
    groups = data_range.get('groups') or []
    if not groups:
        return Q()
    group_op = str(data_range.get('op') or 'or').lower()
    group_qs = []
    for g in groups:
        conds = (g or {}).get('conditions') or []
        cond_qs = [
            q for q in (
                _compile_one_data_range_condition(c, scope_field, creator_field)
                for c in conds if isinstance(c, dict)
            ) if q is not None
        ]
        if not cond_qs:
            continue
        gop = str((g or {}).get('op') or 'or').lower()
        group_qs.append(_combine_qs(cond_qs, gop))
    if not group_qs:
        return Q()
    return _combine_qs(group_qs, group_op)


def _pick_app_json(per_app, public, app_code):
    """按应用 JSON dict 优先取 app_code 切片, 否则回退 public 切片.

    用于 data_ranges / person_data_ranges 等 {app_code: DataRange} 结构:
    指定 app_code 且有值时优先其专属范围, 否则用 public 默认范围
    (与 org_scopes/org_scope 的回退语义一致). 两者皆空返回 None(no-op).
    """
    if app_code and isinstance(per_app, dict) and per_app.get(app_code):
        return per_app[app_code]
    return public if public else None


def iter_unit_scopes(unit_ids, app_code=None):
    """逐个管理单元产出行级可见贡献, 供 scope_filter_q 以 OR 聚合, 且数据范围作为单元内 AND 限制.

    产出 tuple: (dept_ids:list[str], user_ids:list[int], org_dr_q:Q, person_dr_q:Q, has_all:bool)
      - 组织范围(org_scope): _expand_org_scope(节点级 includeChildren / 历史兼容)
      - 成员 DEPT: collect_unit_member_depts(含子级)
      - 成员 USER/PERSON: collect_unit_member_users
      - 组织数据范围(data_range/data_ranges[app]): compile_data_range_q(scope_field=department_id) —— 单元内 AND 限制
      - 人员数据范围(person_data_range/person_data_ranges[app]): compile_data_range_q(scope_field=created_by__department_id) —— 单元内 AND 限制
    app_code 命中时优先用 per-app 切片, 否则回退 public(消除前序 per-app 未接入执行的假绿).
    """
    from django.db.models import Q

    from .models_permission_v2 import ManagementUnit
    for u in ManagementUnit.objects.filter(id__in=list(unit_ids), status=1):
        dept_ids = set(_expand_org_scope(u.org_scope, u.include_children))
        # 成员 DEPT 子级(加法, 不破坏 org_scope 解析)
        try:
            dept_ids.update(collect_unit_member_depts([u.id]))
        except (OperationalError, ProgrammingError):
            logger.warning('[iter_unit_scopes] 成员 DEPT 解析失败, 跳过')
        # 成员 USER/PERSON
        user_ids = collect_unit_member_users([u.id])
        # 组织数据范围(北森「数据范围」) —— 按应用优先, 回退 public, 单元内 AND 限制
        org_dr = _pick_app_json(getattr(u, 'data_ranges', None), getattr(u, 'data_range', None), app_code)
        org_dr_q = compile_data_range_q(org_dr, scope_field='department_id', creator_field='created_by') if org_dr else Q()
        # 人员数据范围(北森「人员数据范围」) —— 按应用优先, 回退 public, 单元内 AND 限制
        person_dr = _pick_app_json(getattr(u, 'person_data_ranges', None), getattr(u, 'person_data_range', None), app_code)
        person_dr_q = compile_data_range_q(person_dr, scope_field='created_by__department_id', creator_field='created_by') if person_dr else Q()
        has_all = ALL_UNIT_SENTINEL in dept_ids
        yield ([d for d in dept_ids if d != ALL_UNIT_SENTINEL], user_ids, org_dr_q, person_dr_q, has_all)


def recruit_type_filter_q(recruit_type):
    """硬系统分区 Q —— 招聘类型(social/campus)是系统级硬边界, 对所有用户(含超管)生效.

    opt-in: 仅当调用方显式传入 recruit_type 时返回按该维度过滤的 Q;
    未传(None/空) -> Q() (no-op, 兼容旧调用方与未分区模型).
    调用方须确保目标模型存在 recruit_type 字段.
    """
    from django.db.models import Q

    if not recruit_type:
        return Q()
    return Q(recruit_type=recruit_type)


def scope_filter_q(user, app_code=None, scope_field='', creator_field='created_by', recruit_type=None, entity=None):
    """返回当前用户行级可见范围的 Q 对象 —— scope_resolver 作为唯一真相源。

    行为等价于原「DataPermissionRule ROW 镜像 + enforcement.row_filter_q CUSTOM 分支」：
    直接由 resolve_scope 产出过滤条件, 不再读写 DataPermissionRule 行级规则。

    recruit_type (opt-in): 显式传入时, 该维度作为硬分区对所有用户(含超管/匿名)生效,
    先于行级 scope 以 AND 叠加 —— 社会/校园招聘数据相互隔离。

    entity (opt-in): 传入业务模块 key（candidate/demand/position/process/talent）时,
    若该用户所属角色配置了「角色自定义范围」规则, 以编译后的表达式 Q 替换默认
    scope（多角色按 RBAC 并集）；无配置则回退下方默认 scope（向后兼容）。

    - 未登录 / 超管 -> 至多仅 recruit_type 分区 (全量行级可见)
    - {'all': True} -> 至多仅 recruit_type 分区
    - department_ids -> 按 scope_field(部门 FK 路径) 或 creator.department_id 过滤
    - management_unit_ids ->
        * 空 list -> SELF (created_by=user.pk)
        * 含整公司 sentinel -> 至多仅 recruit_type 分区 (全量)
        * 否则 -> Q(scope_field__in=dept_ids) | Q(created_by__in=user_ids)
    """
    from django.db.models import Q

    from .role_v2_query import is_super_admin

    # 硬系统分区: 先于行级 scope 计算, 对所有用户(含超管/匿名)生效.
    rt_q = recruit_type_filter_q(recruit_type)

    if not (user and getattr(user, 'is_authenticated', False)):
        return rt_q
    if is_super_admin(user):
        return rt_q

    # 角色自定义范围（数据权限向导）优先于默认 scope：有配置则替换，无配置回退。
    if entity:
        from apps.data_permission.enforcement import role_entity_scope_q
        custom_q = role_entity_scope_q(user, entity)
        if custom_q is not None:
            return custom_q & rt_q

    scope = resolve_scope(user, app_code=app_code)

    if scope.get('all'):
        return rt_q

    if 'department_ids' in scope:
        dept_ids = scope.get('department_ids') or []
        if dept_ids:
            target = f'{scope_field}__in' if scope_field else f'{creator_field}__department_id__in'
            return Q(**{target: dept_ids}) & rt_q
        # 空部门集合 -> 仅看自己创建
        return Q(**{creator_field: user.pk}) & rt_q

    if 'management_unit_ids' in scope:
        unit_ids = scope.get('management_unit_ids') or []
        if not unit_ids:
            # 空管理单元集合 -> SELF 兜底
            return Q(**{creator_field: user.pk}) & rt_q
        q = Q()
        for dept_ids, user_ids, org_dr_q, person_dr_q, has_all in iter_unit_scopes(unit_ids, app_code):
            if has_all:
                # 整公司单元 -> 全量可见(OR 中任意一项为全量即整体全量)
                return rt_q
            unit_q = Q()
            if dept_ids:
                target = f'{scope_field}__in' if scope_field else f'{creator_field}__department_id__in'
                unit_q |= Q(**{target: dept_ids})
            if user_ids:
                unit_q |= Q(**{f'{creator_field}__in': user_ids})
            if not unit_q.children:
                unit_q |= Q(**{creator_field: user.pk})
            # 北森「组织数据范围」: 作为单元内额外限制(AND); 无有效条件则为 no-op
            if org_dr_q.children:
                unit_q &= org_dr_q
            # 北森「人员数据范围」: 作为单元内额外限制(AND); 与组织数据范围独立, 两者皆生效
            if person_dr_q.children:
                unit_q &= person_dr_q
            q |= unit_q
        return (q if q.children else Q(**{creator_field: user.pk})) & rt_q

    # 兜底 (正常不会到达): 无范围信息 -> SELF
    return Q(**{creator_field: user.pk}) & rt_q