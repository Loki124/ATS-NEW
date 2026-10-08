"""Tier 3: scope_resolver 现为行级数据范围唯一真相源.

证明链路:
  UserRoleV2.app_data_scopes[recruit] = [management_unit_ids]
    -> resolve_scope(user, app_code='recruit') 返回 management_unit_ids
    -> scope_filter_q 用 unit_ids_to_dept_ids + collect_unit_member_users
       直接产出过滤 Q (等价于原 DataPermissionRule ROW 镜像).

不再有 DataPermissionRule ROW 镜像 / row_filter_q.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.core.role_v2_query import is_super_admin


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_management_unit_scope_produces_dept_q():
    """管理单元(org_scope 直接部门列表) -> scope_filter_q 产出 referrer__department__in Q."""
    from apps.core.models_permission_v2 import ManagementUnit, UserRoleV2
    from apps.core.scope_resolver import (
        resolve_scope,
        scope_filter_q,
        unit_ids_to_dept_ids,
    )

    User = get_user_model()
    u = User.objects.create_user(username='enf_u', password='x')
    assert not is_super_admin(u)

    unit = ManagementUnit.objects.create(
        unit_name='ENF-单元', system_code='recruit', unit_type='org',
        org_scope=['D1', 'D2'], status=1,
    )
    UserRoleV2.objects.create(
        user_id=u.pk, role_code='R_E', system_code='recruit',
        app_data_scopes={'recruit': [unit.id]}, granted_by_id=1,
    )

    # 1) resolve_scope 按应用优先返回该单元
    scope = resolve_scope(u, app_code='recruit')
    assert scope.get('management_unit_ids') == [unit.id], scope

    # 2) helper: org_scope -> dept ids
    assert sorted(unit_ids_to_dept_ids([unit.id])) == ['D1', 'D2']

    # 3) scope_filter_q 直接产出参考人部门过滤 Q (等价于原镜像 CUSTOM 规则)
    q = scope_filter_q(
        u, app_code='recruit',
        scope_field='referrer__department', creator_field='created_by',
    )
    q_str = str(q)
    assert 'referrer__department__in' in q_str
    assert "'D1'" in q_str and "'D2'" in q_str
    # 无成员用户 -> 不应出现 created_by__in
    assert 'created_by' not in q_str


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_no_management_unit_scope_falls_to_self():
    """无管理单元范围 -> SELF (created_by=user.pk), 非全量也非部门过滤."""
    from django.contrib.auth import get_user_model

    from apps.core.scope_resolver import scope_filter_q

    User = get_user_model()
    u = User.objects.create_user(username='enf_self', password='x')
    assert not is_super_admin(u)

    q = scope_filter_q(
        u, app_code='recruit',
        scope_field='referrer__department', creator_field='created_by',
    )
    q_str = str(q)
    assert 'created_by' in q_str
    assert str(u.pk) in q_str
    # 不应出现部门 IN 过滤
    assert 'referrer__department__in' not in q_str


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_unit_all_company_resolves_to_all_q():
    """整公司级单元 (org_scope={'level':'ROOT'}) -> 空 Q() (全量可见)."""
    from apps.core.models_permission_v2 import ManagementUnit, UserRoleV2
    from apps.core.scope_resolver import (
        ALL_UNIT_SENTINEL,
        scope_filter_q,
        unit_ids_to_dept_ids,
    )

    User = get_user_model()
    u = User.objects.create_user(username='enf_all', password='x')
    assert not is_super_admin(u)

    unit = ManagementUnit.objects.create(
        unit_name='全公司测试', system_code='recruit', unit_type='org',
        org_scope={'name': '全公司测试', 'level': 'ROOT'}, status=1,
    )
    UserRoleV2.objects.create(
        user_id=u.pk, role_code='R_ALL', system_code='recruit',
        app_data_scopes={'recruit': [unit.id]}, granted_by_id=1,
    )

    assert unit_ids_to_dept_ids([unit.id]) == [ALL_UNIT_SENTINEL]
    # ALL sentinel -> 空 Q() 全量可见
    q = scope_filter_q(
        u, app_code='recruit',
        scope_field='referrer__department', creator_field='created_by',
    )
    assert len(q.children) == 0


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_unit_dict_unknown_shape_self_fallback():
    """dict 但无可解析 dept 子键且非整公司 -> 不泄漏 key; 用户无范围则 SELF 兜底."""
    from apps.core.models_permission_v2 import ManagementUnit, UserRoleV2
    from apps.core.scope_resolver import scope_filter_q, unit_ids_to_dept_ids

    User = get_user_model()
    u = User.objects.create_user(username='enf_weird', password='x')
    assert not is_super_admin(u)

    unit = ManagementUnit.objects.create(
        unit_name='怪异单元', system_code='recruit', unit_type='org',
        org_scope={'foo': 'bar', 'baz': 1, 'level': 'TEAM'}, status=1,
    )
    UserRoleV2.objects.create(
        user_id=u.pk, role_code='R_W', system_code='recruit',
        app_data_scopes={'recruit': [unit.id]}, granted_by_id=1,
    )

    # 不应把 foo/baz/level 当 dept id 泄漏
    assert unit_ids_to_dept_ids([unit.id]) == []
    # 解析不出部门 -> SELF 兜底
    q = scope_filter_q(
        u, app_code='recruit',
        scope_field='referrer__department', creator_field='created_by',
    )
    q_str = str(q)
    assert 'created_by' in q_str and str(u.pk) in q_str
    assert 'referrer__department__in' not in q_str


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_management_unit_member_user_produces_created_by_in():
    """管理单元含 USER 成员 -> scope_filter_q 叠加 created_by__in=user_ids."""
    from apps.core.models_permission_v2 import (
        ManagementUnit,
        ManagementUnitMember,
        UserRoleV2,
    )
    from apps.core.scope_resolver import collect_unit_member_users, scope_filter_q

    User = get_user_model()
    u = User.objects.create_user(username='enf_member', password='x')
    member = User.objects.create_user(username='enf_member_u', password='x')
    assert not is_super_admin(u)

    unit = ManagementUnit.objects.create(
        unit_name='成员单元', system_code='recruit', unit_type='org',
        org_scope=['D1'], status=1,
    )
    UserRoleV2.objects.create(
        user_id=u.pk, role_code='R_M', system_code='recruit',
        app_data_scopes={'recruit': [unit.id]}, granted_by_id=1,
    )
    ManagementUnitMember.objects.create(
        unit_id=unit.id, member_type='USER', user_id=member.pk, status=1,
    )

    user_ids = collect_unit_member_users([unit.id])
    assert member.pk in user_ids

    q = scope_filter_q(
        u, app_code='recruit',
        scope_field='referrer__department', creator_field='created_by',
    )
    q_str = str(q)
    # 部门 + 成员用户 并集
    assert 'referrer__department__in' in q_str
    assert 'created_by__in' in q_str
    assert str(member.pk) in q_str
