"""v2 权限模块全局 pytest fixtures.

注意: 已有 tests/conftest.py 提供 hr_user / hrbp_user / super_user / auth_client
等基础 fixtures (Phase 1C). 这里只补充 v2 权限重写专用的 IDOR 跨部门测试 fixtures,
不重复定义同名 fixture 以避免覆盖.

v2 权限 IDOR 测试需要两个不同部门的 HR 用户, 用于验证:
  - HR(dept_a) 不能看到 dept_b 的数据
  - HR(dept_b) 不能看到 dept_a 的数据
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def dept_a(db):
    """部门 a - 用于跨部门 IDOR 测试."""
    from apps.core.models import Department
    return Department.objects.create(id='dept-a-v2', name='部门A-V2', code='dept_a_v2', path='/部门A-V2')


@pytest.fixture
def dept_b(db):
    """部门 b - 用于跨部门 IDOR 测试."""
    from apps.core.models import Department
    return Department.objects.create(id='dept-b-v2', name='部门B-V2', code='dept_b_v2', path='/部门B-V2')


@pytest.fixture
def hr_dept_a(db, dept_a):
    """HR 用户, 部门 a. 应当只看到 dept_a 的数据."""
    u, _ = User.objects.get_or_create(
        username='hr_dept_a',
        defaults={
            'is_active': True,
            'department': dept_a,
            'first_name': 'HrA',
            'last_name': 'A',
        },
    )
    u.set_password('hr123')
    u.save()
    return u


@pytest.fixture
def hr_dept_b(db, dept_b):
    """HR 用户, 部门 b. 应当只看到 dept_b 的数据."""
    u, _ = User.objects.get_or_create(
        username='hr_dept_b',
        defaults={
            'is_active': True,
            'department': dept_b,
            'first_name': 'HrB',
            'last_name': 'B',
        },
    )
    u.set_password('hr123')
    u.save()
    return u