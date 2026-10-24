"""restore 端点的行级可见范围（2026-10-24 整改核验）。

**背景**：本域的 restore 取对象**不走** `get_object()`，而是走
`LearningCRUDMixin.restore_queryset()`（含软删行的 manager）——
因此可见范围的收窄必须落在 `restore_queryset()` 上，
由 `VisibilityScopeMixin.restore_queryset()` 按 `visibility_person_field` 实现。

正确语义：**只能恢复本用户可见范围内的软删行**（带人员的模型：学习进度 / 学习记录 /
考试成绩 / 活动评分），范围外的行 → 404（不泄露存在性）。
无人员维度的模型（课程 / 考试 / 活动 / 板块）是全局目录 → 不按人员收窄（设计如此）。

本文件是**回归护栏**：防止后人把 `VisibilityScopeMixin.restore_queryset` 的收窄删掉
（基类顺序一旦调换，`super()` 链断裂 → 恢复时忘记过滤可见范围 → 越权）。
"""
import uuid
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.campus_learning.models import Course, LearnProgress, LearnRecord
from apps.core.models_permission_v2 import RolePermissionV2, UserRoleV2

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-learning'

User = get_user_model()


def _uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def course(db):
    """一门课程（学习进度必须有课程维度）。"""
    return Course.objects.create(code=f'C{_uid()}', name='新人训练营', duration_min=60)


@pytest.fixture
def other_mentor(db):
    """另一个导师（用来造「本导师看不见的人」）。"""
    user = User.objects.create_user(
        username=f'mentor_{_uid()}', password='Test@1234', employee_id=f'M{_uid()}',
    )
    UserRoleV2.objects.create(user=user, role_code='MENTOR', system_code='recruit')
    for code in ('recruit:campus:course:list', 'recruit:campus:course:edit'):
        # get_or_create：MENTOR 角色的授权行可能已由 conftest 的 mentor_user 建过
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


def _soft_deleted_progress(person, course):
    row = LearnProgress.objects.create(person=person, course=course, progress=50, minutes=30)
    row.soft_delete()
    return row


# ---------------------------------------------------------------------------
# restore 的行级可见范围
# ---------------------------------------------------------------------------
class TestRestore可见范围:
    """带人员的模型：restore 必须按可见人员收窄。"""

    def test_导师不能恢复可见范围外的软删学习进度(self, mentor_client, mentor_user, other_mentor,
                                                 make_person, course):
        """A 恢复「B 的徒弟」的软删学习进度 → 404，且行保持软删。"""
        person_b = make_person(name='B的徒弟', mentor=other_mentor)
        row = _soft_deleted_progress(person_b, course)

        resp = mentor_client.post(f'{BASE}/learn-progress/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 404, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is not None, '越权恢复后软删标记被清掉了'

    def test_导师能恢复自己范围内的软删学习进度(self, mentor_client, mentor_user, make_person, course):
        """A 恢复自己徒弟的软删学习进度 → 200，行被复活。"""
        person = make_person(name='我的徒弟', mentor=mentor_user)
        row = _soft_deleted_progress(person, course)

        resp = mentor_client.post(f'{BASE}/learn-progress/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 200, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is None

    def test_学习记录同样按可见范围收窄(self, mentor_client, mentor_user, other_mentor,
                                    make_person, course):
        """LearnRecord 也是带人员维度的模型 → 同样不可越权恢复。"""
        person_b = make_person(name='B的徒弟2', mentor=other_mentor)
        row = LearnRecord.objects.create(
            person=person_b, course=course, date=date(2026, 7, 1), minutes=20,
        )
        row.soft_delete()

        resp = mentor_client.post(f'{BASE}/learn-records/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 404, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is not None

    def test_自己范围内的学习记录可恢复(self, mentor_client, mentor_user, make_person, course):
        person = make_person(name='我的徒弟2', mentor=mentor_user)
        row = LearnRecord.objects.create(
            person=person, course=course, date=date(2026, 7, 1), minutes=20,
        )
        row.soft_delete()

        resp = mentor_client.post(f'{BASE}/learn-records/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 200, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is None

    def test_无人员维度的课程不按人员收窄(self, mentor_client, mentor_user, course):
        """课程是全局目录（逆向清单 §4.2）→ 恢复不受人员范围限制（设计如此）。"""
        course.soft_delete()

        resp = mentor_client.post(f'{BASE}/courses/{course.id}/restore/', {}, format='json')
        assert resp.status_code == 200, resp.content.decode()

        course.refresh_from_db()
        assert course.deleted_at is None


# ---------------------------------------------------------------------------
# 权限映射别名（契约 §1.2 写 permission_map，仓库运行时读 permission_required_map）
# ---------------------------------------------------------------------------
class Test权限映射别名:
    def test_每个ViewSet都有与运行时一致的permission_map别名(self):
        from apps.campus_learning import views as v

        viewsets = [
            v.CourseViewSet,
            v.LearnProgressViewSet,
            v.LearnRecordViewSet,
            v.ExamViewSet,
            v.ExamScoreViewSet,
            v.ActivityViewSet,
            v.ActivityScoreViewSet,
            v.ForumBoardViewSet,
            v.ForumPostViewSet,
        ]
        for view in viewsets:
            assert hasattr(view, 'permission_map'), f'{view.__name__} 缺 permission_map 别名'
            assert view.permission_map == view.permission_required_map, (
                f'{view.__name__} 的 permission_map 与 permission_required_map 不一致'
            )
