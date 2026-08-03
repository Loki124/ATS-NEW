"""V2 权限 API 测试专用 fixtures.

复刻 tests/fixtures_common.py 的 super_user 模式, 但用独立的用户名 / 部门,
避免与全局 fixture 同名对象冲突.

T30.175 (V2 cutover follow-up): fixtures 改用 V2 RoleV2 / UserRoleV2 (无 FK).

2026-08-03 R7 (寇豆码): 这批测试此前从未被 pytest 收集过 (pytest.ini
`testpaths = tests`), 纳入收集后 8 个用例在 fixture setup 阶段就
`IntegrityError: NOT NULL constraint failed: roles.id`.

  根因: SQLite 测试库跑的是 V1 migrations, `roles` 表 PK 是
  `id VARCHAR(32) NOT NULL` (非自增); 而 `RoleV2` 声明的是 BigAutoField.
  `RoleV2.objects.get_or_create()` 不会给 id 赋值 → INSERT 违反 NOT NULL.
  `UserRoleV2.objects.create()` 同理会撞 V1 `user_roles.role_id NOT NULL`.

  修法: 直接复用 tests/fixtures_common.py 里已经处理好这两个兼容问题的
  `_create_role_v2()` / `_raw_attach_v2_role()` (raw SQL 显式写 id + role_id),
  不再重复实现一套。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.fixtures_common import _create_role_v2, _raw_attach_v2_role


@pytest.fixture
def super_user(db):
    """复刻全局 super_user. 部门/角色独立命名, 不依赖外部 fixture."""
    from apps.core.models import Department
    from apps.core.models_permission_v2 import RoleV2
    dept, _ = Department.objects.get_or_create(
        id='dept-v2-api',
        defaults={'name': 'V2 API dept', 'code': 'V2_API_DEPT', 'path': '/V2'},
    )
    role = RoleV2.objects.filter(
        system_code='recruit', role_code='SUPER_ADMIN_V2',
    ).first()
    if role is None:
        # raw SQL 建角色: 兼容 V1 roles 表 VARCHAR(32) NOT NULL 主键
        role = _create_role_v2('SUPER_ADMIN_V2', '超级管理员V2')
    user = get_user_model().objects.create_user(
        username='admin_v2_api',
        password='Test@1234',
        employee_id='EV2API',
        is_staff=True,
        is_superuser=True,
        department=dept,
    )
    # raw SQL 挂角色: 兼容 V1 user_roles.role_id NOT NULL 外键
    _raw_attach_v2_role(user, role)
    return user


@pytest.fixture
def auth_client(super_user):
    """已认证 API client (Bearer JWT, super_user 身份)."""
    client = APIClient()
    refresh = RefreshToken.for_user(super_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client