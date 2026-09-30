"""信封契约 — OfferViewSet (信封收口 Batch 4, 协调式 backend+FE).

OfferViewSet 原 create/retrieve/update 为 DRF 默认裸返回; list 经 StandardResultsSetPagination
信封, transition @action 已信封. 接入 EnvelopeWriteMixin 兜底写操作与 retrieve.
权限: V2Permission + ScopeQuerysetMixin(is_super_admin 短路放行), 用 super_user(auth_client).
"""
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.application.models import Application
from apps.candidate.models import Candidate
from apps.core.models import Department
from apps.offer.models import Offer
from apps.position.models import Position
from apps.process.models import RecruitmentProcess

pytestmark = pytest.mark.django_db(transaction=True)

LIST = '/api/v1/offers/'


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
    offer = Offer.objects.create(
        code=_uid('OFR'),
        application=application, candidate=candidate, position=position,
        salary=10000.0, start_date='2026-08-15', expire_date='2026-09-15',
        level='L1', position_title='研发工程师',
        state='DRAFT', created_by=user, updated_by=user,
    )
    return {
        'user': user, 'dept': dept, 'process': process, 'position': position,
        'candidate': candidate, 'application': application, 'offer': offer,
    }


def test_offer_retrieve_envelope(auth_client, scenario):
    resp = auth_client.get(f'{LIST}{scenario["offer"].id}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert 'data' in resp.data


def test_offer_update_envelope(auth_client, scenario):
    resp = auth_client.patch(
        f'{LIST}{scenario["offer"].id}/', {'position_title': '高级研发工程师'}, format='json')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    scenario['offer'].refresh_from_db()
    assert scenario['offer'].position_title == '高级研发工程师'


def test_offer_list_envelope(auth_client, scenario):
    resp = auth_client.get(LIST)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert isinstance(resp.data['data'], list)


def test_offer_create_envelope(auth_client, scenario):
    # Application 与 Offer 是 OneToOne, 新建 Offer 需独立的 Application.
    new_app = Application.objects.create(
        code=_uid('APP2'), candidate=scenario['candidate'],
        position=scenario['position'], process=scenario['process'],
        workflow_version='V1.0',
    )
    payload = {
        'application': str(new_app.id),
        'candidate': str(scenario['candidate'].id),
        'position': str(scenario['position'].id),
        'code': _uid('OFRN'),
        'salary': 12000.0,
        'level': 'L2',
        'position_title': '新研发工程师',
        'start_date': '2026-10-01',
        'expire_date': '2026-11-01',
    }
    before = Offer.objects.count()
    resp = auth_client.post(LIST, payload, format='json')
    assert resp.status_code == 201
    assert resp.data['success'] is True
    assert 'data' in resp.data
    assert Offer.objects.count() == before + 1
