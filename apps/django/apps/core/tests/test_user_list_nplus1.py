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
