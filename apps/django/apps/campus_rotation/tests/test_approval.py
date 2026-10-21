"""S5-17 轮岗变更审批流专项测试（需求 5-5）。

锁死：
1. 核心语义：**创建申请单时不改业务字段**（mentor / direct_manager 保持原值）。
2. 审批通过（approve）后：业务字段落值 + 写两条 AuditLog。
3. 审批驳回（reject）：只记录状态与原因，**不落业务字段**。
4. 非法状态流转：已 APPROVED/REJECTED 的单再审批 → 409，不重复落字段。
5. 目标人员不存在 → 拒绝落字段，事务回滚（申请单状态不变）。
6. 免审路径不受影响：兼岗记录创建、阶段/部门/日期等字段不走审批。
"""
import pytest

from apps.campus_rotation.models import RotationApproval, RotationArrangement
from apps.campus_rotation.services import approval as approval_service

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
def mentor_user(db, department):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(
        username='campus_mentor_01', password='Test@1234',
        employee_id='E-MENTOR-01', department=department,
    )


@pytest.fixture
def new_mentor_user(db, department):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(
        username='campus_mentor_02', password='Test@1234',
        employee_id='E-MENTOR-02', department=department,
    )


@pytest.fixture
def arrangement(db, mentor_user):
    return RotationArrangement.objects.create(
        person_id=750001, mentor=mentor_user,
    )


# ──────────────────────────────────────────────────────────────
# 服务层：核心语义
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_create_request_does_not_change_business_field(arrangement, new_mentor_user):
    """🔴 核心：创建申请单不改 RotationArrangement.mentor。"""
    old_mentor_id = arrangement.mentor_id
    ap = approval_service.create_approval_request(
        arrangement=arrangement,
        change_type='MENTOR_CHANGE',
        new_user_id=new_mentor_user.pk,
        reason='原导师离职',
    )
    arrangement.refresh_from_db()
    assert arrangement.mentor_id == old_mentor_id
    assert ap.status == 'PENDING'
    assert ap.old_value == str(old_mentor_id)
    assert ap.new_value == str(new_mentor_user.pk)


@pytest.mark.django_db
def test_approve_applies_field_and_writes_two_audit_logs(arrangement, new_mentor_user, super_user):
    """审批通过 → 落字段 + 两条 AuditLog。"""
    from apps.audit.models import AuditLog

    ap = approval_service.create_approval_request(
        arrangement=arrangement,
        change_type='MENTOR_CHANGE',
        new_user_id=new_mentor_user.pk,
        reason='原导师离职',
    )
    approval_service.approve(ap, approver=super_user)

    arrangement.refresh_from_db()
    ap.refresh_from_db()
    assert arrangement.mentor_id == new_mentor_user.pk
    assert ap.status == 'APPROVED'
    assert ap.approver_id == super_user.pk
    assert ap.approved_at is not None

    logs = AuditLog.objects.filter(entity_id=str(ap.pk), action='approve')
    assert logs.count() == 1
    field_logs = AuditLog.objects.filter(
        entity='RotationArrangement', entity_id=str(arrangement.pk), action='update',
    )
    assert field_logs.count() == 1
    assert field_logs.first().field == 'mentor'


@pytest.mark.django_db
def test_reject_does_not_change_business_field(arrangement, new_mentor_user, super_user):
    """驳回只记录，不落业务字段。"""
    old_mentor_id = arrangement.mentor_id
    ap = approval_service.create_approval_request(
        arrangement=arrangement,
        change_type='MENTOR_CHANGE',
        new_user_id=new_mentor_user.pk,
        reason='原导师离职',
    )
    approval_service.reject(ap, approver=super_user, reason='人手充足')

    arrangement.refresh_from_db()
    ap.refresh_from_db()
    assert arrangement.mentor_id == old_mentor_id
    assert ap.status == 'REJECTED'
    assert ap.reject_reason == '人手充足'


@pytest.mark.django_db
def test_approve_twice_raises(arrangement, new_mentor_user, super_user):
    """已审批的单不可重复审批。"""
    ap = approval_service.create_approval_request(
        arrangement=arrangement,
        change_type='MENTOR_CHANGE',
        new_user_id=new_mentor_user.pk,
    )
    approval_service.approve(ap, approver=super_user)
    with pytest.raises(approval_service.ApprovalError):
        approval_service.approve(ap, approver=super_user)


@pytest.mark.django_db
def test_approve_with_missing_user_rolls_back(arrangement, super_user):
    """目标人员不存在 → 拒绝落字段，事务回滚，申请单状态不变。"""
    ap = approval_service.create_approval_request(
        arrangement=arrangement,
        change_type='MENTOR_CHANGE',
        new_user_id='99999999',
    )
    old_mentor_id = arrangement.mentor_id
    with pytest.raises(approval_service.ApprovalError):
        approval_service.approve(ap, approver=super_user)

    arrangement.refresh_from_db()
    ap.refresh_from_db()
    assert arrangement.mentor_id == old_mentor_id
    assert ap.status == 'PENDING'


@pytest.mark.django_db
def test_manager_change_type(arrangement, new_mentor_user, super_user):
    """MANAGER_CHANGE 落到 direct_manager 字段。"""
    ap = approval_service.create_approval_request(
        arrangement=arrangement,
        change_type='MANAGER_CHANGE',
        new_user_id=new_mentor_user.pk,
    )
    approval_service.approve(ap, approver=super_user)
    arrangement.refresh_from_db()
    assert arrangement.direct_manager_id == new_mentor_user.pk


# ──────────────────────────────────────────────────────────────
# 端点层
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_endpoint_create_then_approve(auth_client, _seed_campus_data, arrangement, new_mentor_user):
    old_mentor_id = arrangement.mentor_id

    r = auth_client.post(
        f'{BASE}/rotation-approvals/',
        {
            'arrangement': str(arrangement.id),
            'change_type': 'MENTOR_CHANGE',
            'new_value': str(new_mentor_user.pk),
            'reason': '导师调整',
        },
        format='json',
    )
    assert r.status_code == 201, r.content
    ap_id = r.json()['data']['id']
    assert r.json()['data']['status'] == 'PENDING'

    # 申请后业务字段未变
    arrangement.refresh_from_db()
    assert arrangement.mentor_id == old_mentor_id

    ap = auth_client.post(f'{BASE}/rotation-approvals/{ap_id}/approve/')
    assert ap.status_code == 200, ap.content
    assert ap.json()['data']['status'] == 'APPROVED'

    arrangement.refresh_from_db()
    assert arrangement.mentor_id == new_mentor_user.pk


@pytest.mark.django_db
def test_endpoint_reject(auth_client, _seed_campus_data, arrangement, new_mentor_user):
    old_mentor_id = arrangement.mentor_id
    r = auth_client.post(
        f'{BASE}/rotation-approvals/',
        {
            'arrangement': str(arrangement.id),
            'change_type': 'MENTOR_CHANGE',
            'new_value': str(new_mentor_user.pk),
        },
        format='json',
    )
    ap_id = r.json()['data']['id']

    rj = auth_client.post(
        f'{BASE}/rotation-approvals/{ap_id}/reject/', {'reason': '暂不调整'}, format='json',
    )
    assert rj.status_code == 200, rj.content
    assert rj.json()['data']['status'] == 'REJECTED'

    arrangement.refresh_from_db()
    assert arrangement.mentor_id == old_mentor_id


@pytest.mark.django_db
def test_endpoint_double_approve_returns_409(auth_client, _seed_campus_data, arrangement, new_mentor_user):
    r = auth_client.post(
        f'{BASE}/rotation-approvals/',
        {
            'arrangement': str(arrangement.id),
            'change_type': 'MENTOR_CHANGE',
            'new_value': str(new_mentor_user.pk),
        },
        format='json',
    )
    ap_id = r.json()['data']['id']
    assert auth_client.post(f'{BASE}/rotation-approvals/{ap_id}/approve/').status_code == 200
    again = auth_client.post(f'{BASE}/rotation-approvals/{ap_id}/approve/')
    assert again.status_code == 409, again.content


@pytest.mark.django_db
def test_endpoint_list_filters_by_status(auth_client, _seed_campus_data, arrangement, new_mentor_user):
    auth_client.post(
        f'{BASE}/rotation-approvals/',
        {
            'arrangement': str(arrangement.id),
            'change_type': 'MENTOR_CHANGE',
            'new_value': str(new_mentor_user.pk),
        },
        format='json',
    )
    pending = auth_client.get(f'{BASE}/rotation-approvals/', {'status': 'PENDING'})
    assert pending.status_code == 200, pending.content
    assert pending.json()['pagination']['total'] == 1

    approved = auth_client.get(f'{BASE}/rotation-approvals/', {'status': 'APPROVED'})
    assert approved.json()['pagination']['total'] == 0


@pytest.mark.django_db
def test_endpoint_rejects_same_value(auth_client, _seed_campus_data, arrangement):
    """新值与当前值相同 → 400，不建单。"""
    r = auth_client.post(
        f'{BASE}/rotation-approvals/',
        {
            'arrangement': str(arrangement.id),
            'change_type': 'MENTOR_CHANGE',
            'new_value': str(arrangement.mentor_id),
        },
        format='json',
    )
    assert r.status_code == 400, r.content
    assert RotationApproval.objects.count() == 0
