"""pytest 全局 fixtures (Phase 1C)

T30.175 (V2 cutover follow-up): fixtures 同时支持 V1 (test DB SQLite, V1 migrations)
和 V2 (dev MySQL, V2 cutover applied). 通过探测 roles 表是否有 role_code 列
动态选择路径. 这保证单测在切库前/切库后都能跑.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import Department, Role as _V1_Role
from apps.core.models_permission_v2 import RoleV2, UserRoleV2


def _v2_schema_present() -> bool:
    """探测 V2 schema 是否就绪. SQLite in-memory (test DB, V1 migrations) → False.
    MySQL/dev DB with V2 cutover → True.
    """
    try:
        from django.db import connection
        with connection.cursor() as c:
            if 'sqlite' in connection.vendor:
                c.execute("PRAGMA table_info(roles)")
            else:
                c.execute("DESCRIBE roles")
            cols = {row[1] for row in c.fetchall()}
        return 'role_code' in cols
    except Exception:
        return False


@pytest.fixture
def user_model():
    return get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def department(db):
    return Department.objects.create(
        id='dept-test-001',
        name='测试部门',
        code='TEST_DEPT',
        path='/测试部门',
    )


@pytest.fixture
def hr_role(db):
    if _v2_schema_present():
        return RoleV2.objects.create(
            system_code='recruit', role_code='HR', role_name='HR', status=1,
        )
    return _V1_Role.objects.create(
        id='role-hr-001', code='HR', name='HR', is_active=True,
    )


@pytest.fixture
def hrbp_role(db):
    if _v2_schema_present():
        return RoleV2.objects.create(
            system_code='recruit', role_code='HRBP', role_name='HRBP', status=1,
        )
    return _V1_Role.objects.create(
        id='role-hrbp-001', code='HRBP', name='HRBP', is_active=True,
    )


@pytest.fixture
def super_admin_role(db):
    if _v2_schema_present():
        return RoleV2.objects.create(
            system_code='recruit', role_code='SUPER_ADMIN', role_name='超级管理员', status=1,
        )
    return _V1_Role.objects.create(
        id='role-super-001', code='SUPER_ADMIN', name='超级管理员', is_active=True,
    )


def _attach_role(user, role) -> None:
    """T30.175: V2 → UserRoleV2; V1 → user.user_roles. 根据 role 类型自动分支.
    """
    if isinstance(role, RoleV2):
        UserRoleV2.objects.get_or_create(
            user_id=user.pk,
            role_code=role.role_code,
            system_code=role.system_code,
        )
    else:
        # V1 path (test DB on SQLite still runs V1 migrations)
        user.user_roles.create(role=role, department=None)


@pytest.fixture
def hr_user(db, department, hr_role):
    user = get_user_model().objects.create_user(
        username='hr_zhang',
        password='Test@1234',
        employee_id='E001',
        department=department,
    )
    _attach_role(user, hr_role)
    return user


@pytest.fixture
def hrbp_user(db, department, hrbp_role):
    user = get_user_model().objects.create_user(
        username='hrbp_li',
        password='Test@1234',
        employee_id='E002',
        department=department,
    )
    _attach_role(user, hrbp_role)
    return user


@pytest.fixture
def super_user(db, department, super_admin_role):
    user = get_user_model().objects.create_user(
        username='admin',
        password='Test@1234',
        employee_id='E000',
        is_staff=True,
        is_superuser=True,
        department=department,
    )
    _attach_role(user, super_admin_role)
    return user


@pytest.fixture
def auth_client(super_user):
    """已认证的 API client"""
    client = APIClient()
    refresh = RefreshToken.for_user(super_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def auth_hr_client(hr_user):
    """HR 身份认证 client"""
    client = APIClient()
    refresh = RefreshToken.for_user(hr_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def auth_hrbp_client(hrbp_user):
    """HRBP 身份认证 client"""
    client = APIClient()
    refresh = RefreshToken.for_user(hrbp_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client
