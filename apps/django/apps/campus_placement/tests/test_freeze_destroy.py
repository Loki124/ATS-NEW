"""撮合启动后的志愿冻结（2026-10-24 整改：软删 / 恢复也要拦）。

**缺陷**：契约 §4.3「`SelectionFlow.started=True` 后校招生**不可再修改志愿**
（服务端拒绝）」。原实现只在 `create`（填报）与 `update`（改）拦，
**`destroy`（软删志愿）与 `restore`（恢复志愿）没拦** →
撮合启动后仍能把自己**已推送**的志愿删掉（BP 手里已拿到的志愿对不上）。

本文件锁定：启动后 destroy / restore 一律 400 + 明确中文错误；未启动时行为不变。
"""
import uuid
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.campus_control.models import Person
from apps.campus_placement.models import (
    PositionApplication,
    PositionDemand,
    SelectionFlow,
)
from apps.core.models_permission_v2 import RolePermissionV2, UserRoleV2

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-placement'

User = get_user_model()

#: 本域用到的资源码（与 core 迁移登记的码一致）
PLACEMENT_CODES = (
    'recruit:campus:placement:list',
    'recruit:campus:placement:create',
    'recruit:campus:placement:edit',
    'recruit:campus:placement:delete',
)


def _uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def mentor_user(db):
    """带教导师账号（V2 角色 MENTOR + 本域资源码授权）。"""
    user = User.objects.create_user(
        username=f'mentor_{_uid()}', password='Test@1234', employee_id=f'M{_uid()}',
    )
    UserRoleV2.objects.create(user=user, role_code='MENTOR', system_code='recruit')
    for code in PLACEMENT_CODES:
        RolePermissionV2.objects.get_or_create(
            role_code='MENTOR', resource_code=code,
            defaults={'system_code': 'recruit'},
        )
    return user


@pytest.fixture
def mentor_client(mentor_user):
    """带教导师身份的客户端（非超管 → 走真实权限码校验 + 真实可见范围收窄）。"""
    client = APIClient()
    refresh = RefreshToken.for_user(mentor_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def person(mentor_user):
    """一名归属该导师的校招生（导师可见范围内的档案）。"""
    return Person.objects.create(
        code=f'C{_uid()}', name='张三', bu='能电BG', school='985', sex='男', major='工学',
        status='在职', batch='B2026', mentor=mentor_user,
    )


@pytest.fixture
def demand(db):
    return PositionDemand.objects.create(
        name=f'岗位-{_uid()}',
        dept='客服部',
        business_dept='能电BG',
        headcount=2,
        need_status=PositionDemand.NeedStatus.PUBLISHED,
        scope_type=PositionDemand.ScopeType.ALL,
        open_enabled=True,
        open_start=date(2026, 1, 1),
        open_end=date(2026, 12, 31),
    )


@pytest.fixture
def application(db, person, demand):
    """一条已填报的志愿。"""
    return PositionApplication.objects.create(
        person=person, position=demand, order=1,
        status=PositionApplication.Status.FILED,
    )


class Test启动后不可删志愿:
    """撮合启动后软删志愿被拒。"""

    def test_启动后删除志愿被拒(self, mentor_client, application):
        SelectionFlow.objects.create(batch='B2026', started=True)

        resp = mentor_client.delete(f'{BASE}/applications/{application.id}/')
        assert resp.status_code == 400, resp.content.decode()
        assert '不能再修改志愿' in str(resp.content.decode())

        application.refresh_from_db()
        assert application.deleted_at is None, '启动后志愿仍被软删了'

    def test_启动后删除被推送的志愿同样被拒(self, mentor_client, application):
        """已推送给 BP 的志愿（状态=推送中）更不能删。"""
        application.status = PositionApplication.Status.PUSHING
        application.save(update_fields=['status'])
        SelectionFlow.objects.create(batch='B2026', started=True)

        resp = mentor_client.delete(f'{BASE}/applications/{application.id}/')
        assert resp.status_code == 400, resp.content.decode()
        assert '不能再修改志愿' in str(resp.content.decode())

        application.refresh_from_db()
        assert application.deleted_at is None

    def test_未启动时可以正常软删志愿(self, mentor_client, application):
        """未启动 → 软删照常（契约只冻结「启动后」）。"""
        SelectionFlow.objects.create(batch='B2026', started=False)

        resp = mentor_client.delete(f'{BASE}/applications/{application.id}/')
        assert resp.status_code in (200, 204), resp.content.decode()

        application.refresh_from_db()
        assert application.deleted_at is not None


class Test启动后不可恢复志愿:
    """撮合启动后恢复（= 撤回删除）同样被拒。"""

    def test_启动后恢复志愿被拒(self, mentor_client, application):
        """先在未启动时软删，再启动撮合 → 恢复被拒。"""
        application.soft_delete()
        SelectionFlow.objects.create(batch='B2026', started=True)

        resp = mentor_client.post(f'{BASE}/applications/{application.id}/restore/', {}, format='json')
        assert resp.status_code == 400, resp.content.decode()
        assert '不能再修改志愿' in str(resp.content.decode())

        application.refresh_from_db()
        assert application.deleted_at is not None, '启动后志愿仍被恢复了'

    def test_未启动时可以正常恢复志愿(self, mentor_client, application):
        application.soft_delete()
        SelectionFlow.objects.create(batch='B2026', started=False)

        resp = mentor_client.post(f'{BASE}/applications/{application.id}/restore/', {}, format='json')
        assert resp.status_code == 200, resp.content.decode()

        application.refresh_from_db()
        assert application.deleted_at is None
