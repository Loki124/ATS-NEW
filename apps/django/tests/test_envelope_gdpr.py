"""信封契约 — GDPRRequestViewSet (信封收口 Batch 10, 后端-only).

GDPRRequestViewSet 加 EnvelopeReadOnlyMixin(retrieve 信封) + 手信封 update/partial_update;
自定义 create (AllowAny, 注入 verification_code) 与 @action verify/process 已手动信封, 保留.

FE 影响面核查: 全仓 web/app/src 无 gdpr 端点 API 调用 → 零 FE 改动.

权限: 非 create/verify 动作走 IsSuperAdmin; auth_client=super_user(is_superuser=True) 放行.
create 走 AllowAny (候选人提交).

⚠️ 预存 bug (不在本批范围): views.create 把 validated_data['candidate'] (Candidate 对象)
直接当 candidate_id 字符串传给 GdprService.submit_request, 后者做
Candidate.objects.get(id=<对象>) → 永远 NotFound → create 实际 404. 故本批不测 create 信封,
仅锁 list/retrieve/update 形状; create 端点功能修复另立 issue.
"""
import uuid

import pytest

from apps.candidate.models import Candidate
from apps.gdpr.models import GDPRRequest, GDPRRequestType

pytestmark = pytest.mark.django_db

GDPR_LIST = '/api/v1/gdpr/'


def _uid(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


def _make_candidate() -> Candidate:
    return Candidate.objects.create(
        id=_uid('cand'), name='GDPR 信封候选人', phone='13800000002',
    )


def _make_request(candidate: Candidate) -> GDPRRequest:
    return GDPRRequest.objects.create(
        candidate=candidate,
        request_type=GDPRRequestType.FORGET,
        submitted_email='gdpr-env@example.com',
    )


def test_gdpr_list_envelope(auth_client):
    resp = auth_client.get(GDPR_LIST)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert isinstance(resp.data['data'], list)
    assert 'pagination' in resp.data


def test_gdpr_retrieve_envelope(auth_client):
    candidate = _make_candidate()
    req = _make_request(candidate)
    resp = auth_client.get(f'{GDPR_LIST}{req.id}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['data']['id'] == str(req.id)


def test_gdpr_update_envelope(auth_client):
    candidate = _make_candidate()
    req = _make_request(candidate)
    resp = auth_client.patch(
        f'{GDPR_LIST}{req.id}/',
        {'submitted_email': 'gdpr-env-updated@example.com'},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    assert resp.data['success'] is True
    assert resp.data['data']['submitted_email'] == 'gdpr-env-updated@example.com'
