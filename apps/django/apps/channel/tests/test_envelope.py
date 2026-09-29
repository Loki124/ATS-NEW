"""Channel 信封契约测试 (P1-3 A2)

验证 ChannelViewSet / ChannelCostViewSet 经 EnvelopeWriteMixin 后:
- create / update / retrieve 返回统一信封 {success, data, message, code}
  (不再返回 DRF 默认裸 serializer.data)
- list 已由 StandardResultsSetPagination 包信封 (回归守住)

鉴权用全局 auth_client (super_user, 可过 IsHROrAbove / V2Permission)。
"""
import pytest

from apps.channel.models import Channel, ChannelCost

CHANNEL_LIST = '/api/v1/channels/'
COST_LIST = '/api/v1/channels/costs/'

pytestmark = pytest.mark.django_db


@pytest.fixture
def channel(auth_client):
    resp = auth_client.post(
        CHANNEL_LIST,
        {'name': '信封测试渠道', 'code': 'ENV_CH', 'category': 'SOCIAL'},
        format='json',
    )
    assert resp.status_code == 201
    return Channel.objects.get(code='ENV_CH')


def test_create_channel_envelope(auth_client):
    resp = auth_client.post(
        CHANNEL_LIST,
        {'name': '新建渠道', 'code': 'ENV_NEW', 'category': 'CAMPUS'},
        format='json',
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body['success'] is True
    assert body['data']['code'] == 'ENV_NEW'
    assert body['data']['name'] == '新建渠道'
    assert body['data']['category'] == 'CAMPUS'


def test_retrieve_channel_envelope(auth_client, channel):
    resp = auth_client.get(f'{CHANNEL_LIST}{channel.id}/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['data']['id'] == str(channel.id)
    assert body['data']['code'] == 'ENV_CH'


def test_update_channel_envelope(auth_client, channel):
    resp = auth_client.patch(
        f'{CHANNEL_LIST}{channel.id}/', {'is_active': False}, format='json'
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['data']['isActive'] is False


def test_list_channel_envelope(auth_client, channel):
    resp = auth_client.get(CHANNEL_LIST, {'page_size': 200})
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert isinstance(body['data'], list)
    assert body['pagination']['total'] >= 1


def test_create_cost_envelope(auth_client, channel):
    resp = auth_client.post(
        COST_LIST,
        {
            'channel': str(channel.id),
            'amount': '1200.00',
            'cost_type': 'BOOTH',
            'incurred_at': '2026-09-20',
        },
        format='json',
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body['success'] is True
    assert body['data']['amount'] == '1200.00'
    assert body['data']['costType'] == 'BOOTH'


def test_retrieve_cost_envelope(auth_client, channel):
    cost = ChannelCost.objects.create(
        channel=channel, amount='800.00', cost_type='POSTER',
        incurred_at='2026-09-21',
    )
    resp = auth_client.get(f'{COST_LIST}{cost.id}/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['data']['id'] == str(cost.id)
    assert body['data']['amount'] == '800.00'
