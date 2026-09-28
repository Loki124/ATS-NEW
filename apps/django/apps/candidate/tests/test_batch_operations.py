"""candidate_batch_* 真实后端测试（替代 501 stub，闭环 P0-3 治理迁移）

覆盖 G9 PRD 五个候选人维度批量端点：
- batch/recommend/  → CandidatePositionRecommendation
- batch/archive/    → Candidate.is_archived 软标志
- batch/assign/     → Candidate.recruiter
- batch/screen/     → CandidateScreening
- batch/export/     → CSV blob
"""
import pytest
from rest_framework.test import APIClient

from apps.candidate.models import (
    Candidate,
    CandidateScreening,
    CandidatePositionRecommendation,
)
from apps.position.models import Position
from apps.core.models import Department
from apps.process.models import RecruitmentProcess


@pytest.mark.django_db
class TestCandidateBatchOperations:
    @pytest.fixture
    def api_client(self, hr_user):
        c = APIClient()
        c.force_authenticate(user=hr_user)
        return c

    @pytest.fixture
    def a_position(self, hr_user):
        dept = Department.objects.create(code='D-BATCH', name='批量测试部门')
        proc = RecruitmentProcess.objects.create(
            id='proc-batch-1', code='PBPROC', name='批量测试流程', current_version='V1.0',
        )
        return Position.objects.create(
            id='pos-batch-1', code='PB001', title='批量测试职位',
            department=dept, hiring_manager=hr_user, owner=hr_user,
            process=proc, recruit_type='social',
        )

    def test_batch_recommend_creates_records(self, api_client, hr_user, a_position):
        c1 = Candidate.objects.create(id='cb-rec-1', name='推荐A', phone='13800000001', recruit_type='social')
        resp = api_client.post('/api/v1/candidates/batch/recommend/', {
            'candidate_ids': [c1.id], 'position_id': a_position.id, 'comment': '匹配度高',
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['success'] is True
        assert resp.json()['data']['results'][0]['success'] is True
        rec = CandidatePositionRecommendation.objects.get(candidate=c1, position=a_position)
        assert rec.recommender == hr_user
        assert rec.reason == '匹配度高'

    def test_batch_archive_sets_flag(self, api_client, hr_user):
        c1 = Candidate.objects.create(id='cb-arc-1', name='归档A', phone='13800000002', recruit_type='social')
        resp = api_client.post('/api/v1/candidates/batch/archive/', {
            'candidate_ids': [c1.id],
        }, format='json')
        assert resp.status_code == 200
        c1.refresh_from_db()
        assert c1.is_archived is True
        assert c1.archived_at is not None

    def test_batch_assign_sets_recruiter(self, api_client, hr_user):
        c1 = Candidate.objects.create(id='cb-asn-1', name='分配A', phone='13800000003', recruit_type='social')
        resp = api_client.post('/api/v1/candidates/batch/assign/', {
            'candidate_ids': [c1.id], 'recruiter_id': hr_user.id,
        }, format='json')
        assert resp.status_code == 200
        c1.refresh_from_db()
        assert c1.recruiter_id == hr_user.id

    def test_batch_screen_creates_records(self, api_client, hr_user):
        c1 = Candidate.objects.create(id='cb-scr-1', name='初筛A', phone='13800000004', recruit_type='social')
        resp = api_client.post('/api/v1/candidates/batch/screen/', {
            'candidate_ids': [c1.id], 'result': 'PASS', 'comment': 'ok',
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['data']['results'][0]['success'] is True
        scr = CandidateScreening.objects.get(candidate=c1)
        assert scr.result == 'PASS'
        assert scr.screener == hr_user

    def test_batch_export_returns_csv(self, api_client, hr_user):
        Candidate.objects.create(id='cb-exp-1', name='导出A', phone='13800000005', recruit_type='social')
        resp = api_client.post('/api/v1/candidates/batch/export/', {
            'candidate_ids': ['cb-exp-1'],
        }, format='json')
        assert resp.status_code == 200
        assert resp['Content-Type'].startswith('text/csv')
        body = resp.content.decode('utf-8-sig')
        assert '导出A' in body
