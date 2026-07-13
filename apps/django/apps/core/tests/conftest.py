"""V2 权限 API 测试专用 fixtures.

复用 tests/conftest.py 的 super_user 模式但避免 cross-tree fixture 加载问题.
pytest-django 只向上找 conftest, tests/conftest.py 不会被 apps/core/tests/* 继承.

T30.175 (V2 cutover follow-up): fixtures 改用 V2 RoleV2 / UserRoleV2 (无 FK).
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def super_user(db):
    """复刻 tests/conftest.py 的 super_user. 部门已存在, 不依赖外部 fixture."""
    from apps.core.models import Department
    from apps.core.models_permission_v2 import RoleV2, UserRoleV2
    dept, _ = Department.objects.get_or_create(
        id='dept-v2-api',
        defaults={'name': 'V2 API dept', 'code': 'V2_API_DEPT', 'path': '/V2'},
    )
    role, _ = RoleV2.objects.get_or_create(
        system_code='recruit',
        role_code='SUPER_ADMIN_V2',
        defaults={'role_name': '超级管理员V2', 'status': 1},
    )
    user = get_user_model().objects.create_user(
        username='admin_v2_api',
        password='Test@1234',
        employee_id='EV2API',
        is_staff=True,
        is_superuser=True,
        department=dept,
    )
    UserRoleV2.objects.create(
        user_id=user.pk,
        role_code=role.role_code,
        system_code=role.system_code,
    )
    return user


@pytest.fixture
def auth_client(super_user):
    """已认证 API client (Bearer JWT, super_user 身份)."""
    client = APIClient()
    refresh = RefreshToken.for_user(super_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client