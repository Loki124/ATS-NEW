"""定岗双选撮合六步状态机（逆向清单 §4.3 / 契约 §4.3）。

锁定链路（逆向清单 §4.3 原文）：
    ① 校招生填报 N 个志愿（N = 该批次 wish_limit，缺省继承全局默认 2）
    ② 撮合启动后：第一志愿推送至「岗位所属业务 BP」
    ③ BP 录取 → 后续志愿自动释放；BP 放弃 → 下一志愿自动推送
    ④ 两志愿均未被选 → 进入人才市场（status=人才市场），全员 BP 可选
    ⑤ 仍未被选 → 班主任/管理员指定分配（channel=指定）
    ⑥ 管理员发布双选结果

另锁定：撮合启动后校招生**不可再修改志愿**（服务端拒绝 + 明确中文错误信息）。
"""
from datetime import date

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.campus_control.models import Person
from apps.campus_placement.models import (
    PositionApplication,
    PositionDemand,
    SelectionFlow,
)
from apps.campus_placement.views import PositionApplicationViewSet

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-placement'


def _person(code, name, batch='B2026', **kw):
    """建一名校招生档案（批次显式给值，避免被自动批次规则回填）。"""
    return Person.objects.create(
        code=code, name=name, bu='能电BG', school='985', sex='男', major='工学',
        status='在职', batch=batch, **kw,
    )


def _demand(name, **kw):
    """建一个已发布且开放报名的岗位需求（默认全批次可见）。"""
    defaults = {
        'dept': '客服部',
        'business_dept': '能电BG',
        'headcount': 2,
        'need_status': PositionDemand.NeedStatus.PUBLISHED,
        'scope_type': PositionDemand.ScopeType.ALL,
        'open_enabled': True,
        'open_start': date(2026, 1, 1),
        'open_end': date(2026, 12, 31),
    }
    defaults.update(kw)
    return PositionDemand.objects.create(name=name, **defaults)


def _file(client, person, demand, order):
    """走真实 HTTP 填报一条志愿。"""
    return client.post(
        f'{BASE}/applications/',
        {'position_id': demand.id, 'order': order, 'person_id': person.id},
        format='json',
    )


def _start_flow(client, batch='B2026', wish_limit=None):
    """走真实 HTTP 启动撮合（PATCH started=True）→ 触发「第一志愿自动推送」。

    ⚠️ 不能直接 `SelectionFlow.objects.create(started=True)`：自动推送挂在
    ViewSet 的 perform_create / perform_update 上，直接建库不会推送，
    测的就不是状态机本身了。
    """
    flow = SelectionFlow.objects.create(batch=batch, started=False, wish_limit=wish_limit)
    client.patch(f'{BASE}/selection-flows/{flow.id}/', {'started': True}, format='json')
    flow.refresh_from_db()
    assert flow.started is True
    return flow


@pytest.fixture
def student(db):
    return _person('C90000001', '张三')


@pytest.fixture
def demand_a(db):
    return _demand('客服部 · 直播运营')


@pytest.fixture
def demand_b(db):
    return _demand('三到BG · 客服质检')


class Test志愿填报:
    """① 填报志愿。"""

    def test_默认最多两个志愿(self, auth_client, student, demand_a, demand_b):
        """N 缺省继承全局默认 2：第三个志愿被拒。"""
        assert _file(auth_client, student, demand_a, 1).status_code == 201
        assert _file(auth_client, student, demand_b, 2).status_code == 201

        r = _file(auth_client, student, demand_a, 3)
        assert r.status_code == 400
        assert '本批次最多填报 2 个志愿' in str(r.data)

    def test_批次可覆盖志愿上限(self, auth_client, student, demand_a, demand_b):
        """批次 `wish_limit` 覆盖全局默认。"""
        SelectionFlow.objects.create(batch='B2026', started=False, wish_limit=3)
        assert _file(auth_client, student, demand_a, 1).status_code == 201
        assert _file(auth_client, student, demand_b, 2).status_code == 201
        third = PositionDemand.objects.create(
            name='客服部 · 排班', need_status=PositionDemand.NeedStatus.PUBLISHED,
            open_enabled=True, scope_type=PositionDemand.ScopeType.ALL,
        )
        assert _file(auth_client, student, third, 3).status_code == 201

    def test_同一顺序不可重复填报(self, auth_client, student, demand_a, demand_b):
        assert _file(auth_client, student, demand_a, 1).status_code == 201
        r = _file(auth_client, student, demand_b, 1)
        assert r.status_code == 400
        assert '第 1 志愿已填报' in str(r.data)

    def test_同一岗位不可重复填报(self, auth_client, student, demand_a):
        assert _file(auth_client, student, demand_a, 1).status_code == 201
        r = _file(auth_client, student, demand_a, 2)
        assert r.status_code == 400
        assert '该岗位已填报过志愿' in str(r.data)

    def test_岗位未开放不可填报(self, auth_client, student, demand_a):
        """岗位开放判定第一步：审核状态未过 → 拒绝。"""
        demand_a.need_status = PositionDemand.NeedStatus.PENDING
        demand_a.save(update_fields=['need_status'])
        r = _file(auth_client, student, demand_a, 1)
        assert r.status_code == 400
        assert '尚未通过审核' in str(r.data)

    def test_窗口期外不可填报(self, auth_client, student, demand_a):
        """岗位开放判定第五步：窗口期。"""
        demand_a.open_start = date(2099, 1, 1)
        demand_a.save(update_fields=['open_start'])
        r = _file(auth_client, student, demand_a, 1)
        assert r.status_code == 400
        assert '开放报名' in str(r.data)


class Test撮合启动与推送:
    """② 撮合启动 → 第一志愿自动推送给岗位所属业务 BP。"""

    def test_启动后第一志愿自动推送(self, auth_client, student, demand_a, demand_b):
        assert _file(auth_client, student, demand_a, 1).status_code == 201
        assert _file(auth_client, student, demand_b, 2).status_code == 201

        flow = SelectionFlow.objects.create(batch='B2026', started=False)
        r = auth_client.patch(
            f'{BASE}/selection-flows/{flow.id}/', {'started': True}, format='json',
        )
        assert r.status_code == 200

        flow.refresh_from_db()
        assert flow.started is True and flow.start_time is not None

        first = PositionApplication.objects.get(person=student, order=1)
        second = PositionApplication.objects.get(person=student, order=2)
        assert first.status == PositionApplication.Status.PUSHING
        assert first.pushed_at is not None
        # 只推第一志愿，第二志愿保持「已填报」
        assert second.status == PositionApplication.Status.FILED

    def test_post启动即生效(self, auth_client, student, demand_a):
        """POST /selection-flows/ 不传 started → 默认启动（契约 §4.3「POST 启动」）。"""
        assert _file(auth_client, student, demand_a, 1).status_code == 201
        r = auth_client.post(
            f'{BASE}/selection-flows/', {'batch': 'B2026'}, format='json',
        )
        assert r.status_code == 201
        flow = SelectionFlow.objects.get(batch='B2026')
        assert flow.started is True and flow.start_time is not None
        assert PositionApplication.objects.get(person=student).status == (
            PositionApplication.Status.PUSHING
        )

    def test_显式待启动可先定上限(self, auth_client, student, demand_a):
        """`started: false` → 建待启动流程（先定 wish_limit 再开放填报）。"""
        r = auth_client.post(
            f'{BASE}/selection-flows/',
            {'batch': 'B2026', 'wish_limit': 3, 'started': False},
            format='json',
        )
        assert r.status_code == 201
        flow = SelectionFlow.objects.get(batch='B2026')
        assert flow.started is False and flow.wish_limit == 3


class Test录取与释放:
    """③ BP 录取 → 后续志愿自动释放。"""

    def test_录取后其余志愿自动释放(self, auth_client, student, demand_a, demand_b):
        _file(auth_client, student, demand_a, 1)
        _file(auth_client, student, demand_b, 2)
        _start_flow(auth_client)
        first = PositionApplication.objects.get(person=student, order=1)

        r = auth_client.post(f'{BASE}/applications/{first.id}/accept/', {}, format='json')
        assert r.status_code == 200

        first.refresh_from_db()
        second = PositionApplication.objects.get(person=student, order=2)
        assert first.status == PositionApplication.Status.ACCEPTED
        assert first.decision == '接受' and first.decided_at is not None
        assert second.status == PositionApplication.Status.RELEASED

    def test_人才市场志愿可被录取(self, auth_client, student, demand_a, demand_b):
        """状态机 ④：人才市场里的志愿，全员 BP 可选。"""
        _file(auth_client, student, demand_a, 1)
        _start_flow(auth_client)
        app = PositionApplication.objects.get(person=student)
        app.status = PositionApplication.Status.MARKET
        app.save(update_fields=['status'])

        r = auth_client.post(f'{BASE}/applications/{app.id}/accept/', {}, format='json')
        assert r.status_code == 200
        app.refresh_from_db()
        assert app.status == PositionApplication.Status.ACCEPTED


class Test放弃与顺延:
    """③ BP 放弃 → 下一志愿自动推送；④ 两志愿均未被选 → 人才市场。"""

    def test_放弃后下一志愿自动推送(self, auth_client, student, demand_a, demand_b):
        _file(auth_client, student, demand_a, 1)
        _file(auth_client, student, demand_b, 2)
        _start_flow(auth_client)
        first = PositionApplication.objects.get(person=student, order=1)

        r = auth_client.post(f'{BASE}/applications/{first.id}/reject/', {}, format='json')
        assert r.status_code == 200

        first.refresh_from_db()
        second = PositionApplication.objects.get(person=student, order=2)
        assert first.status == PositionApplication.Status.REJECTED
        assert first.decision == '拒绝'
        assert second.status == PositionApplication.Status.PUSHING

    def test_两志愿均未被选进入人才市场(self, auth_client, student, demand_a, demand_b):
        """状态机 ④：两个志愿都被放弃 → 最后一条转入「人才市场」。"""
        _file(auth_client, student, demand_a, 1)
        _file(auth_client, student, demand_b, 2)
        _start_flow(auth_client)

        first = PositionApplication.objects.get(person=student, order=1)
        auth_client.post(f'{BASE}/applications/{first.id}/reject/', {}, format='json')
        second = PositionApplication.objects.get(person=student, order=2)
        assert second.status == PositionApplication.Status.PUSHING

        auth_client.post(f'{BASE}/applications/{second.id}/reject/', {}, format='json')
        second.refresh_from_db()
        assert second.status == PositionApplication.Status.MARKET


class Test指定分配:
    """⑤ 班主任/管理员指定分配（channel=指定）。"""

    def test_指定分配落指定渠道并释放其余志愿(
        self, auth_client, student, demand_a, demand_b,
    ):
        _file(auth_client, student, demand_a, 1)
        _file(auth_client, student, demand_b, 2)
        first = PositionApplication.objects.get(person=student, order=1)

        r = auth_client.post(
            f'{BASE}/applications/{first.id}/assign/',
            {'position_id': demand_b.id},
            format='json',
        )
        assert r.status_code == 200

        assigned = PositionApplication.objects.get(person=student, position=demand_b)
        assert assigned.channel == PositionApplication.Channel.ASSIGNED
        assert assigned.status == PositionApplication.Status.ACCEPTED

        first.refresh_from_db()
        assert first.status == PositionApplication.Status.RELEASED

    def test_指定分配缺岗位报错(self, auth_client, student, demand_a):
        _file(auth_client, student, demand_a, 1)
        app = PositionApplication.objects.get(person=student)
        r = auth_client.post(f'{BASE}/applications/{app.id}/assign/', {}, format='json')
        assert r.status_code == 400
        assert '请指定分配到的岗位需求' in str(r.data)


class Test启动后志愿冻结:
    """撮合启动后校招生不可再修改志愿（逆向清单 §4.3）。"""

    def test_启动后不可再填报(self, auth_client, student, demand_a, demand_b):
        _file(auth_client, student, demand_a, 1)
        SelectionFlow.objects.create(batch='B2026', started=True)

        r = _file(auth_client, student, demand_b, 2)
        assert r.status_code == 400
        assert '不能再修改志愿' in str(r.data)

    def test_启动后不可改已填志愿(self, auth_client, student, demand_a, demand_b):
        _file(auth_client, student, demand_a, 1)
        app = PositionApplication.objects.get(person=student)
        SelectionFlow.objects.create(batch='B2026', started=True)

        r = auth_client.patch(
            f'{BASE}/applications/{app.id}/', {'order': 2}, format='json',
        )
        assert r.status_code == 400
        assert '不能再修改志愿' in str(r.data)


class Test发布双选结果:
    """⑥ 管理员发布双选结果。"""

    def test_发布后流程标记为已发布(self, auth_client, student, demand_a):
        _file(auth_client, student, demand_a, 1)
        flow = SelectionFlow.objects.create(batch='B2026', started=True)

        r = auth_client.post(f'{BASE}/selection-flows/{flow.id}/publish/', {}, format='json')
        assert r.status_code == 200

        flow.refresh_from_db()
        assert flow.published is True and flow.published_at is not None

    def test_未启动不能发布(self, auth_client, db):
        flow = SelectionFlow.objects.create(batch='B2026', started=False)
        r = auth_client.post(f'{BASE}/selection-flows/{flow.id}/publish/', {}, format='json')
        assert r.status_code == 400
        assert '尚未启动' in str(r.data)


class Test可见范围:
    """列表端点按 `campus_control.visibility.visible_persons` 收窄。"""

    def test_班主任只看得见自己带的班(self, db, student):
        from django.contrib.auth import get_user_model

        from apps.core.models_permission_v2 import UserRoleV2

        teacher = get_user_model().objects.create_user(
            username=f'teacher_{student.code}', password='Test@1234',
        )
        UserRoleV2.objects.create(
            user=teacher, role_code='HEAD_TEACHER', system_code='recruit',
        )
        mine = _person('C90000002', '李四', head_teacher=teacher)
        other = _person('C90000003', '王五')
        for person in (student, mine, other):
            PositionApplication.objects.create(
                person=person,
                position=_demand(f'岗位-{person.code}'),
                order=1,
            )

        request = Request(APIRequestFactory().get('/'))
        request.user = teacher
        view = PositionApplicationViewSet()
        view.request = request
        visible = set(
            view.get_queryset().values_list('person_id', flat=True),
        )
        assert visible == {mine.id}
