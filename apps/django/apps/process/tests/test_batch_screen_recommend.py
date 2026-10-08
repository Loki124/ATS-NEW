"""batch/screen + batch/recommend 真实现测试"""
import pytest
from rest_framework.test import APIClient

from apps.candidate.models import Candidate
from apps.process.models import CandidateRecommendation, CandidateScreen


@pytest.mark.django_db
class TestBatchScreenRecommend:
    """批量筛选 + 批量推荐 测试"""

    @pytest.fixture
    def api_client(self, hr_user):
        client = APIClient()
        client.force_authenticate(user=hr_user)
        return client

    @pytest.fixture
    def a_process(self, db):
        """测试用的招聘流程"""
        from apps.process.models import RecruitmentProcess
        return RecruitmentProcess.objects.create(
            id='proc-batch-test',
            code='BATCH_TEST',
            name='批量操作测试流程',
            current_version='1.0',
            is_template=False,
            is_enabled=True,
            is_latest=True,  # T1：is_latest 默认 False，依赖 is_latest=True 过滤的查询会落空
        )

    @pytest.fixture
    def a_candidate(self, db):
        """测试用候选人"""
        return Candidate.objects.create(
            id='cand-screen-001',
            name='筛选测试候选人',
            phone='13800000998',
        )

    def test_batch_screen_creates_records(
        self, api_client, hr_user, a_process, a_candidate,
    ):
        """batch-screen → 200 + CandidateScreen 记录写入"""
        cand2 = Candidate.objects.create(
            id='cand-screen-002', name='李四', phone='13900000002',
        )

        url = f'/api/v1/processes/{a_process.id}/batch-screen/'
        resp = api_client.post(url, {
            'candidate_ids': [a_candidate.id, cand2.id],
            'decision': 'PASS',
            'comment': '初筛通过',
        }, format='json')

        assert resp.status_code == 200
        payload = resp.json()
        results = payload['data']['results']
        assert len(results) == 2
        assert all(r['success'] for r in results)
        assert all(r['result'] == 'PASS' for r in results)
        # CamelCaseJSONRenderer: screen_id → screenId
        assert all('screenId' in r for r in results)

        # 验证 DB 写入
        screens = CandidateScreen.objects.filter(process=a_process)
        assert screens.count() == 2
        for s in screens:
            assert s.screen_result['decision'] == 'PASS'
            assert s.screened_by == hr_user

    def test_batch_recommend_creates_records(
        self, api_client, hr_user, a_process, a_candidate,
    ):
        """batch-recommend → 200 + CandidateRecommendation 记录写入"""
        url = f'/api/v1/processes/{a_process.id}/batch-recommend/'
        resp = api_client.post(url, {
            'candidate_ids': [a_candidate.id],
            'reason': '技术栈高度匹配，推荐面试',
        }, format='json')

        assert resp.status_code == 200
        payload = resp.json()
        results = payload['data']['results']
        assert len(results) == 1
        assert results[0]['success'] is True
        # CamelCaseJSONRenderer: recommendation_id → recommendationId
        rec_id = results[0]['recommendationId']
        assert rec_id is not None

        # 验证 DB 写入
        rec = CandidateRecommendation.objects.get(id=rec_id)
        assert rec.candidate == a_candidate
        assert rec.process == a_process
        assert rec.recommender == hr_user
        assert '技术栈高度匹配' in rec.reason
