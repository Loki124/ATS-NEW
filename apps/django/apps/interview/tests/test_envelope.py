"""Interview 信封契约测试 (P1-3 A2)

验证 InterviewViewSet / InterviewEvaluationViewSet 经 EnvelopeWriteMixin 后:
- retrieve / create / update 返回统一信封 {success, data, message, code}
  (不再返回 DRF 默认裸 serializer.data)
- list 已由 StandardResultsSetPagination 包信封 (回归守住)

鉴权用全局 auth_client (super_user, 可过 IsHROrAbove / V2Permission)。
"""
import datetime

import pytest
from rest_framework.test import APIClient

from apps.core.models import Department, User
from apps.process.models import RecruitmentProcess, RecruitmentStage, ProcessStageLink
from apps.candidate.models import Candidate
from apps.position.models import Position
from apps.application.models import Application, ApplicationStageRecord
from apps.interview.models import Interview, InterviewEvaluation


@pytest.fixture
def interviewer(db):
    return User.objects.create_user(username='eval_interviewer', password='pw123456')


@pytest.fixture
def interview(db):
    dept = Department.objects.create(name='面试研发部', code='rd_int', path='/面试研发部')
    process = RecruitmentProcess.objects.create(code='WINT01', name='标准流程')
    rec = RecruitmentStage.objects.create(code='PTINT01', name='简历筛选', stage_type='SCREEN')
    link = ProcessStageLink.objects.create(process=process, stage=rec)
    candidate = Candidate.objects.create(name='面试候选人', phone='13800000000', email='iv@example.com')
    user = User.objects.create_user(username='iv_owner', password='pw123456')
    position = Position.objects.create(
        code='POSINT01', title='后端工程师', department=dept,
        hiring_manager=user, owner=user, process=process,
    )
    application = Application.objects.create(
        code='APPINT01', candidate=candidate, position=position,
        process=process, workflow_version='V1.0',
    )
    stage_record = ApplicationStageRecord.objects.create(
        application=application, link=link, stage=link.stage,
    )
    return Interview.objects.create(
        code='INT001',
        application=application,
        stage_record=stage_record,
        scheduled_at=datetime.datetime(2026, 8, 20, 10, 0, 0, tzinfo=datetime.timezone.utc),
    )


def _make_evaluation(interview, interviewer):
    return InterviewEvaluation.objects.create(
        interview=interview,
        interviewer=interviewer,
        scores={'专业能力': 4},
        overall_score=4.0,
        recommendation='RECOMMEND',
        comment='表现不错',
        meta_json={},
    )


def test_interview_retrieve_envelope(auth_client, interview):
    """InterviewViewSet.retrieve 须包信封 (EnvelopeWriteMixin)。"""
    resp = auth_client.get(f'/api/v1/interviews/{interview.id}/')
    assert resp.status_code == 200
    body = resp.data
    assert body['success'] is True
    assert body['data']['id'] == str(interview.id)
    assert body['data']['code'] == 'INT001'


def test_interview_list_envelope(auth_client, interview):
    """list 已由 StandardResultsSetPagination 包信封 (回归守住)。"""
    resp = auth_client.get('/api/v1/interviews/')
    assert resp.status_code == 200
    body = resp.data
    assert body['success'] is True
    assert isinstance(body['data'], list)
    assert body['pagination']['total'] >= 1


def test_evaluation_create_envelope(auth_client, interview, interviewer):
    """InterviewEvaluationViewSet.create 须包信封 (EnvelopeWriteMixin, 201)。"""
    payload = {
        'interview': str(interview.id),
        'interviewer': str(interviewer.id),
        'scores': {'专业能力': 4},
        'overall_score': 4.0,
        'recommendation': 'RECOMMEND',
        'comment': '表现不错',
        'meta_json': {},
    }
    resp = auth_client.post('/api/v1/interviews/evaluations/', data=payload, format='json')
    assert resp.status_code == 201
    body = resp.data
    assert body['success'] is True
    assert 'id' in body['data']
    assert body['data']['recommendation'] == 'RECOMMEND'


def test_evaluation_retrieve_envelope(auth_client, interview, interviewer):
    """InterviewEvaluationViewSet.retrieve 须包信封。"""
    evaluation = _make_evaluation(interview, interviewer)
    resp = auth_client.get(f'/api/v1/interviews/evaluations/{evaluation.id}/')
    assert resp.status_code == 200
    body = resp.data
    assert body['success'] is True
    assert body['data']['id'] == str(evaluation.id)


def test_evaluation_update_envelope(auth_client, interview, interviewer):
    """InterviewEvaluationViewSet.partial_update 须包信封。"""
    evaluation = _make_evaluation(interview, interviewer)
    resp = auth_client.patch(
        f'/api/v1/interviews/evaluations/{evaluation.id}/',
        data={'comment': '更新评语'}, format='json',
    )
    assert resp.status_code == 200
    body = resp.data
    assert body['success'] is True
    assert body['data']['comment'] == '更新评语'
