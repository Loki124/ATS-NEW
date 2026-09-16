"""M4 联调: 管理单元范围真正接入 data_permission 执行引擎 (防 fake-green).

证明链路:
  UserAppDataScope(management_unit_ids)
    -> _rebuild_user_rules 镜像成 DataPermissionRule(USER 维度, CUSTOM, department_ids)
    -> row_filter_q 真实产出 department_id__in 过滤 Q

不是"记录落库了就算过", 而是 enforcement 真的用 management_unit_ids 的 org_scope
解析结果去过滤数据行。
"""
import pytest
from django.contrib.auth import get_user_model

from apps.core.role_v2_query import is_super_admin


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_management_unit_scope_reaches_enforcement():
    from apps.core.models_permission_v2 import ManagementUnit, UserAppDataScope
    from apps.core.scope_resolver import resolve_scope, unit_ids_to_dept_ids
    from apps.core.views_permission_v2 import _rebuild_user_rules
    from apps.data_permission.models import DimensionType
    from apps.data_permission.enforcement import row_filter_q

    User = get_user_model()
    u = User.objects.create_user(username='enforce_u', password='x')
    # 普通用户: 非超管, 不走 bypass
    assert not is_super_admin(u)

    unit = ManagementUnit.objects.create(
        unit_name='ENF-单元',
        system_code='recruit',
        unit_type='org',
        org_scope=['D1', 'D2'],
        status=1,
    )
    UserAppDataScope.objects.create(
        user_id=u.pk,
        role_code='R_E',
        app_code='campus',
        system_code='recruit',
        management_unit_ids=[unit.id],
        granted_by_id=1,
    )

    # 1) resolve_scope 按应用优先返回该单元
    scope = resolve_scope(u, app_code='campus')
    assert scope.get('management_unit_ids') == [unit.id], scope

    # 2) helper: org_scope -> dept ids
    assert sorted(unit_ids_to_dept_ids([unit.id])) == ['D1', 'D2']

    # 3) 重建规则: USER 维度 + department_ids 解析正确
    rule = _rebuild_user_rules(u.pk)
    assert rule is not None
    assert rule.dimension_type == DimensionType.USER
    assert rule.dimension_value == str(u.pk)
    assert sorted(rule.scope_payload['department_ids']) == ['D1', 'D2']
    assert rule.scope_payload['management_unit_ids'] == [unit.id]

    # 4) enforcement 真实产出 department 过滤 Q (既非 None 也非全量)
    q = row_filter_q(u, scope_field='department_id')
    assert q is not None
    q_str = str(q)
    assert 'department_id__in' in q_str
    assert "'D1'" in q_str and "'D2'" in q_str


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_rebuild_user_rules_clears_when_no_scope():
    """无范围时删除规则, 回退 OLD 引擎 (row_filter_q 返回 None)."""
    from apps.core.models_permission_v2 import UserAppDataScope
    from apps.core.views_permission_v2 import _rebuild_user_rules
    from apps.data_permission.enforcement import row_filter_q
    from django.contrib.auth import get_user_model

    User = get_user_model()
    u = User.objects.create_user(username='enforce_clear', password='x')
    assert not is_super_admin(u)

    # 没有任何 UserAppDataScope / UserRoleV2 -> 重建应删除规则并返回 None
    rule = _rebuild_user_rules(u.pk)
    assert rule is None

    from apps.data_permission.models import DataPermissionRule
    assert not DataPermissionRule.objects.filter(id=f'uads_user_{u.pk}').exists()

    # enforcement 无生效规则 -> 返回 None (调用方回退旧引擎)
    assert row_filter_q(u, scope_field='department_id') is None


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_unit_all_company_resolves_to_all_rule():
    """整公司级单元 (org_scope={'level':'ROOT'}) -> ALL 规则 (可见全量), 非泄漏 key."""
    from apps.core.models_permission_v2 import ManagementUnit, UserAppDataScope
    from apps.core.scope_resolver import unit_ids_to_dept_ids, ALL_UNIT_SENTINEL
    from apps.core.views_permission_v2 import _rebuild_user_rules
    from apps.data_permission.models import DimensionType, RowScopeType
    from apps.data_permission.enforcement import row_filter_q
    from django.contrib.auth import get_user_model

    User = get_user_model()
    u = User.objects.create_user(username='allco_u', password='x')
    assert not is_super_admin(u)

    unit = ManagementUnit.objects.create(
        unit_name='全公司测试', system_code='recruit', unit_type='org',
        org_scope={'name': '全公司测试', 'level': 'ROOT'}, status=1,
    )
    UserAppDataScope.objects.create(
        user_id=u.pk, role_code='R_ALL', app_code='campus',
        system_code='recruit', management_unit_ids=[unit.id], granted_by_id=1,
    )

    # helper: ROOT dict -> ALL sentinel (绝不泄漏 name/level 当 dept id)
    assert unit_ids_to_dept_ids([unit.id]) == [ALL_UNIT_SENTINEL]

    rule = _rebuild_user_rules(u.pk)
    assert rule is not None
    assert rule.dimension_type == DimensionType.USER
    assert rule.scope_type == RowScopeType.ALL
    assert rule.dimension_value == str(u.pk)

    # ALL 规则 -> row_filter_q 返回空 Q() (全量可见)
    q = row_filter_q(u, scope_field='department_id')
    assert q is not None
    assert len(q.children) == 0


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_unit_dict_unknown_shape_no_leak():
    """dict 但无可解析 dept 子键且非整公司 -> 不泄漏 key, 不建 NEW 引擎规则 (回退)."""
    from apps.core.models_permission_v2 import ManagementUnit, UserAppDataScope
    from apps.core.scope_resolver import unit_ids_to_dept_ids
    from apps.core.views_permission_v2 import _rebuild_user_rules
    from apps.data_permission.models import DataPermissionRule
    from django.contrib.auth import get_user_model

    User = get_user_model()
    u = User.objects.create_user(username='weird_u', password='x')
    assert not is_super_admin(u)

    unit = ManagementUnit.objects.create(
        unit_name='怪异单元', system_code='recruit', unit_type='org',
        org_scope={'foo': 'bar', 'baz': 1, 'level': 'TEAM'}, status=1,
    )
    UserAppDataScope.objects.create(
        user_id=u.pk, role_code='R_W', app_code='campus',
        system_code='recruit', management_unit_ids=[unit.id], granted_by_id=1,
    )

    # 不应把 foo/baz/level 当 dept id 泄漏
    assert unit_ids_to_dept_ids([unit.id]) == []
    # 不应创建 NEW 引擎规则 (回退 OLD 引擎 / SELF)
    assert _rebuild_user_rules(u.pk) is None
    assert not DataPermissionRule.objects.filter(id=f'uads_user_{u.pk}').exists()
