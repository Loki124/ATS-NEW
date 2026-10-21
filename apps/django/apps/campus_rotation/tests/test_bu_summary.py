"""BU 汇总三段式回归测试（需求 4-1 / S5-14）

锁定 ResourceBuSummaryView 的聚合口径：
1. anchorCount = 该 BU 下 LiveRoom 的 ONGOING 占用（RotationArrangement.stage=ONGOING
   AND current_dept_id=直播间.department_id）；
2. csCount = 该 BU 下 ServiceDept 的 ONGOING 占用（service_dept_id）；
3. capacity 合计（空值按 0）；
4. usedRate = count/capacity，**capacity=0 时返回 null**（防除零）；
5. 总数据 = 直播 + 客服 占用合计 + buList。
"""
import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.core.models import Department, User
from apps.campus_rotation.models import (
    LiveRoom,
    RotationArrangement,
    ServiceDept,
)
from apps.campus_rotation.views import ResourceBuSummaryView


@pytest.fixture
def bu_hierarchy(db):
    """depth 0/1/2/3 的部门链 + 三级部门各一个"""
    root = Department.objects.create(id='r-bu-sum', name='BU根', code='r_bu_sum', parent=None)
    grp = Department.objects.create(id='g-bu-sum', name='事业群', code='g_bu_sum', parent=root)
    bu_a = Department.objects.create(id='bu-a-sum', name='A事业部', code='bu_a_sum', parent=grp)
    bu_b = Department.objects.create(id='bu-b-sum', name='B事业部', code='bu_b_sum', parent=grp)
    dept_a = Department.objects.create(id='dept-a-sum', name='A三级', code='dept_a_sum', parent=bu_a)
    dept_b = Department.objects.create(id='dept-b-sum', name='B三级', code='dept_b_sum', parent=bu_b)
    return {
        'root': root, 'grp': grp, 'bu_a': bu_a, 'bu_b': bu_b,
        'dept_a': dept_a, 'dept_b': dept_b,
    }


def _live_room(dept, bu, capacity):
    lr = LiveRoom(
        name=f'直播-{dept.id}', department=dept, bu=bu,
        platform='VIDEO_ACCOUNT', location='BEIJING',
    )
    lr.capacity = capacity
    lr.save()
    return lr


def _service_dept(dept, bu, capacity):
    sd = ServiceDept(
        name=f'客服-{dept.id}', department=dept, bu=bu, brand='CORE',
    )
    sd.capacity = capacity
    sd.save()
    return sd


def _ongoing(current_dept=None, service_dept=None, person_id=900001):
    return RotationArrangement.objects.create(
        person_id=person_id, stage='ONGOING',
        current_dept=current_dept, service_dept=service_dept,
    )


def test_bu_summary_aggregates_and_null_rate(db, bu_hierarchy):
    h = bu_hierarchy
    # BU-A：直播 cap=10 占 1；客服 cap=5 占 1
    lr_a = _live_room(h['dept_a'], h['bu_a'], 10)
    sd_a = _service_dept(h['dept_a'], h['bu_a'], 5)
    _ongoing(current_dept=h['dept_a'], person_id=900011)
    _ongoing(service_dept=sd_a, person_id=900012)
    # BU-B：直播 cap=0 占 1 → usedRate 必须 null（防除零）
    lr_b = _live_room(h['dept_b'], h['bu_b'], 0)
    _ongoing(current_dept=h['dept_b'], person_id=900013)

    # 内联造超管：测试库未 seed 超管（User.objects.filter(is_superuser=True) 在
    # test_ats_test 中为 None）。超管经 is_super_admin → scope_filter_q 返回全量行级可见。
    admin = User.objects.create_user(
        username='bu_summary_admin',
        employee_id='E-BUSUM',
        is_staff=True,
        is_superuser=True,
    )
    req = APIRequestFactory().get('/api/v1/campus-rotation/resources/bu-summary/')
    force_authenticate(req, user=admin)
    resp = ResourceBuSummaryView.as_view()(req)
    payload = resp.data
    assert resp.status_code == 200
    assert payload['success'] is True
    data = payload['data']

    by_bu = {row['buId']: row for row in data['live']}
    assert h['bu_a'].id in by_bu and h['bu_b'].id in by_bu

    # BU-A：anchorCount=1, capacity=10, usedRate=0.1
    a = by_bu[h['bu_a'].id]
    assert a['anchorCount'] == 1
    assert a['capacity'] == 10
    assert a['usedRate'] == pytest.approx(0.1)

    # BU-B：capacity=0 → usedRate 必须 null
    b = by_bu[h['bu_b'].id]
    assert b['anchorCount'] == 1
    assert b['capacity'] == 0
    assert b['usedRate'] is None

    # 客服段：BU-A csCount=1, capacity=5, usedRate=0.2
    svc = {row['buId']: row for row in data['service']}
    assert svc[h['bu_a'].id]['csCount'] == 1
    assert svc[h['bu_a'].id]['capacity'] == 5
    assert svc[h['bu_a'].id]['usedRate'] == pytest.approx(0.2)

    # 总数据
    total = data['total']
    assert total['liveAnchorTotal'] == 2          # BU-A 1 + BU-B 1
    assert total['serviceTotal'] == 1             # BU-A 1
    assert total['grandTotal'] == 3
    bu_ids = {x['buId'] for x in total['buList']}
    assert {h['bu_a'].id, h['bu_b'].id} <= bu_ids
