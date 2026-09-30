"""信封契约 — OnboardingViewSet (信封收口 Batch 7, 协调式 backend-only).

OnboardingViewSet 原 create/retrieve/update 为 DRF 默认裸返回; list 经 StandardResultsSetPagination
信封, transition @action(views.py:56) 已手写 {success,data}, perform_destroy(软删) 不动.
接入 EnvelopeWriteMixin 兜底写操作与 retrieve.

FE 影响面核查: 仅 OnboardingList.vue 调 listOnboardings(读信封, 不动) 与 transitionOnboarding
(消费已信封 transition action). 无 FE 代码直连 retrieve/create/update 裸端点 → 本批零 FE 改动.

权限: V2Permission + ScopeQuerysetMixin(is_super_admin 短路放行), 用 super_user(auth_client).
"""
import uuid
from datetime import date as _Date

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.application.models import Application
from apps.candidate.models import Candidate
from apps.core.models import Department
from apps.onboarding.models import Onboarding, OnboardingState
from apps.offer.models import Offer, OfferState
from apps.position.models import Position
from apps.process.models import RecruitmentProcess

pytestmark = pytest.mark.django_db(transaction=True)

LIST = '/api/v1/onboardings/'


def _uid(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


def _make_offer(user, candidate, position, process, application):
    """构造一条独立 Offer（OneToOne 约束, 不可复用）。绕过 create_offer 钩子, 仅供测试基座。"""
    return Offer.objects.create(
        code=_uid('OFR'),
        application=application, candidate=candidate, position=position,
        salary=10000.0,
        start_date='2026-09-15',
        expire_date='2026-10-15',
        level='L1',
        position_title='研发工程师',
        state=OfferState.SENT,
        created_by=user, updated_by=user,
    )


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
    offer = _make_offer(user, candidate, position, process, application)
    onboarding = Onboarding.objects.create(
        offer=offer, candidate=candidate, position=position,
        start_date=_Date(2026, 9, 15),
        todo_list=['t1'], todo_completed={'t1': False},
        state=OnboardingState.PENDING,
        created_by=user, updated_by=user,
    )
    return {
        'user': user, 'dept': dept, 'process': process, 'position': position,
        'candidate': candidate, 'application': application, 'offer': offer,
        'onboarding': onboarding,
    }


def test_onboarding_retrieve_envelope(auth_client, scenario):
    resp = auth_client.get(f'{LIST}{scenario["onboarding"].id}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['data']['id'] == str(scenario['onboarding'].id)


def test_onboarding_update_envelope(auth_client, scenario):
    # PATCH start_date 走 mixin.update(partial=True) → 信封.
    resp = auth_client.patch(
        f'{LIST}{scenario["onboarding"].id}/',
        {'start_date': '2026-10-01'}, format='json')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    # Onboarding.state 是 FSMField(protected=True), refresh_from_db 会触发
    # "Direct state modification is not allowed"; 改为从响应信封断言更新后字段.
    assert resp.data['data']['start_date'] == '2026-10-01'


def test_onboarding_list_envelope(auth_client, scenario):
    resp = auth_client.get(LIST)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert isinstance(resp.data['data'], list)


def test_onboarding_create_envelope(auth_client, scenario):
    # Onboarding.offer 是 OneToOne, 须独立 Offer(复用 scenario.offer 会撞唯一约束).
    User = get_user_model()
    user = scenario['user']
    application = Application.objects.create(
        code=_uid('APP2'), candidate=scenario['candidate'],
        position=scenario['position'], process=scenario['process'],
        workflow_version='V1.0',
    )
    offer = _make_offer(user, scenario['candidate'], scenario['position'],
                       scenario['process'], application)
    payload = {
        'offer': str(offer.id),
        'candidate': str(scenario['candidate'].id),
        'position': str(scenario['position'].id),
        'start_date': '2026-09-20',
    }
    before = Onboarding.objects.count()
    resp = auth_client.post(LIST, payload, format='json')
    assert resp.status_code == 201
    assert resp.data['success'] is True
    assert 'data' in resp.data
    assert Onboarding.objects.count() == before + 1
