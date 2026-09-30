"""announcement 信封契约: create(201)/update(200)/retrieve(200)/list 均含 {success,data,code}.

注: AnnouncementViewSet 原手写 {success,data} 半信封, 本次收敛到 success_response 补齐 code;
所有 success 分支(含 @action)统一带 code, 错误分支(Response({'detail':...}) / success:False)保持不变.
"""
import pytest

from apps.announcement.models import Announcement


def _assert_envelope(body, code=0):
    assert body.get('success') is True
    assert 'data' in body
    assert body.get('code') == code


@pytest.mark.django_db
def test_announcement_list(auth_client):
    Announcement.objects.create(
        title='L1', category='SYSTEM', audience='RECRUIT_EXPERT', body='b', is_active=True)
    resp = auth_client.get('/api/v1/announcements/')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
    assert isinstance(resp.json()['data'], list)


@pytest.mark.django_db
def test_announcement_create_retrieve_update(auth_client):
    resp = auth_client.post('/api/v1/announcements/', {
        'title': '信封测试', 'category': 'SYSTEM', 'audience': 'RECRUIT_EXPERT', 'body': '正文',
    }, format='json')
    assert resp.status_code == 201
    _assert_envelope(resp.json())
    pk = resp.json()['data']['id']
    assert resp.json()['data']['title'] == '信封测试'

    resp = auth_client.get(f'/api/v1/announcements/{pk}/')
    assert resp.status_code == 200
    _assert_envelope(resp.json())

    resp = auth_client.patch(f'/api/v1/announcements/{pk}/', {'is_active': False}, format='json')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
    assert resp.json()['data']['isActive'] is False


@pytest.mark.django_db
def test_announcement_config_envelope(auth_client):
    """config @action 也经 success_response 带 code."""
    resp = auth_client.get('/api/v1/announcements/config/')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
