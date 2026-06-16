"""pytest 全局 fixtures (Phase 1C)"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import Department, Role


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
    return Role.objects.create(
        id='role-hr-001',
        code='HR',
        name='HR',
        is_active=True,
    )


@pytest.fixture
def hrbp_role(db):
    return Role.objects.create(
        id='role-hrbp-001',
        code='HRBP',
        name='HRBP',
        is_active=True,
    )


@pytest.fixture
def super_admin_role(db):
    return Role.objects.create(
        id='role-super-001',
        code='SUPER_ADMIN',
        name='超级管理员',
        is_active=True,
    )


@pytest.fixture
def hr_user(db, department, hr_role):
    user = get_user_model().objects.create_user(
        username='hr_zhang',
        password='Test@1234',
        employee_id='E001',
        department=department,
    )
    user.user_roles.create(role=hr_role, department=department)
    return user


@pytest.fixture
def hrbp_user(db, department, hrbp_role):
    user = get_user_model().objects.create_user(
        username='hrbp_li',
        password='Test@1234',
        employee_id='E002',
        department=department,
    )
    user.user_roles.create(role=hrbp_role, department=department)
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
    user.user_roles.create(role=super_admin_role, department=department)
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
