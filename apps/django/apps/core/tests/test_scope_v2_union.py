"""卡 1.1「管理单元并集」: 角色自定义范围与默认 scope 由**替换语义**改为**并集(附加授权)**。

背景（口径变更 2026-10-16）
--------------------------
`scope_filter_q(entity=...)` 原实现里，角色自定义范围一旦命中就 `return custom_q & rt_q`，
直接跳过下方全部管理单元/部门/SELF 逻辑 —— 即「替换」。工单卡 1.1 要求改为并集：

    最终行过滤 = custom_q | q_default      （q_default = 管理单元 / 部门 / SELF 兜底）

「只有一方存在时行为完全不变」是硬约束，因此本文件用 4 组用例把它钉死：

  1. test_union_of_unit_and_custom_is_additive
       并集生效：管理单元 A 与角色规则 B 数据集**互不相交** -> 可见 = A ∪ B（行数等于两者之和，
       而不是任一方）。这是本次变更唯一真正放宽权限的用例。
  2. test_single_sided_unchanged / test_custom_only_unchanged
       单方存在行为不变：只有管理单元无角色规则、只有角色规则无管理单元，结果均与变更前一致。
  3. test_default_scope_all_not_downgraded_by_custom
       **防假绿最重要的一条**：默认 scope 为全量 + 角色规则为窄范围 -> 结果仍是全量。
       Django 中 `Q() | Q(a=1)` == `Q(a=1)`（空 Q 被 OR 吸收），若把「全量」当空 Q 丢进并集，
       全量可见会被静默降级成「仅角色规则范围」= 严重的权限**收窄**事故。
  4. test_all_company_sentinel_not_downgraded
       整公司哨兵（ALL_UNIT_SENTINEL）同样必须短路返回全量，不被角色规则降级。

安全方向：该变更**放宽**可见范围（挂管理单元且有角色规则的用户可见集变大），
只会把既有授权相加，不会让任一侧的范围被吞掉，也不会收紧任何一侧。
回滚方式：revert 引入并集逻辑的 commit（口径与本文件测试同 commit 回退，无需数据迁移）。

已知遗留（本次刻意不改）：`apps/core/scope_preview.py:103` 的 `desc['custom_replaced']`
语义仍是「是否**替换**了默认 scope」，改并集后该字段已失真（详见 scope_resolver.scope_filter_q
docstring 的「遗留」段）。
"""
import pytest
from django.contrib.auth import get_user_model

from apps.core.models import Department
from apps.core.models_permission_v2 import ManagementUnit, RoleV2, UserRoleV2
from apps.core.scope_resolver import (
    ALL_UNIT_SENTINEL,
    resolve_scope,
    scope_filter_q,
)
from apps.data_permission.models import DataPermissionRule

# candidate 模块的 CUSTOM「dept」维度编译为 referrer__department_id（field_map.MODULE_DIMENSION_FIELDS）
CUSTOM_SCOPE_FIELD = 'referrer__department'
CUSTOM_CREATOR_FIELD = 'created_by'


def _mk_departments():
    """建立 3 个互不相干的部门 —— D1(角色规则域) / D2(管理单元域) / D3(两边都不属于)。"""
    for did in ('D1', 'D2', 'D3'):
        Department.objects.create(
            id=did, name=did, code=f'u-{did}', path=did, parent=None,
        )


def _mk_user(username, dept_id='D1'):
    return get_user_model().objects.create_user(
        username=username, password='x', department_id=dept_id,
    )


def _grant_unit(user, role_code, unit):
    """给用户挂管理单元（走 per-app 范围, 与生产入口一致: app_code='recruit'）。"""
    UserRoleV2.objects.create(
        user_id=user.pk, role_code=role_code, system_code='recruit',
        app_data_scopes={'recruit': [unit.id]}, granted_by_id=1,
    )


def _mk_unit(name, org_scope):
    return ManagementUnit.objects.create(
        unit_name=name, system_code='recruit', unit_type='org',
        org_scope=org_scope, status=1,
    )


def _custom_rule_dept(role_code, dept_id, entity='candidate'):
    """角色 CUSTOM 规则：候选人「推荐人所属部门」== dept_id。

    该维度编译为 referrer__department_id，与管理单元贡献的
    `scope_field='referrer__department__in'` 同字段，因此两侧行集可直接做行数对比。
    """
    DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value=role_code, level='ROW',
        entity=entity, scope_type='CUSTOM',
        scope_payload={
            'expr': '1',
            'groups': [{
                'expr': '1',
                'conditions': [{'dimension': 'dept', 'operator': 'in',
                                'values': [{'id': dept_id, 'label': dept_id}]}],
            }],
        },
        status=1,
    )


def _mk_candidate(name, referrer):
    from apps.candidate.models import Candidate
    return Candidate.objects.create(name=name, referrer=referrer, created_by=referrer)


# ---------------------------------------------------------------------------
# 1. 并集生效: A ∪ B, 互不相交 -> 行数等于两者之和
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_union_of_unit_and_custom_is_additive():
    """管理单元 D2 与角色规则 D1 数据集互不相交 -> 可见 = D1 ∪ D2（不是任一方）。"""
    from apps.candidate.models import Candidate

    _mk_departments()
    u = _mk_user('union_u', dept_id='D1')
    referrer_d1 = _mk_user('union_r_d1', dept_id='D1')
    referrer_d2 = _mk_user('union_r_d2', dept_id='D2')
    referrer_d3 = _mk_user('union_r_d3', dept_id='D3')

    # 管理单元 -> D2；角色自定义规则 -> D1。两者互不相交。
    _grant_unit(u, 'R_UNION', _mk_unit('并集单元', ['D2']))
    _custom_rule_dept('R_UNION', 'D1')

    _mk_candidate('角色规则可见', referrer_d1)
    _mk_candidate('管理单元可见', referrer_d2)
    _mk_candidate('两边都不可见', referrer_d3)

    assert resolve_scope(u, app_code='recruit').get('management_unit_ids'), \
        '前置条件: 用户必须确实挂在管理单元上'

    q = scope_filter_q(
        u, app_code='recruit', scope_field=CUSTOM_SCOPE_FIELD,
        creator_field=CUSTOM_CREATOR_FIELD, entity='candidate',
    )
    names = set(Candidate.objects.filter(q).values_list('name', flat=True))

    # 并集: 两侧都可见 —— 替换语义下这里只会剩下「角色规则可见」一条
    assert names == {'角色规则可见', '管理单元可见'}, names
    assert Candidate.objects.filter(q).count() == 2, '并集行数 = A ∪ B 之和'
    # 明确排除任一方单独生效的可能（即防「假装并集」）
    assert names != {'角色规则可见'} and names != {'管理单元可见'}


# ---------------------------------------------------------------------------
# 2. 单方存在: 行为与变更前完全一致
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_single_sided_unit_only_unchanged():
    """只有管理单元、无角色规则 -> 结果等于原管理单元结果（不含角色侧范围）。"""
    from apps.candidate.models import Candidate

    _mk_departments()
    u = _mk_user('unit_only_u', dept_id='D1')
    r_d1 = _mk_user('unit_only_r_d1', dept_id='D1')
    r_d2 = _mk_user('unit_only_r_d2', dept_id='D2')

    _grant_unit(u, 'R_UNIT_ONLY', _mk_unit('仅单元', ['D2']))
    _mk_candidate('管理单元可见', r_d2)
    _mk_candidate('角色侧不可见', r_d1)

    q = scope_filter_q(
        u, app_code='recruit', scope_field=CUSTOM_SCOPE_FIELD,
        creator_field=CUSTOM_CREATOR_FIELD, entity='candidate',
    )
    names = set(Candidate.objects.filter(q).values_list('name', flat=True))
    assert names == {'管理单元可见'}, names


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_single_sided_custom_only_unchanged():
    """只有角色规则、无管理单元 -> 结果等于原角色规则结果（且仍含 SELF 兜底那一侧）。"""
    from apps.candidate.models import Candidate

    _mk_departments()
    u = _mk_user('custom_only_u', dept_id='D1')
    r_d1 = _mk_user('custom_only_r_d1', dept_id='D1')
    r_d2 = _mk_user('custom_only_r_d2', dept_id='D2')

    # 无管理单元授权 -> 默认 scope 退化 SELF
    UserRoleV2.objects.create(
        user_id=u.pk, role_code='R_CUSTOM_ONLY', system_code='recruit', granted_by_id=1,
    )
    _custom_rule_dept('R_CUSTOM_ONLY', 'D1')

    _mk_candidate('角色规则可见', r_d1)
    _mk_candidate('角色侧不可见', r_d2)

    q = scope_filter_q(
        u, app_code='recruit', scope_field=CUSTOM_SCOPE_FIELD,
        creator_field=CUSTOM_CREATOR_FIELD, entity='candidate',
    )
    names = set(Candidate.objects.filter(q).values_list('name', flat=True))
    # 按工单口径 SELF 兜底属于「一方的贡献」, 参与并集 -> 角色范围 ∪ 自己创建的
    assert '角色规则可见' in names, names
    assert '角色侧不可见' not in names, names


# ---------------------------------------------------------------------------
# 3. 全量不被降级（本次改动最重要的防假绿用例）
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_default_scope_all_not_downgraded_by_custom():
    """默认 scope 为全量 + 角色规则为窄范围 -> 结果仍是**全量**，不被收窄成角色规则。"""
    from apps.candidate.models import Candidate

    _mk_departments()
    u = _mk_user('all_scope_u', dept_id='D1')
    other = _mk_user('all_scope_other', dept_id='D3')

    # 默认 scope 全量: 角色 default_data_scope_type='ALL'（L2）
    RoleV2.objects.create(
        system_code='recruit', role_code='R_ALL_SCOPE', role_name='全量角色',
        status=1, default_data_scope_type='ALL',
    )
    UserRoleV2.objects.create(
        user_id=u.pk, role_code='R_ALL_SCOPE', system_code='recruit', granted_by_id=1,
    )
    # 角色自定义规则为窄范围（D1）
    _custom_rule_dept('R_ALL_SCOPE', 'D1')

    # D3 的候选人：不在角色规则范围内, 只有「全量默认 scope」才可见
    _mk_candidate('角色规则外', other)

    assert resolve_scope(u, app_code='recruit').get('all') is True, '前置条件: 默认 scope 确为全量'

    q = scope_filter_q(
        u, app_code='recruit', scope_field=CUSTOM_SCOPE_FIELD,
        creator_field=CUSTOM_CREATOR_FIELD, entity='candidate',
    )
    names = set(Candidate.objects.filter(q).values_list('name', flat=True))
    assert names == {'角色规则外'}, '默认 scope 全量时不得被角色规则收窄（权限收窄事故）'
    assert not q.children, '全量 -> 空 Q（不参与并集运算）'


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_custom_all_not_downgraded_by_unit():
    """反向对称: 角色规则为 ALL（返回空 Q）+ 有管理单元 -> 仍是全量, 不被单元收窄。"""
    from apps.candidate.models import Candidate

    _mk_departments()
    u = _mk_user('custom_all_u', dept_id='D1')
    other = _mk_user('custom_all_other', dept_id='D3')

    UserRoleV2.objects.create(
        user_id=u.pk, role_code='R_CUSTOM_ALL', system_code='recruit',
        app_data_scopes={'recruit': [_mk_unit('ALL规则单元', ['D2']).id]}, granted_by_id=1,
    )
    DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value='R_CUSTOM_ALL', level='ROW',
        entity='candidate', scope_type='ALL', status=1,
    )

    _mk_candidate('单元外', other)

    q = scope_filter_q(
        u, app_code='recruit', scope_field=CUSTOM_SCOPE_FIELD,
        creator_field=CUSTOM_CREATOR_FIELD, entity='candidate',
    )
    assert not q.children, '角色规则 ALL -> 空 Q -> 全量（不可被管理单元收窄）'
    assert set(Candidate.objects.filter(q).values_list('name', flat=True)) == {'单元外'}


# ---------------------------------------------------------------------------
# 4. 整公司哨兵不被降级
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_all_company_sentinel_not_downgraded():
    """管理单元含 ALL_UNIT_SENTINEL + 角色规则为窄范围 -> 仍返回全量, 不被降级。"""
    from apps.candidate.models import Candidate

    _mk_departments()
    u = _mk_user('sentinel_u', dept_id='D1')
    other = _mk_user('sentinel_other', dept_id='D3')

    _grant_unit(u, 'R_SENTINEL', _mk_unit('整公司单元', {'name': '全公司', 'level': 'ROOT'}))
    _custom_rule_dept('R_SENTINEL', 'D1')

    _mk_candidate('单元外', other)

    q = scope_filter_q(
        u, app_code='recruit', scope_field=CUSTOM_SCOPE_FIELD,
        creator_field=CUSTOM_CREATOR_FIELD, entity='candidate',
    )
    assert not q.children, '整公司哨兵 -> 全量短路（不可被角色规则吸收降级）'
    assert set(Candidate.objects.filter(q).values_list('name', flat=True)) == {'单元外'}
    assert resolve_scope(u, app_code='recruit').get('management_unit_ids'), '前置条件'
