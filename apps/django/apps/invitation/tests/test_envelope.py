"""信封契约 — InvitationViewSet (信封收口 Batch 6, 协调式 backend+FE).

InvitationViewSet 原 create/retrieve/update 为 DRF 默认裸返回; list 经 StandardResultsSetPagination
信封, transition/grab-pool/claimable/process-expired/grab @action 已信封. 接入 EnvelopeWriteMixin
兜底写操作与 retrieve. 权限: V2Permission + ScopeQuerysetMixin(is_super_admin 短路放行),
用 super_user(auth_client).
"""
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.application.models import Application
from apps.candidate.models import Candidate
from apps.core.models import Department
from apps.invitation.models import Invitation
from apps.position.models import Position
from apps.process.models import RecruitmentProcess

pytestmark = pytest.mark.django_db(transaction=True)

LIST = '/api/v1/invitations/'


def _uid(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


@pytest.fixture
def scenario(db):
    User = get_user_model()
    user = User.objects.create_user(username=_uid('hr'), password='Test@1234')
    dept = Department.objects.create(id=_uid('dept'), name='信封BG', code=_uid('NED'))
    process = RecruitmentProcess.objects.create(
        code=_uid('PROC'), name='信封流程', current_version='V1.0',
        version_seq=1, is_latest=True,
    )
    position = Position.objects.create(
        code=_uid('POS'), title='信封职位', department=dept,
        hiring_manager=user, owner=user, process=process,
    )
    candidate = Candidate.objects.create(
        name='信封候选人', phone=_uid('138'),
        gender='男', school_tag='985', major_tag='工学',
    )
    application = Application.objects.create(
        code=_uid('APP'), candidate=candidate, position=position,
        process=process, workflow_version='V1.0',
    )
    invitation = Invitation.objects.create(
        application=application, inviter=user,
        expire_at=timezone.now() + timedelta(days=90),
        state='PENDING', created_by=user, updated_by=user,
    )
    return {
        'user': user, 'dept': dept, 'process': process, 'position': position,
        'candidate': candidate, 'application': application, 'invitation': invitation,
    }


def test_invitation_retrieve_envelope(auth_client, scenario):
    resp = auth_client.get(f'{LIST}{scenario["invitation"].id}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert 'data' in resp.data


def test_invitation_update_envelope(auth_client, scenario):
    resp = auth_client.patch(
        f'{LIST}{scenario["invitation"].id}/', {'is_grab_pool': True}, format='json')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    # Invitation.state 是 FSMField, refresh_from_db 会触发 "Direct state modification" 报错;
    # 改为直接断言信封响应里的更新后字段.
    assert resp.data['data']['is_grab_pool'] is True


def test_invitation_list_envelope(auth_client, scenario):
    resp = auth_client.get(LIST)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert isinstance(resp.data['data'], list)


def test_invitation_create_envelope(auth_client, scenario):
    # Invitation.application 是 FK(非 OneToOne), 可复用 scenario 的 application.
    payload = {
        'application': str(scenario['application'].id),
        'inviter': str(scenario['user'].id),
        'expire_at': (timezone.now() + timedelta(days=120)).isoformat(),
    }
    before = Invitation.objects.count()
    resp = auth_client.post(LIST, payload, format='json')
    assert resp.status_code == 201
    assert resp.data['success'] is True
    assert 'data' in resp.data
    assert Invitation.objects.count() == before + 1
