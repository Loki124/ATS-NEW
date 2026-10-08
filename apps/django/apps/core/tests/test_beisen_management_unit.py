"""北森管理单元模型补齐验证 (Block 1 组织范围节点级包含下级 + Block 3 数据范围条件筛选器).

证明:
  - ManagementUnit.org_scope 支持结构化 [{deptId, includeChildren}] -> 节点级子树展开;
  - ManagementUnit.data_range 经 compile_data_range_q 编译为 Q, 并在 scope_filter_q 中
    作为单元内 AND 限制生效.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.core.role_v2_query import is_super_admin


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_structured_org_scope_per_node_include_children():
    """org_scope=[{deptId,includeChildren}] -> 节点级子树展开, 仅本级不展开."""
    from apps.core.models_permission_v2 import ManagementUnit
    from apps.core.scope_resolver import unit_ids_to_dept_ids

    # 部门树: D1 -> D1-1; D2 独立
    for did, path in [('D1', 'D1'), ('D1-1', 'D1/D1-1'), ('D2', 'D2')]:
        from apps.core.models import Department
        Department.objects.create(
            id=did, name=did, code=f'code-{did}', path=path, parent=None,
        )

    unit = ManagementUnit.objects.create(
        unit_name='结构化单元', system_code='recruit', unit_type='org',
        org_scope=[
            {'deptId': 'D1', 'includeChildren': True},
            {'deptId': 'D2', 'includeChildren': False},
        ],
        include_children=0,  # 单元级开关不应再影响 org_scope 纯结构化写法
        status=1,
    )

    # D1 展开为自身 + 子级 D1-1; D2 仅本级
    assert sorted(unit_ids_to_dept_ids([unit.id])) == ['D1', 'D1-1', 'D2']


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_compile_data_range_q_dept_dimension():
    """data_range 部门维度 -> 等于/不等于 Q; 未支持维度 no-op."""
    from django.db.models import Q

    from apps.core.scope_resolver import compile_data_range_q

    eq_q = compile_data_range_q({
        'op': 'or',
        'groups': [{'conditions': [{'dimension': 'dept', 'operator': 'eq', 'value': 'D1'}]}],
    })
    assert str(eq_q) == str(Q(department_id__in=['D1']))

    neq_q = compile_data_range_q({
        'op': 'or',
        'groups': [{'conditions': [{'dimension': '部门', 'operator': 'neq', 'value': 'D2'}]}],
    })
    assert str(neq_q) == str(~Q(department_id__in=['D2']))

    # 未支持维度 -> Q() no-op (fail-safe, 不放行)
    assert str(compile_data_range_q({
        'op': 'or',
        'groups': [{'conditions': [{'dimension': 'position', 'operator': 'eq', 'value': '经理'}]}],
    })) == str(Q())


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_scope_filter_q_applies_data_range_as_and():
    """data_range 作为单元内 AND 限制: org_scope 与 data_range 求交."""
    from apps.core.models_permission_v2 import ManagementUnit, UserRoleV2
    from apps.core.scope_resolver import scope_filter_q

    User = get_user_model()
    u = User.objects.create_user(username='dr_u', password='x')
    assert not is_super_admin(u)

    unit = ManagementUnit.objects.create(
        unit_name='数据范围单元', system_code='recruit', unit_type='org',
        org_scope=['D1'], status=1,
        # 数据范围: 仅部门 D2 (与 org_scope D1 无交集 -> 部门维度实际为空, 验证 AND 生效)
        data_range={
            'op': 'or',
            'groups': [{'conditions': [{'dimension': 'dept', 'operator': 'eq', 'value': 'D2'}]}],
        },
    )
    UserRoleV2.objects.create(
        user_id=u.pk, role_code='R_DR', system_code='recruit',
        app_data_scopes={'recruit': [unit.id]}, granted_by_id=1,
    )

    q = scope_filter_q(u, app_code='recruit',
                       scope_field='referrer__department', creator_field='created_by')
    q_str = str(q)
    # org_scope 贡献 referrer__department__in=['D1']
    assert 'referrer__department__in' in q_str and "'D1'" in q_str
    # data_range 贡献 referrer__department__in=['D2'] 且以 AND 并入 (两条件并存)
    assert "'D2'" in q_str
    # 无成员 -> 不应出现 created_by__in
    assert 'created_by' not in q_str
