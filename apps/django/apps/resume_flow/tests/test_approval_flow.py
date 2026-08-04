"""审批流测试 — create / list / transition"""
import pytest
from rest_framework.test import APIClient

from apps.candidate.models import Candidate
from apps.resume_flow.models import ApprovalFlow, ApprovalFlowHistory


@pytest.mark.django_db
class TestApprovalFlow:
    """审批流 CRUD + transition 测试"""

    @pytest.fixture
    def api_client(self, hr_user):
        """带认证的 API 客户端"""
        client = APIClient()
        client.force_authenticate(user=hr_user)
        return client

    @pytest.fixture
    def a_candidate(self, db):
        """测试用候选人"""
        return Candidate.objects.create(
            id='cand-approval-001',
            name='审批测试候选人',
            phone='13800000999',
        )

    def test_create_approval_flow(self, api_client, hr_user, a_candidate):
        """创建审批流 → 201 + status=PENDING + history(CREATED)"""
        url = '/api/v1/resumes/approval-flows/'
        payload = {
            'candidate': a_candidate.id,
            'resume_id': 'resume-001',
            'nodes': [
                {'nodeId': 'n1', 'role': 'HRBP'},
                {'nodeId': 'n2', 'role': 'HIRING_MANAGER'},
            ],
        }
        resp = api_client.post(url, payload, format='json')

        assert resp.status_code == 201
        payload = resp.json()
        data = payload['data']
        assert data['status'] == 'PENDING'
        # CamelCaseJSONRenderer: current_node_id → currentNodeId
        assert data['currentNodeId'] == 'n1'
        assert len(data['nodes']) == 2

        # 验证 history 写入
        flow = ApprovalFlow.objects.get(id=data['id'])
        assert flow.histories.count() == 1
        assert flow.histories.first().action == 'CREATED'

    def test_list_approval_flows(self, api_client, hr_user, a_candidate):
        """列表 → 200 + 包含已创建的审批流"""
        flow = ApprovalFlow.objects.create(
            candidate=a_candidate,
            resume_id='resume-002',
            status='PENDING',
            current_node_id='n1',
            nodes=[{'nodeId': 'n1', 'role': 'HRBP'}],
            created_by=hr_user,
        )

        url = '/api/v1/resumes/approval-flows/'
        resp = api_client.get(url)

        assert resp.status_code == 200
        payload = resp.json()
        # StandardResultsSetPagination: {success, data: [...], pagination: {total, ...}}
        assert payload['success'] is True
        assert payload['pagination']['total'] >= 1
        ids = [item['id'] for item in payload['data']]
        assert flow.id in ids

    def test_transition_approve(self, api_client, hr_user, a_candidate):
        """批准 → status=APPROVED（单节点流）"""
        flow = ApprovalFlow.objects.create(
            candidate=a_candidate,
            resume_id='resume-003',
            status='PENDING',
            current_node_id='n1',
            nodes=[{'nodeId': 'n1', 'role': 'HRBP'}],
            created_by=hr_user,
        )
        ApprovalFlowHistory.objects.create(
            flow=flow, action='CREATED',
            from_node='', to_node='n1',
            operated_by=hr_user, comment='创建',
        )

        url = f'/api/v1/resumes/approval-flows/{flow.id}/approve/'
        resp = api_client.post(url, {
            'node_id': 'n1',
            'comment': '同意录用',
        }, format='json')

        assert resp.status_code == 200
        payload = resp.json()
        data = payload['data']
        assert data['status'] == 'APPROVED'
        # CamelCaseJSONRenderer: current_node_id → currentNodeId
        assert data['currentNodeId'] == ''

        flow.refresh_from_db()
        assert flow.histories.count() == 2
        last_history = flow.histories.first()
        assert last_history.action == 'APPROVED'
