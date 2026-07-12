"""V2 权限 API 测试专用 fixtures.

复用 tests/conftest.py 的 super_user 模式但避免 cross-tree fixture 加载问题.
pytest-django 只向上找 conftest, tests/conftest.py 不会被 apps/core/tests/* 继承.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def super_user(db):
    """复刻 tests/conftest.py 的 super_user. 部门已存在, 不依赖外部 fixture."""
    from apps.core.models import Department, Role
    dept, _ = Department.objects.get_or_create(
        id='dept-v2-api',
        defaults={'name': 'V2 API dept', 'code': 'V2_API_DEPT', 'path': '/V2'},
    )
    role, _ = Role.objects.get_or_create(
        id='role-super-v2-api',
        defaults={'code': 'SUPER_ADMIN_V2', 'name': '超级管理员V2', 'is_active': True},
    )
    user = get_user_model().objects.create_user(
        username='admin_v2_api',
        password='Test@1234',
        employee_id='EV2API',
        is_staff=True,
        is_superuser=True,
        department=dept,
    )
    user.user_roles.create(role=role, department=dept)
    return user


@pytest.fixture
def auth_client(super_user):
    """已认证 API client (Bearer JWT, super_user 身份)."""
    client = APIClient()
    refresh = RefreshToken.for_user(super_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client