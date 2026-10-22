"""S5-18 批量调整端点增强专项测试（需求 5-3）。

锁死：
1. 字段白名单：stage 被拒（走 /transition/），未知字段被拒。
2. 事务 + 整批拒绝：任一条失败 → 整批不落库，返回失败明细。
3. 每条成功记录写一条 AuditLog。
4. mentor / direct_manager 走审批：本端点**不改业务字段**，只建申请单。
5. 行级隔离：不可见的 id 视为失败（不静默跳过）。
"""
import pytest

from apps.campus_rotation.models import RotationApproval, RotationArrangement

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
def arrangements(db):
    return [
        RotationArrangement.objects.create(person_id=760001),
        RotationArrangement.objects.create(person_id=760002),
    ]


# ──────────────────────────────────────────────────────────────
# 白名单
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_stage_rejected(auth_client, _seed_campus_data, arrangements):
    r = auth_client.post(
        f'{BASE}/rotation-arrangements/batch-assign/',
        {'ids': [str(a.id) for a in arrangements], 'stage': 'ONGOING'},
        format='json',
    )
    assert r.status_code == 400, r.content
    assert 'transition' in r.json()['message']


@pytest.mark.django_db
def test_unknown_field_rejected(auth_client, _seed_campus_data, arrangements):
    r = auth_client.post(
        f'{BASE}/rotation-arrangements/batch-assign/',
        {'ids': [str(a.id) for a in arrangements], 'person_id': 999},
        format='json',
    )
    assert r.status_code == 400, r.content
    assert 'person_id' in r.json()['message']


@pytest.mark.django_db
def test_no_field_rejected(auth_client, _seed_campus_data, arrangements):
    r = auth_client.post(
        f'{BASE}/rotation-arrangements/batch-assign/',
        {'ids': [str(a.id) for a in arrangements]},
        format='json',
    )
    assert r.status_code == 400, r.content


# ──────────────────────────────────────────────────────────────
# 免审字段：批量更新 + 审计
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_batch_updates_direct_fields(auth_client, _seed_campus_data, arrangements):
    r = auth_client.post(
        f'{BASE}/rotation-arrangements/batch-assign/',
        {
            'ids': [str(a.id) for a in arrangements],
            'rotation_start': '2026-07-01',
            'rotation_end': '2026-12-31',
        },
        format='json',
    )
    assert r.status_code == 200, r.content
    assert r.json()['data']['updated'] == 2

    for a in arrangements:
        a.refresh_from_db()
        assert str(a.rotation_start) == '2026-07-01'
        assert str(a.rotation_end) == '2026-12-31'


@pytest.mark.django_db
def test_batch_writes_audit_log_per_record(auth_client, _seed_campus_data, arrangements):
    from apps.audit.models import AuditLog

    auth_client.post(
        f'{BASE}/rotation-arrangements/batch-assign/',
        {'ids': [str(a.id) for a in arrangements], 'rotation_start': '2026-07-01'},
        format='json',
    )
    logs = AuditLog.objects.filter(
        action='batch_assign', entity='RotationArrangement',
    ).exclude(entity_id='')
    assert logs.count() == 2, f'期望每条一条审计，实际 {logs.count()}'


# ──────────────────────────────────────────────────────────────
# 整批拒绝语义
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_invalid_mentor_rejects_whole_batch(auth_client, _seed_campus_data, arrangements):
    """mentor 不具备 CAMPUS_MENTOR 身份 → 整批拒绝，一条都不落库。"""
    r = auth_client.post(
        f'{BASE}/rotation-arrangements/batch-assign/',
        {'ids': [str(a.id) for a in arrangements], 'mentor': 999999},
        format='json',
    )
    assert r.status_code == 400, r.content
    assert r.json()['data']['failed']

    for a in arrangements:
        a.refresh_from_db()
        assert a.mentor_id is None
        assert a.rotation_start is None


@pytest.mark.django_db
def test_missing_id_rejected_with_detail(auth_client, _seed_campus_data, arrangements):
    """传不存在的 id → 整批拒绝并返回失败明细。"""
    r = auth_client.post(
        f'{BASE}/rotation-arrangements/batch-assign/',
        {'ids': [str(arrangements[0].id), 'does-not-exist'], 'rotation_start': '2026-07-01'},
        format='json',
    )
    assert r.status_code == 400, r.content
    failed = r.json()['data']['failed']
    assert any('does-not-exist' in str(f.get('id')) for f in failed)

    arrangements[0].refresh_from_db()
    assert arrangements[0].rotation_start is None


# ──────────────────────────────────────────────────────────────
# mentor / direct_manager 走审批
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_mentor_change_creates_approval_not_direct_write(auth_client, _seed_campus_data, arrangements, department):
    from django.contrib.auth import get_user_model

    from apps.campus_rotation.seeds import seed_campus_roles

    mentor = get_user_model().objects.create_user(
        username='batch_mentor', password='Test@1234',
        employee_id='E-BM-01', department=department,
    )
    # 给导师身份
    from apps.campus_rotation.validators import user_has_campus_role
    seed_campus_roles()
    _grant_mentor_role(mentor)

    r = auth_client.post(
        f'{BASE}/rotation-arrangements/batch-assign/',
        {'ids': [str(a.id) for a in arrangements], 'mentor': str(mentor.pk)},
        format='json',
    )
    assert r.status_code == 200, r.content
    assert r.json()['data']['approvalRequested'] == 2

    # 业务字段未改
    for a in arrangements:
        a.refresh_from_db()
        assert a.mentor_id is None

    # 生成了申请单
    assert RotationApproval.objects.filter(change_type='MENTOR_CHANGE').count() == 2


def _grant_mentor_role(user):
    """给用户授予 CAMPUS_MENTOR 身份（幂等）。

    对齐 validators.user_has_campus_role 的判定口径：
    RoleV2 须 system_code='recruit' / role_code='CAMPUS_MENTOR' / status=1 / is_system=1，
    且 UserRoleV2 存在对应授予行。
    """
    from apps.core.models import RoleV2, UserRoleV2
    role = RoleV2.objects.filter(
        system_code='recruit', role_code='CAMPUS_MENTOR', status=1, is_system=1,
    ).first()
    if role is None:
        return
    UserRoleV2.objects.get_or_create(
        user=user,
        system_code='recruit', role_code='CAMPUS_MENTOR',
    )


@pytest.mark.django_db
def test_approval_then_mentor_applied(auth_client, _seed_campus_data, arrangements, department):
    """建单 → 审批通过 → mentor 落字段（与 S5-17 语义一致）。"""
    from django.contrib.auth import get_user_model

    from apps.campus_rotation.seeds import seed_campus_roles

    seed_campus_roles()
    mentor = get_user_model().objects.create_user(
        username='batch_mentor2', password='Test@1234',
        employee_id='E-BM-02', department=department,
    )
    _grant_mentor_role(mentor)

    r = auth_client.post(
        f'{BASE}/rotation-arrangements/batch-assign/',
        {'ids': [str(arrangements[0].id)], 'mentor': str(mentor.pk)},
        format='json',
    )
    assert r.status_code == 200, r.content

    ap = RotationApproval.objects.filter(change_type='MENTOR_CHANGE').first()
    assert ap is not None
    arr = arrangements[0]
    arr.refresh_from_db()
    assert arr.mentor_id is None  # 审批前不落字段

    appr = auth_client.post(f'{BASE}/rotation-approvals/{ap.id}/approve/')
    assert appr.status_code == 200, appr.content
    arr.refresh_from_db()
    assert arr.mentor_id == mentor.pk
