"""轮岗资源 · 统计概览回归测试（需求 4-x）

锁定 `ResourceStatsOverviewView` + `services.stats_overview` 的聚合口径：

1. **行粒度 = BG × 当前BU**，取值来自校招生档案（`Person.bu` / `Person.intent_bu`）；
2. 人员类指标：入职（有实际入职日期）/ 离职（status=离职）/ 在职（status=在职）；
3. 比率一律「分母为 0 → null」（不静默当成 0）；
4. 性别分布(当前) = **在职**口径；意向BU 男/女 = **不限状态**口径（两者不得混淆）；
5. 轮岗分布按资源类型映射：SERVICE_DEPT→客服 / LIVE_ROOM→主播 / OTHER→其他岗位；
6. 需求按「BU 名 → BG 名 → 未分配」三级兜底归集，**不丢弃**；
7. `bgSpan` = BG 组内行数（组首行承载，其余行 0），供 naive-ui 的 rowSpan 使用；
8. 权限码 `recruit:campus:resource:list` 缺失 → 403。
"""
import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.campus_control.models import Person
from apps.campus_rotation.models import RotationArrangement, RotationResource
from apps.campus_rotation.services import stats_overview
from apps.campus_rotation.views import ResourceStatsOverviewView
from apps.core.models import Department, User
from apps.demand.models import Demand
from apps.process.models import RecruitmentProcess


# ---------------------------------------------------------------------------
# 纯函数层
# ---------------------------------------------------------------------------
def _person(**kw):
    base = {
        'bg': '能电BG', 'bu': '能良出行', 'sex': '男',
        'status': '在职', 'onboarded': True,
    }
    base.update(kw)
    return base


def test_service_aggregates_person_metrics():
    """人员类指标：入职/离职/在职 + 性别分布(在职) + 意向BU(全体)。"""
    persons = [
        _person(sex='男', status='在职', onboarded=True),
        _person(sex='女', status='在职', onboarded=True),
        _person(sex='女', status='离职', onboarded=True),
        _person(sex='男', status='待入职', onboarded=False),
    ]
    out = stats_overview.build_stats_overview(persons=persons, arrangements=[], demands=[])
    row = out['rows'][0]
    assert row['bgGroup'] == '整体'
    # 入职=有实际入职日期 3 人；离职=1；在职=2
    assert row['onboard'] == 3
    assert row['offboard'] == 1
    assert row['active'] == 2
    # 性别分布(当前) 只算在职 → 男 1 / 女 1
    assert row['male'] == 1
    assert row['female'] == 1
    # 意向BU 不限状态 → 男 2 / 女 2
    assert row['intendMale'] == 2
    assert row['intendFemale'] == 2
    # 女生比 = 女 / (男+女) = 2/4
    assert row['femaleRatio'] == pytest.approx(0.5)


def test_service_null_rate_when_denominator_zero():
    """分母为 0 的比率必须为 None（不得静默变成 0）。"""
    out = stats_overview.build_stats_overview(
        # sex 为空 → 不计入男/女 → 意向人群为 0
        persons=[_person(status='待入职', onboarded=False, sex='')],
        arrangements=[], demands=[],
    )
    row = out['rows'][0]
    assert row['demand'] == 0
    assert row['fillRate'] is None      # 业务需求为 0
    assert row['onboard'] == 0
    assert row['retainRate'] is None     # 入职为 0
    assert row['femaleRatio'] is None   # 意向人群为 0
    # 真实的 0 与「无意义」必须可区分：固定率分母为 0 但人数有 → 也是 None
    assert row['active'] == 0


def test_service_resource_type_buckets():
    """资源类型 → 客服 / 主播 / 其他岗位；离职与在职分别计。"""
    arrangements = [
        {'bg': '能电BG', 'bu': '能良出行', 'resource_type': 'SERVICE_DEPT',
         'person_status': '在职', 'fixed': True},
        {'bg': '能电BG', 'bu': '能良出行', 'resource_type': 'LIVE_ROOM',
         'person_status': '在职', 'fixed': False},
        {'bg': '能电BG', 'bu': '能良出行', 'resource_type': 'OTHER',
         'person_status': '离职', 'fixed': True},
        {'bg': '能电BG', 'bu': '能良出行', 'resource_type': 'OTHER',
         'person_status': '离职', 'fixed': False},
    ]
    out = stats_overview.build_stats_overview(
        persons=[], arrangements=arrangements, demands=[],
    )
    row = out['rows'][0]
    assert row['onCS'] == 1
    assert row['onAnchor'] == 1
    assert row['onOther'] == 0
    assert row['offCS'] == 0
    assert row['offAnchor'] == 0
    assert row['offOther'] == 2
    # 已定岗 = final_dept 非空 → 2；其中 1 人已离职 → 定岗流失 1
    assert row['fixed'] == 2
    assert row['lost'] == 1


def test_service_demand_fallback_to_unassigned():
    """需求归集三级兜底：BU 名 → BG 名 → 未分配；不丢弃。"""
    persons = [_person(bg='能电BG', bu='能良出行')]
    demands = [
        {'bu': '能良出行', 'bg': '能电BG', 'headcount': 10},   # BU 名命中
        {'bu': '别的BU', 'bg': '能电BG', 'headcount': 4},      # BG 名命中
        {'bu': '无关BU', 'bg': '无关BG', 'headcount': 3},      # 都落空 → 未分配
    ]
    out = stats_overview.build_stats_overview(
        persons=persons, arrangements=[], demands=demands,
    )
    rows = out['rows']
    hit = next(r for r in rows if r['buName'] == '能良出行')
    assert hit['demand'] == 14            # 10（BU 名命中）+ 4（BG 名命中）
    unassigned = next(r for r in rows if r['bgGroup'] == '未分配 BG')
    assert unassigned['demand'] == 3
    assert out['unassignedDemand'] == 3


def test_service_bg_span_and_overall():
    """bgSpan = BG 组内行数（含末尾小计行）；整体行 = 各明细行之和。"""
    persons = [
        _person(bg='能电BG', bu='BU1'),
        _person(bg='能电BG', bu='BU2'),
        _person(bg='三到BG', bu='BU3'),
    ]
    out = stats_overview.build_stats_overview(persons=persons, arrangements=[], demands=[])
    rows = out['rows']
    assert rows[0]['bgGroup'] == '整体'
    detail = rows[1:]
    spans = {r['buName']: r['bgSpan'] for r in detail}
    # 能电BG 组 = BU1 + BU2 + BG汇总 = 3 行 → 组首行 span=3
    assert spans['BU1'] == 3
    assert spans['BU2'] == 0
    assert spans['BG汇总'] == 0
    # 三到BG 组 = BU3 + BG汇总 = 2 行
    assert spans['BU3'] == 2
    # 小计行不是明细，不能计入整体（否则重复计数）
    detail_only = [r for r in detail if r['buName'] != 'BG汇总']
    assert sum(r['active'] for r in detail_only) == rows[0]['active'] == 3
    # 能电BG 的小计行 = 组内明细之和
    sub = next(r for r in detail if r['bgGroup'] == '能电BG' and r['buName'] == 'BG汇总')
    assert sub['active'] == 2


# ---------------------------------------------------------------------------
# 视图层
# ---------------------------------------------------------------------------
@pytest.fixture
def org_tree(db):
    root = Department.objects.create(id='r-stats', name='根', code='r_stats', parent=None)
    grp = Department.objects.create(id='g-stats', name='事业群', code='g_stats', parent=root)
    bu = Department.objects.create(id='bu-stats', name='BU甲', code='bu_stats', parent=grp)
    return {'root': root, 'grp': grp, 'bu': bu}


def _admin(username='stats_admin'):
    return User.objects.create_user(
        username=username, employee_id=f'E-{username}', is_staff=True, is_superuser=True,
    )


def _mk_person(code, bu, intent_bu, sex, status, entry=True):
    return Person.objects.create(
        code=code, name=f'人{code}', bu=bu, intent_bu=intent_bu,
        school='985', sex=sex, major='工学', status=status,
        expected_entry_date='2026-07-01',
        actual_entry_date='2026-07-01' if entry else None,
    )


def test_view_returns_real_data(db, org_tree):
    _mk_person('P001', '能电BG', 'BU甲', '男', '在职')
    _mk_person('P002', '能电BG', 'BU甲', '女', '离职', entry=True)
    _mk_person('P003', '能电BG', '', '女', '待入职', entry=False)
    admin = _admin('stats_admin_data')
    proc = RecruitmentProcess.objects.create(
        id='proc-stats', code='P-STATS', name='校招流程', current_version='V1.0',
        version_seq=1, is_latest=True, status='ENABLED', is_template=False, is_enabled=True,
    )
    Demand.objects.create(
        id='demand-stats-1', code='D-STATS-1', title='校招需求', department=org_tree['bu'],
        headcount=8, recruit_type='campus', demand_type='CAMPUS',
        requested_by=admin, hr=admin, process=proc, process_version='V1.0',
    )

    req = APIRequestFactory().get('/api/v1/campus-rotation/resources/stats-overview/')
    force_authenticate(req, user=admin)
    resp = ResourceStatsOverviewView.as_view()(req)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    data = resp.data['data']

    total = data['totals']
    assert total['onboard'] == 2      # P001 + P002 有实际入职日期
    assert total['offboard'] == 1
    assert total['active'] == 1
    assert total['male'] == 1         # 在职口径
    assert total['intendFemale'] == 2  # 不限状态

    rows = data['rows']
    assert rows[0]['bgGroup'] == '整体'
    # 有人的分组行（BG=能电BG）
    grp_rows = [r for r in rows if r['bgGroup'] == '能电BG' and r['buName'] != 'BG汇总']
    assert grp_rows
    # 需求按 BU 名（BU甲）命中该行
    assert grp_rows[0]['demand'] == 8
    # 「整体」行 = 各**明细**行之和（小计行是明细的重复，不能再计入）
    detail = [r for r in rows[1:] if r['buName'] != 'BG汇总']
    assert sum(r['demand'] for r in detail) == 8
    assert rows[0]['demand'] == sum(r['demand'] for r in detail) == 8
    # 小计行 = 组内明细之和
    sub = next(r for r in rows if r['buName'] == 'BG汇总')
    assert sub['demand'] == 8


def test_view_requires_permission_code(db, org_tree):
    """缺资源码 → 403（写操作之外的读权限同样受控）。"""
    user = User.objects.create_user(
        username='stats_no_perm', employee_id='E-NOPERM', is_staff=True,
    )
    req = APIRequestFactory().get('/api/v1/campus-rotation/resources/stats-overview/')
    force_authenticate(req, user=user)
    resp = ResourceStatsOverviewView.as_view()(req)
    assert resp.status_code == 403


def test_view_counts_fixed_and_lost(db, org_tree):
    """已定岗 / 定岗流失：来自轮岗安排的定岗去向 + 人员状态。"""
    person = _mk_person('P010', '能电BG', 'BU甲', '男', '离职', entry=True)
    res = RotationResource.objects.create(
        name='直播间-1', resource_type='LIVE_ROOM',
        department=org_tree['bu'], bu=org_tree['bu'],
        platform='VIDEO_ACCOUNT', location='上海',
    )
    arr = RotationArrangement.objects.create(
        campus_person=person, resource=res, intent_bu='BU甲', final_dept='技术中心',
    )
    arr.save()

    admin = _admin('stats_admin_fixed')
    req = APIRequestFactory().get('/api/v1/campus-rotation/resources/stats-overview/')
    force_authenticate(req, user=admin)
    resp = ResourceStatsOverviewView.as_view()(req)
    data = resp.data['data']
    total = data['totals']
    assert total['fixed'] == 1
    assert total['lost'] == 1        # 已定岗且当前离职
    assert total['onAnchor'] == 0    # 人已离职 → 不计入在职分布
    assert total['offAnchor'] == 1   # 计入离职分布
