"""BU 汇总分段式回归测试（需求 4-1 / S5-14）

锁定 ResourceBuSummaryView 的聚合口径（2026-10-22 直播间+客服部门合并为
「轮岗资源」后改为「一张表 + 按 resource_type 分段」）：

1. 数据源统一为 `RotationResource`；
2. 占用口径统一为**资源级**：`RotationArrangement.resource_id` + stage=ONGOING；
3. 分段：live（直播间）/ service（客服部门）/ other（其他），各段独立算
   count 与 capacity；
4. capacity 合计（空值按 0）；
5. usedRate = count/capacity，**capacity=0 时返回 null**（防除零）；
6. 总数据 = 三段占用合计 + buList。
"""
import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.campus_rotation.models import (
    RotationArrangement,
    RotationResource,
)
from apps.campus_rotation.views import ResourceBuSummaryView
from apps.core.models import Department, User


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


def _resource(dept, bu, capacity, resource_type='LIVE_ROOM', name=None):
    """建一条轮岗资源（直播间 / 客服部门 / 其他）。"""
    res = RotationResource(
        name=name or f'{resource_type}-{dept.id}',
        resource_type=resource_type,
        department=dept, bu=bu,
        platform='VIDEO_ACCOUNT' if resource_type == 'LIVE_ROOM' else '',
        location='BEIJING',
    )
    res.capacity = capacity
    res.save()
    return res


def _ongoing(resource=None, person_id=900001):
    # 🔴 S5-19：stage 为 FSM 流程态，初始 PENDING，经 submit→approve 才到 ONGOING。
    obj = RotationArrangement.objects.create(
        person_id=person_id, resource=resource,
    )
    obj.submit()
    obj.approve()
    obj.save()
    return obj


def test_bu_summary_aggregates_and_null_rate(db, bu_hierarchy):
    h = bu_hierarchy
    # BU-A：直播 cap=10 占 1；客服 cap=5 占 1
    lr_a = _resource(h['dept_a'], h['bu_a'], 10, 'LIVE_ROOM')
    sd_a = _resource(h['dept_a'], h['bu_a'], 5, 'SERVICE_DEPT')
    _ongoing(resource=lr_a, person_id=900011)
    _ongoing(resource=sd_a, person_id=900012)
    # BU-B：直播 cap=0 占 1 → usedRate 必须 null（防除零）
    lr_b = _resource(h['dept_b'], h['bu_b'], 0, 'LIVE_ROOM')
    _ongoing(resource=lr_b, person_id=900013)

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
    assert total['otherTotal'] == 0
    assert total['grandTotal'] == 3
    bu_ids = {x['buId'] for x in total['buList']}
    assert {h['bu_a'].id, h['bu_b'].id} <= bu_ids


def test_bu_summary_segments_other_type(db, bu_hierarchy):
    """「其他」类型资源必须单独成段（不能从汇总里消失）。"""
    h = bu_hierarchy
    other = _resource(h['dept_a'], h['bu_a'], 8, 'OTHER')
    _ongoing(resource=other, person_id=900021)

    admin = User.objects.create_user(
        username='bu_summary_admin_other',
        employee_id='E-BUSUM2',
        is_staff=True,
        is_superuser=True,
    )
    req = APIRequestFactory().get('/api/v1/campus-rotation/resources/bu-summary/')
    force_authenticate(req, user=admin)
    resp = ResourceBuSummaryView.as_view()(req)
    data = resp.data['data']

    seg = {row['buId']: row for row in data['other']}
    assert seg[h['bu_a'].id]['otherCount'] == 1
    assert seg[h['bu_a'].id]['capacity'] == 8
    assert seg[h['bu_a'].id]['usedRate'] == pytest.approx(0.125)
    assert data['total']['otherTotal'] == 1
    assert data['total']['grandTotal'] == 1


def test_bu_summary_counts_by_resource_not_department(db, bu_hierarchy):
    """🔴 占用口径：按**资源**统计，不按归属部门。

    合并前直播间口径是「按归属部门」（current_dept_id == 资源.归属部门），
    合并后统一为资源级（resource_id）→ 同一部门下的两个资源不会互相重复计入。
    """
    h = bu_hierarchy
    r1 = _resource(h['dept_a'], h['bu_a'], 10, 'LIVE_ROOM', name='直播间一')
    _resource(h['dept_a'], h['bu_a'], 10, 'LIVE_ROOM', name='直播间二')
    # 一条安排占用 r1；另一条只落在部门上（无资源）→ 不应计入任何资源
    _ongoing(resource=r1, person_id=900031)
    _ongoing(resource=None, person_id=900032)

    admin = User.objects.create_user(
        username='bu_summary_admin_res',
        employee_id='E-BUSUM3',
        is_staff=True,
        is_superuser=True,
    )
    req = APIRequestFactory().get('/api/v1/campus-rotation/resources/bu-summary/')
    force_authenticate(req, user=admin)
    resp = ResourceBuSummaryView.as_view()(req)
    data = resp.data['data']

    seg = {row['buId']: row for row in data['live']}
    # 容量是两个直播间之和（20），占用只有 1（无资源的那条不计入）
    assert seg[h['bu_a'].id]['capacity'] == 20
    assert seg[h['bu_a'].id]['anchorCount'] == 1
