"""Candidate app 测试"""
import pytest

from apps.candidate.models import Candidate, CandidateState


@pytest.fixture
def candidates(db, department):
    return [
        Candidate.objects.create(
            id=f'cand-{i:03d}',
            name=f'候选人{i}',
            phone=f'1380000{i:04d}',
            email=f'cand{i}@example.com',
        )
        for i in range(5)
    ]


@pytest.mark.django_db
class TestCandidateAPI:
    def test_list_candidates(self, auth_hr_client, candidates):
        response = auth_hr_client.get('/api/v1/candidates/candidates/')
        assert response.status_code == 200
        assert response.data['success'] is True
        assert len(response.data['data']['results']) == 5

    def test_candidate_pagination(self, auth_hr_client, candidates):
        response = auth_hr_client.get('/api/v1/candidates/candidates/?page_size=2')
        assert response.status_code == 200
        assert len(response.data['data']['results']) == 2
        assert response.data['data']['pagination']['total'] == 5

    def test_search_candidate_by_name(self, auth_hr_client, candidates):
        response = auth_hr_client.get('/api/v1/candidates/candidates/?search=候选人2')
        assert response.status_code == 200
        names = [c['name'] for c in response.data['data']['results']]
        assert '候选人2' in names

    def test_unauth_returns_401(self, api_client):
        response = api_client.get('/api/v1/candidates/candidates/')
        assert response.status_code == 401
