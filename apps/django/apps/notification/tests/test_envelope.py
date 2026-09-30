"""notification 信封契约: 经 EnvelopeWriteMixin, create(201)/update(200)/retrieve(200) 包 {success,data,code}.

NotificationTemplate 此前为裸 DRF 默认(ModelViewSet 无自定义 create/update/retrieve),
返回裸 serializer.data; 本次套 EnvelopeWriteMixin 收口. list 由 StandardResultsSetPagination 信封.
无 FE 消费方(纯后端), 仅校验契约.
"""
import pytest

from apps.notification.models import NotificationTemplate


def _assert_envelope(body, code=0):
    assert body.get('success') is True
    assert 'data' in body
    assert body.get('code') == code


@pytest.mark.django_db
def test_notification_template_list(auth_client):
    NotificationTemplate.objects.create(code='NT-LIST-001', name='T', event='evt')
    resp = auth_client.get('/api/v1/notifications/')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
    assert isinstance(resp.json()['data'], list)


@pytest.mark.django_db
def test_notification_template_create_retrieve_update(auth_client):
    resp = auth_client.post('/api/v1/notifications/', {
        'code': 'NT-CU-001', 'name': '模板', 'event': 'offer.sent',
    }, format='json')
    assert resp.status_code == 201
    _assert_envelope(resp.json())
    pk = resp.json()['data']['id']
    assert resp.json()['data']['code'] == 'NT-CU-001'

    resp = auth_client.get(f'/api/v1/notifications/{pk}/')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
    assert resp.json()['data']['code'] == 'NT-CU-001'

    resp = auth_client.patch(f'/api/v1/notifications/{pk}/', {'name': '改后名称'}, format='json')
    assert resp.status_code == 200
    _assert_envelope(resp.json())
    assert resp.json()['data']['name'] == '改后名称'
