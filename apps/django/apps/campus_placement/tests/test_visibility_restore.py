"""restore 端点的行级可见范围（2026-10-24 整改：越权恢复）。

**缺陷**：`SoftDeleteRestoreMixin` 在 restore 动作里把取数来源换成 `model.all_objects`
（含软删行），**只**保留 `scope_queryset()` 这一层过滤；本域原先把可见范围写在
`get_queryset()` 里 → restore 路径上被整层丢弃 → 导师/班主任只要拿到 id 就能复活
**别人（可见范围外）**的软删志愿 / 定岗记录（越权）。

正确语义：**只能恢复本用户可见范围内的软删行**，范围外一律 404（不泄露存在性）。
"""
import uuid
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.campus_control.models import Person
from apps.campus_placement.models import (
    PlacementGoal,
    PlacementRecord,
    PositionApplication,
    PositionDemand,
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
    'recruit:campus:placement:publish',
    'recruit:campus:placement:approve',
    'recruit:campus:placement:reject',
    'recruit:campus:placement:assign',
    'recruit:campus:placement_track:list',
    'recruit:campus:placement_track:create',
    'recruit:campus:placement_track:edit',
    'recruit:campus:placement_track:delete',
)


def _uid():
    return uuid.uuid4().hex[:8]


def _make_mentor():
    """造一个带教导师账号（V2 角色 MENTOR + 本域资源码授权）。"""
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


def _client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def mentor_a(db):
    return _make_mentor()


@pytest.fixture
def mentor_b(db):
    return _make_mentor()


@pytest.fixture
def demand(db):
    """一个岗位需求（志愿必须挂在岗位上）。"""
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


def _person(mentor, code=None):
    """造一名校招生档案（归属该导师）。"""
    return Person.objects.create(
        code=code or f'C{_uid()}', name=f'学员{_uid()[:4]}', bu='能电BG', school='985',
        sex='男', major='工学', status='在职', batch='B2026', mentor=mentor,
    )


def _soft_deleted_application(person, demand):
    row = PositionApplication.objects.create(person=person, position=demand, order=1)
    row.soft_delete()
    return row


# ---------------------------------------------------------------------------
# restore 的行级可见范围
# ---------------------------------------------------------------------------
class TestRestore可见范围:
    """志愿 / 定岗跟踪：restore 必须按可见人员收窄。"""

    def test_导师不能恢复可见范围外的软删志愿(self, mentor_a, mentor_b, demand):
        """A 恢复「B 的徒弟」的软删志愿 → 404，且行保持软删。"""
        client = _client_for(mentor_a)
        person_b = _person(mentor_b)
        row = _soft_deleted_application(person_b, demand)

        resp = client.post(f'{BASE}/applications/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 404, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is not None, '越权恢复后软删标记被清掉了'

    def test_导师能恢复自己范围内的软删志愿(self, mentor_a, demand):
        """A 恢复自己徒弟的软删志愿 → 200，行被复活。"""
        client = _client_for(mentor_a)
        person = _person(mentor_a)
        row = _soft_deleted_application(person, demand)

        resp = client.post(f'{BASE}/applications/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 200, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is None

    def test_可见范围外的定岗跟踪记录同样不可恢复(self, mentor_a, mentor_b):
        """定岗跟踪主表也按可见人员收窄。"""
        client = _client_for(mentor_a)
        person_b = _person(mentor_b)
        row = PlacementRecord.objects.create(
            person=person_b, dept='客服部', position_name='客服专员',
            place_date=date(2026, 7, 1), status=PlacementRecord.Status.ONGOING,
        )
        row.soft_delete()

        resp = client.post(f'{BASE}/placement-records/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 404, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is not None

    def test_自己范围内的定岗跟踪记录可恢复(self, mentor_a):
        client = _client_for(mentor_a)
        person = _person(mentor_a)
        row = PlacementRecord.objects.create(
            person=person, dept='客服部', position_name='客服专员',
            place_date=date(2026, 7, 1), status=PlacementRecord.Status.ONGOING,
        )
        row.soft_delete()

        resp = client.post(f'{BASE}/placement-records/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 200, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is None

    def test_定岗子表按所属记录的校招生收窄(self, mentor_a, mentor_b):
        """子表（定岗目标）的人员维度是「经定岗记录」的二级路径 → 同样按可见范围收窄。"""
        client = _client_for(mentor_a)
        record_b = PlacementRecord.objects.create(
            person=_person(mentor_b), dept='客服部', position_name='客服专员',
            place_date=date(2026, 7, 1), status=PlacementRecord.Status.ONGOING,
        )
        goal = PlacementGoal.objects.create(record=record_b, name='转正目标', weight=100)
        goal.soft_delete()

        resp = client.post(f'{BASE}/placement-goals/{goal.id}/restore/', {}, format='json')
        assert resp.status_code == 404, resp.content.decode()

        goal.refresh_from_db()
        assert goal.deleted_at is not None


# ---------------------------------------------------------------------------
# 权限映射别名（契约 §1.2 写 permission_map，仓库运行时读 permission_required_map）
# ---------------------------------------------------------------------------
class Test权限映射别名:
    def test_每个ViewSet都有与运行时一致的permission_map别名(self):
        from apps.campus_placement import views as v

        viewsets = [
            v.PositionDemandViewSet,
            v.PositionApplicationViewSet,
            v.SelectionFlowViewSet,
            v.PlacementRecordViewSet,
            v.PlacementGoalViewSet,
            v.PlacementMetricViewSet,
            v.PlacementAssessmentViewSet,
            v.PriceSchemeViewSet,
            v.PriceBidViewSet,
            v.RevenueRecordViewSet,
            v.BillViewSet,
        ]
        for view in viewsets:
            assert hasattr(view, 'permission_map'), f'{view.__name__} 缺 permission_map 别名'
            assert view.permission_map == view.permission_required_map, (
                f'{view.__name__} 的 permission_map 与 permission_required_map 不一致'
            )
