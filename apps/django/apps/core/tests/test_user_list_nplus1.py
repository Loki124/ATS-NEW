"""UserViewSet 列表 N+1 回归 (#9, 2026-10-09).

UserMinimalSerializer.to_representation 原本逐行查 UserRoleV2 (user_id 是整型字段,
无 FK 反向关系, 无法 prefetch_related)。修复: UserViewSet.get_serializer_context 按页
批量注入 role_map, 序列化器优先读 role_map。本测试隔离 `user_roles` 表查询, 验证:
- 带 role_map: 序列化阶段 0 条 user_roles 查询 (N+1 消除)
- 不带 (fallback): 每行 1 条 user_roles 查询 (复现原 bug, 作对照)
"""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.core.models_permission_v2 import UserRoleV2
from apps.core.serializers import UserMinimalSerializer
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _make_users(n: int):
    users = []
    for _ in range(n):
        u = UserFactory()
        UserRoleV2.objects.create(user_id=u.pk, role_code='HRBP', system_code='recruit')
        users.append(u)
    return users


def _role_queries(ctx):
    return [q for q in ctx.captured_queries if 'user_roles' in q['sql'].lower()]


def test_role_map_eliminates_per_row_query():
    users = _make_users(8)
    role_map = {u.pk: 'HRBP' for u in users}
    with CaptureQueriesContext(connection) as ctx:
        data = UserMinimalSerializer(users, many=True, context={'role_map': role_map}).data
    assert len(data) == 8
    # 角色查询应被 role_map 完全吸收, 序列化阶段 0 条 user_roles 查询
    assert _role_queries(ctx) == [], '带 role_map 时不应再逐行查 user_roles'


def test_fallback_still_queries_per_row():
    users = _make_users(6)
    with CaptureQueriesContext(connection) as ctx:
        UserMinimalSerializer(users, many=True).data
    # 无 role_map -> 退化路径, 每行 1 条 user_roles 查询 (对照, 证明修复前确有 N+1)
    assert len(_role_queries(ctx)) >= 5


def test_role_names_map_returns_all_identity_names():
    """用户管理「拥有身份」列 (2026-10-10): 一个用户挂多个角色时,
    roleNames 必须返回全部身份名称, 而不是像 roleType 那样只取一个。"""
    from apps.core.models_permission_v2 import RoleV2
    user = UserFactory()
    # ZZ 前缀避免与种子角色 role_code 撞唯一约束 uk_system_role
    pairs = [('ZZROLE_A', '身份甲'), ('ZZROLE_B', '身份乙')]
    for code, name in pairs:
        RoleV2.objects.update_or_create(
            system_code='recruit', role_code=code, defaults={'role_name': name},
        )
        UserRoleV2.objects.create(user_id=user.pk, role_code=code, system_code='recruit')
    data = UserMinimalSerializer([user], many=True, context={
        'role_map': {user.pk: 'ZZROLE_A'},
        'role_names_map': {user.pk: ['身份甲', '身份乙']},
    }).data
    assert data[0]['roleNames'] == ['身份甲', '身份乙']
    # roleType 保持原单值语义, 不受 roleNames 影响
    assert data[0]['roleType'] == 'ZZROLE_A'


def test_list_context_injects_role_names_map():
    """UserViewSet.get_serializer_context 必须按页批量注入 role_names_map。

    这一步漏掉 -> 序列化器拿不到 map -> 「拥有身份」列整列恒空, 且不报错,
    很难从代码阅读中发现, 故单独锁住。
    """
    from rest_framework.request import Request
    from rest_framework.test import APIRequestFactory

    from apps.core.models_permission_v2 import RoleV2
    from apps.core.views import UserViewSet

    user = UserFactory()
    RoleV2.objects.update_or_create(
        system_code='recruit', role_code='ZZVIEW_A', defaults={'role_name': '视图身份甲'},
    )
    UserRoleV2.objects.create(user_id=user.pk, role_code='ZZVIEW_A', system_code='recruit')

    request = Request(APIRequestFactory().get('/api/v1/users/'))
    request.user = user  # 无 HRBP 角色 -> get_queryset 收敛为仅自己
    view = UserViewSet()
    view.request = request
    view.kwargs = {}
    view.action = 'list'
    # 手工装配 view，绕过 dispatch()：DRF 的 format_kwarg 在此版本非可解析属性，
    # 直接补一个 None，让 GenericAPIView.get_serializer_context 能取到 format。
    view.format_kwarg = None
    ctx = view.get_serializer_context()
    assert ctx['role_names_map'].get(user.pk) == ['视图身份甲']
    # roleType 仍走原 role_map 单值语义
    assert ctx['role_map'].get(user.pk) == 'ZZVIEW_A'


def test_role_names_empty_without_map_and_no_query():
    """未注入 role_names_map 时给空数组, 且不查 user_roles。

    这里刻意不做逐行 fallback: 只注入 role_map 的调用方 (如 process 列表) 若 fallback,
    每行 1 次 user_roles 查询, #9 修掉的 N+1 会回来。本测试锁住该行为。
    """
    user = UserFactory()
    UserRoleV2.objects.create(user_id=user.pk, role_code='HRBP', system_code='recruit')
    with CaptureQueriesContext(connection) as ctx:
        data = UserMinimalSerializer(
            [user], many=True, context={'role_map': {user.pk: 'HRBP'}},
        ).data
    assert data[0]['roleNames'] == []
    assert _role_queries(ctx) == [], '未注入 role_names_map 时不应再查 user_roles'
