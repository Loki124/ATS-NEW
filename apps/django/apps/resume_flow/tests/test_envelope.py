"""信封契约 — ApprovalFlowViewSet (信封收口 Batch 10, 后端-only).

ApprovalFlowViewSet 加 EnvelopeReadOnlyMixin(retrieve 信封) + 手信封 update/partial_update;
自定义 create (写入 ApprovalFlowHistory) 与 @action approve/reject/delegate 已手动信封, 保留.

FE 影响面核查: web/app/src 仅 SpecialApproval.vue 调用 list(/resumes/approval-flows) 与
approve 动作; 不调用 retrieve/create/update → 本次信封化零 FE 影响.
(端点前缀 /api/v1/resumes/approval-flows/, 非此前误判的 /api/v1/approval-flows/)

权限: V2Permission, auth_client=super_user 经 is_super_admin 短路.
"""
import uuid

import pytest
from rest_framework.test import APIClient

from apps.candidate.models import Candidate
from apps.resume_flow.models import ApprovalFlow

pytestmark = pytest.mark.django_db

FLOW_LIST = '/api/v1/resumes/approval-flows/'


def _uid(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


def _make_candidate() -> Candidate:
    return Candidate.objects.create(
        id=_uid('cand'), name='审批流信封候选人', phone='13800000003',
    )


def _make_flow(candidate: Candidate, user) -> ApprovalFlow:
    return ApprovalFlow.objects.create(
        candidate=candidate,
        resume_id='resume-env-001',
        status='PENDING',
        nodes=[],
        created_by=user,
    )


def test_flow_list_envelope(auth_client):
    resp = auth_client.get(FLOW_LIST)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert isinstance(resp.data['data'], list)
    assert 'pagination' in resp.data


def test_flow_retrieve_envelope(auth_client, super_user):
    candidate = _make_candidate()
    flow = _make_flow(candidate, super_user)
    resp = auth_client.get(f'{FLOW_LIST}{flow.id}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['data']['id'] == str(flow.id)


def test_flow_update_envelope(auth_client, super_user):
    candidate = _make_candidate()
    flow = _make_flow(candidate, super_user)
    resp = auth_client.patch(
        f'{FLOW_LIST}{flow.id}/', {'resume_id': 'resume-env-002'}, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.data['success'] is True
    assert resp.data['data']['resume_id'] == 'resume-env-002'


def test_flow_create_envelope(auth_client):
    """create 写 ApprovalFlowHistory(CREATED), 自定义返回 {success, data}."""
    candidate = _make_candidate()
    resp = auth_client.post(FLOW_LIST, {
        'candidate': str(candidate.id),
        'resume_id': 'resume-env-003',
        'nodes': [
            {'nodeId': 'n1', 'role': 'HRBP'},
            {'nodeId': 'n2', 'role': 'HIRING_MANAGER'},
        ],
    }, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.data['success'] is True
    assert resp.data['code'] == 0, resp.data   # 黄金标准: 缺 code 即半信封未收口
    assert resp.data['data']['id']
    assert resp.data['data']['status'] == 'PENDING'
