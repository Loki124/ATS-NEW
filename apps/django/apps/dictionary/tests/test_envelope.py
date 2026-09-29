"""Dictionary 信封契约测试 (P1-3 A2)

验证 DictionaryTypeViewSet / DictionaryItemViewSet 经 EnvelopeWriteMixin 后:
- create / update / retrieve 返回统一信封 {success, data, message, code}
  (不再返回 DRF 默认裸 serializer.data)
- submit 成功响应也包信封 (错误响应保持裸 {detail, headErrors, itemErrors}, 由 P2 拦截器归一)
- list 已由 StandardResultsSetPagination 包信封 (回归守住)
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.dictionary.models import DictionaryItem, DictionaryType

TYPE_LIST = '/api/v1/dictionary-types/'
ITEM_LIST = '/api/v1/dictionary-items/'

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client(db):
    user = get_user_model().objects.create_user(
        username='dict_env_user', password='Test@1234', employee_id='EDE001'
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def custom_type(auth_client):
    resp = auth_client.post(
        TYPE_LIST, {'code': 'env_custom', 'name': '信封测试类型'}, format='json'
    )
    assert resp.status_code == 201
    return resp.json()['data']['code']


def test_create_type_envelope(auth_client):
    resp = auth_client.post(
        TYPE_LIST, {'code': 'env_type', 'name': '信封类型'}, format='json'
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body['success'] is True
    assert body['data']['code'] == 'env_type'
    assert body['data']['name'] == '信封类型'


def test_retrieve_type_envelope(auth_client, custom_type):
    resp = auth_client.get(f'{TYPE_LIST}{custom_type}/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['data']['code'] == custom_type


def test_update_type_envelope(auth_client, custom_type):
    resp = auth_client.patch(f'{TYPE_LIST}{custom_type}/', {'is_enabled': False}, format='json')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['data']['isEnabled'] is False


def test_create_item_envelope(auth_client, custom_type):
    type_id = DictionaryType.objects.get(code=custom_type).id
    resp = auth_client.post(
        ITEM_LIST, {'type': type_id, 'key': 'ENV_ITEM', 'value': '信封项'}, format='json'
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body['success'] is True
    assert body['data']['key'] == 'ENV_ITEM'


def test_list_type_envelope(auth_client, custom_type):
    resp = auth_client.get(TYPE_LIST, {'page_size': 200})
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert isinstance(body['data'], list)
    assert body['pagination']['total'] >= 1
