"""S5-22 考核规则引擎专项测试（需求 5-9：满 15 天必须考核，不足免考）。

锁死：
1. 判定纯函数边界：>= 15 天 → REQUIRED；< 15 天 → WAIVED；日期缺失 → PENDING。
2. 落库自动判定：创建/更新阶段时自动套用规则。
3. 客户端不得直写 assessment_status。
4. 置 DONE 校验：REQUIRED 且无结论 → 400 拒绝；WAIVED → 放行。
5. 定时任务扫描：返回需考核但未考核的清单。
"""
from datetime import date, timedelta

import pytest

from apps.campus_rotation.models import RotationArrangement, RotationStage
from apps.campus_rotation.services import assessment

BASE = '/api/v1/campus-rotation'


@pytest.fixture
def _seed_campus_data(db):
    from apps.campus_rotation.seeds import (
        seed_campus_roles,
        seed_live_room_platform_type,
        seed_location_type,
    )
    seed_campus_roles()
    seed_live_room_platform_type()
    seed_location_type()


@pytest.fixture
def arrangement(db):
    return RotationArrangement.objects.create(person_id=740001)


def _stage(arrangement, **kw):
    defaults = dict(arrangement=arrangement, stage_no=1)
    defaults.update(kw)
    return RotationStage.objects.create(**defaults)


# ──────────────────────────────────────────────────────────────
# 判定纯函数边界
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_exactly_15_days_requires_assessment(arrangement):
    """边界：正好 15 天 → REQUIRED（Q-02 建议口径，>= 15 即考核）。"""
    s = _stage(
        arrangement,
        actual_start=date(2026, 7, 1), actual_end=date(2026, 7, 16),
    )
    assert (date(2026, 7, 16) - date(2026, 7, 1)) == timedelta(days=15)
    assert assessment.evaluate_assessment_status(s) == 'REQUIRED'


@pytest.mark.django_db
def test_14_days_is_waived(arrangement):
    s = _stage(
        arrangement,
        actual_start=date(2026, 7, 1), actual_end=date(2026, 7, 15),
    )
    assert assessment.evaluate_assessment_status(s) == 'WAIVED'


@pytest.mark.django_db
def test_missing_dates_keeps_pending(arrangement):
    s = _stage(arrangement)
    assert assessment.evaluate_assessment_status(s) == 'PENDING'


@pytest.mark.django_db
def test_planned_fallback_when_actual_missing(arrangement):
    """actual_end 缺失时回退 planned_end。"""
    s = _stage(
        arrangement,
        planned_start=date(2026, 7, 1), planned_end=date(2026, 7, 20),
    )
    assert assessment.evaluate_assessment_status(s) == 'REQUIRED'


@pytest.mark.django_db
def test_actual_overrides_planned(arrangement):
    """实际区间优先于计划区间。"""
    s = _stage(
        arrangement,
        planned_start=date(2026, 7, 1), planned_end=date(2026, 7, 20),
        actual_start=date(2026, 7, 1), actual_end=date(2026, 7, 5),
    )
    assert assessment.evaluate_assessment_status(s) == 'WAIVED'


# ──────────────────────────────────────────────────────────────
# 落库自动判定
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_create_auto_evaluates_status(arrangement):
    s = _stage(
        arrangement,
        actual_start=date(2026, 7, 1), actual_end=date(2026, 7, 16),
    )
    s.refresh_from_db()
    assert s.assessment_status == 'REQUIRED'


@pytest.mark.django_db
def test_status_not_client_writable(auth_client, _seed_campus_data, arrangement):
    """客户端直写 assessment_status 须被忽略（规则引擎独占判定）。"""
    r = auth_client.post(
        f'{BASE}/rotation-stages/',
        {
            'arrangement': str(arrangement.id), 'stage_no': 1,
            'actual_start': '2026-07-01', 'actual_end': '2026-07-03',
            'assessment_status': 'DONE',
        },
        format='json',
    )
    assert r.status_code in (200, 201), r.content
    assert r.json()['data']['assessmentStatus'] == 'WAIVED'


# ──────────────────────────────────────────────────────────────
# 置 DONE 校验（400 拒绝）
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_mark_assessed_rejects_required_without_result(auth_client, _seed_campus_data, arrangement):
    """满 15 天且无考核结论 → 拒绝置 DONE，返 400。"""
    s = _stage(
        arrangement,
        actual_start=date(2026, 7, 1), actual_end=date(2026, 7, 16),
    )
    s.refresh_from_db()
    assert s.assessment_status == 'REQUIRED'

    r = auth_client.post(f'{BASE}/rotation-stages/{s.id}/mark-assessed/', {}, format='json')
    assert r.status_code == 400, r.content
    assert '15' in r.json()['message']


@pytest.mark.django_db
def test_mark_assessed_succeeds_with_result(auth_client, _seed_campus_data, arrangement):
    s = _stage(
        arrangement,
        actual_start=date(2026, 7, 1), actual_end=date(2026, 7, 16),
    )
    r = auth_client.post(
        f'{BASE}/rotation-stages/{s.id}/mark-assessed/',
        {'result': '考核合格，达标'}, format='json',
    )
    assert r.status_code == 200, r.content
    assert r.json()['data']['assessmentStatus'] == 'DONE'
    assert r.json()['data']['assessmentResult'] == '考核合格，达标'


@pytest.mark.django_db
def test_mark_assessed_allows_waived(auth_client, _seed_campus_data, arrangement):
    """不足 15 天 → 免考，放行。"""
    s = _stage(
        arrangement,
        actual_start=date(2026, 7, 1), actual_end=date(2026, 7, 5),
    )
    r = auth_client.post(f'{BASE}/rotation-stages/{s.id}/mark-assessed/', {}, format='json')
    assert r.status_code == 200, r.content
    assert r.json()['data']['assessmentStatus'] == 'DONE'


@pytest.mark.django_db
def test_mark_assessed_rejects_when_dates_missing(auth_client, _seed_campus_data, arrangement):
    """起止日期不全 → 无法判定，拒绝置 DONE。"""
    s = _stage(arrangement)
    r = auth_client.post(f'{BASE}/rotation-stages/{s.id}/mark-assessed/', {}, format='json')
    assert r.status_code == 400, r.content
    assert '日期' in r.json()['message']


# ──────────────────────────────────────────────────────────────
# 定时任务
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_reminder_task_scans_required_without_result(arrangement, db):
    """满 15 天需考核但无结论 → 进提醒清单。"""
    from apps.campus_rotation.tasks import rotation_assessment_reminder

    today = date.today()
    s = _stage(
        arrangement,
        actual_start=today - timedelta(days=20), actual_end=today - timedelta(days=1),
    )
    s.refresh_from_db()
    assert s.assessment_status == 'REQUIRED'

    result = rotation_assessment_reminder()
    assert result['need_remind'] >= 1
    assert any(item['id'] == str(s.id) for item in result['items'])


@pytest.mark.django_db
def test_reminder_task_ignores_assessed(arrangement, db):
    from apps.campus_rotation.tasks import rotation_assessment_reminder

    today = date.today()
    s = _stage(
        arrangement,
        actual_start=today - timedelta(days=20), actual_end=today - timedelta(days=1),
    )
    assessment.mark_assessed(s, result='已考核')

    result = rotation_assessment_reminder()
    assert not any(item['id'] == str(s.id) for item in result['items'])
