"""campus_learning 测试用共享 fixtures。

⚠️ 根目录 `apps/django/conftest.py` 已全局加载 `tests.fixtures_common` plugin
（提供 `super_user` / `auth_client` 等基础 fixture），本文件只补**本域专用**的
零件，不重复定义同名 fixture。

⚠️ 用户名 / 工号一律带 uuid：pytest.ini 明确警告 —— 共享 factory 的
`UserFactory` 用进程内 Sequence 命名，跨测试文件会撞名 → 返回别人的用户 →
随机失败（整跑 flaky 根因之一）。
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.campus_control.models import Person
from apps.core.models_permission_v2 import RolePermissionV2, UserRoleV2

User = get_user_model()

#: 本域用到的资源码（与父会话在 core 迁移 0051 登记的码一一对齐）：
#: course / exam / activity / forum 四个子模块的 list + 写码。
LEARNING_RESOURCE_CODES = (
    'recruit:campus:course:list',
    'recruit:campus:course:create',
    'recruit:campus:course:edit',
    'recruit:campus:course:delete',
    'recruit:campus:exam:list',
    'recruit:campus:exam:create',
    'recruit:campus:exam:edit',
    'recruit:campus:exam:delete',
    'recruit:campus:activity:list',
    'recruit:campus:activity:create',
    'recruit:campus:activity:edit',
    'recruit:campus:activity:delete',
    'recruit:campus:forum:list',
    'recruit:campus:forum:create',
    'recruit:campus:forum:edit',
    'recruit:campus:forum:delete',
)


@pytest.fixture
def make_person(db):
    """校招生档案工厂（`Person` 编号/批次由模型自动补，只需给最小必填字段）。"""

    def _make(name='测试校招生', status='在职', **kwargs):
        params = {
            'name': name,
            'bu': '能电BG',
            'school': '985',
            'sex': '男',
            'major': '工学',
            'status': status,
        }
        params.update(kwargs)
        return Person.objects.create(**params)

    return _make


@pytest.fixture
def mentor_user(db):
    """带教导师账号（V2 角色 MENTOR + 本域资源码授权）。

    角色码必须与 `campus_control.visibility.ROLE_MENTOR` 一致（= 'MENTOR'），
    否则可见范围助手认不出来 → 会被当成「无角色」兜底成空集。
    """
    suffix = uuid.uuid4().hex[:8]
    user = User.objects.create_user(
        username=f'mentor_{suffix}',
        password='Test@1234',
        employee_id=f'M{suffix}',
    )
    UserRoleV2.objects.create(user=user, role_code='MENTOR', system_code='recruit')
    for code in LEARNING_RESOURCE_CODES:
        RolePermissionV2.objects.create(
            role_code='MENTOR', resource_code=code, system_code='recruit',
        )
    return user


@pytest.fixture
def mentor_client(mentor_user):
    """导师身份的 API client（非超管 → 走真实可见范围收窄）。"""
    client = APIClient()
    refresh = RefreshToken.for_user(mentor_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client
