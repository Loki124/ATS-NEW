"""Metrics 信封契约测试 (P1-3 A2)

验证 metrics 后端经 EnvelopeWriteMixin / success_response 后:
- 4 个 CRUD ViewSet 的 create / update / retrieve 返回统一信封 {success, data, ...}
- 部分 APIView（operators / sample-data / definitions / toggle）成功响应包信封
- list 已由 StandardResultsSetPagination 包信封 (回归守住)
- 错误响应保持裸（由 P2 拦截器归一）

鉴权用全局 auth_client (super_user)。
"""
import pytest

from apps.metrics.models import AtomicMetric, DerivedMetric, MetricRule, MetricTemplate

BASE = '/api/v1/metrics/'

pytestmark = pytest.mark.django_db


@pytest.fixture
def atomic_metric(auth_client):
    resp = auth_client.post(BASE + 'atomic-metrics/', {
        'name': '信封年龄', 'source_path': 'candidate.age', 'data_type': 'number', 'unit': '岁',
    }, format='json')
    assert resp.status_code == 201
    return resp.json()['data']['id']


def test_create_atomic_envelope(auth_client):
    resp = auth_client.post(BASE + 'atomic-metrics/', {
        'name': '新建原子', 'source_path': 'candidate.name', 'data_type': 'string',
    }, format='json')
    assert resp.status_code == 201
    body = resp.json()
    assert body['success'] is True
    assert body['data']['sourcePath'] == 'candidate.name'
    assert body['data']['dataType'] == 'string'


def test_retrieve_atomic_envelope(auth_client, atomic_metric):
    resp = auth_client.get(f'{BASE}atomic-metrics/{atomic_metric}/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['data']['id'] == atomic_metric


def test_update_atomic_envelope(auth_client, atomic_metric):
    resp = auth_client.patch(f'{BASE}atomic-metrics/{atomic_metric}/', {'unit': '年'}, format='json')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['data']['unit'] == '年'


def test_list_atomic_envelope(auth_client, atomic_metric):
    resp = auth_client.get(BASE + 'atomic-metrics/', {'page_size': 200})
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert isinstance(body['data'], list)
    assert body['pagination']['total'] >= 1


@pytest.fixture
def template(auth_client, atomic_metric):
    resp = auth_client.post(BASE + 'templates/', {
        'name': '信封模板', 'atomic_metric': atomic_metric, 'operators': ['GT', 'LT'],
    }, format='json')
    assert resp.status_code == 201
    return resp.json()['data']['id']


def test_create_template_envelope(auth_client, atomic_metric):
    resp = auth_client.post(BASE + 'templates/', {
        'name': '新建模板', 'atomic_metric': atomic_metric, 'operators': ['EQ'],
    }, format='json')
    assert resp.status_code == 201
    body = resp.json()
    assert body['success'] is True
    assert body['data']['name'] == '新建模板'


def test_create_rule_envelope(auth_client, template):
    resp = auth_client.post(BASE + 'rules/', {
        'name': '信封规则', 'scene': 'TALENT_POOL',
        'conditions': [{'templateId': template, 'operator': 'GT', 'value': '30'}],
        'logic': 'AND', 'action_type': 'DEDUCT', 'enabled': True,
    }, format='json')
    assert resp.status_code == 201
    body = resp.json()
    assert body['success'] is True
    assert body['data']['name'] == '信封规则'
    assert body['data']['scene'] == 'TALENT_POOL'


@pytest.fixture
def derived_metric(auth_client):
    resp = auth_client.post(BASE + 'derived-metrics/', {
        'name': '信封派生', 'calc_func': 'HIGHEST_EDU', 'base_path': 'candidate.education',
        'data_type': 'string',
    }, format='json')
    assert resp.status_code == 201
    return resp.json()['data']['id']


def test_create_derived_envelope(auth_client):
    resp = auth_client.post(BASE + 'derived-metrics/', {
        'name': '新建派生', 'calc_func': 'HIGHEST_EDU', 'base_path': 'candidate.workExperience',
        'data_type': 'string',
    }, format='json')
    assert resp.status_code == 201
    body = resp.json()
    assert body['success'] is True
    assert body['data']['calcFunc'] == 'HIGHEST_EDU'


def test_rule_toggle_envelope(auth_client, template):
    resp = auth_client.post(BASE + 'rules/', {
        'name': '信封开关规则', 'scene': 'FILTER',
        'conditions': [{'templateId': template, 'operator': 'GT', 'value': '30'}],
        'logic': 'AND', 'action_type': 'VETO', 'enabled': False,
    }, format='json')
    assert resp.status_code == 201
    rule_id = resp.json()['data']['id']
    resp = auth_client.post(f'{BASE}rules/{rule_id}/toggle/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['data']['enabled'] is True


def test_operator_catalog_envelope(auth_client):
    resp = auth_client.get(BASE + 'operators/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert isinstance(body['data'], list)
    assert 'GT' in {o['value'] for o in body['data']}


def test_sample_data_envelope(auth_client):
    resp = auth_client.get(BASE + 'sample-data/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['data']['candidate']['age'] == 32


def test_definitions_envelope(auth_client):
    resp = auth_client.get(BASE + 'definitions/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert isinstance(body['data'], list)
