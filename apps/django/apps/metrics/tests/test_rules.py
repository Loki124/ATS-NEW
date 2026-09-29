"""指标规则持久化测试 —— 新增 / 编辑 / 删除 / 启停 / 按规则执行。"""
import pytest

from apps.candidate.models import Candidate
from apps.metrics.models import MetricRule

pytestmark = pytest.mark.django_db

BASE = '/api/v1/metrics/'


def _unwrap(resp):
    body = resp.data
    if isinstance(body, dict) and 'success' in body and 'data' in body:
        return body['data']
    return body


def _ensure_atomic(client, name='年龄', path='candidate.age'):
    rows = _unwrap(client.get(BASE + 'atomic-metrics/'))
    found = next((r for r in rows if r['name'] == name), None)
    if found:
        return found['id']
    return _unwrap(client.post(BASE + 'atomic-metrics/', {
        'name': name, 'sourcePath': path, 'dataType': 'number', 'unit': '岁',
    }, format='json'))['id']


def _ensure_template(client, name='年龄限制'):
    rows = _unwrap(client.get(BASE + 'templates/'))
    found = next((r for r in rows if r['name'] == name), None)
    if found:
        return found['id']
    atomic_id = _ensure_atomic(client)
    return _unwrap(client.post(BASE + 'templates/', {
        'name': name, 'atomicMetric': atomic_id, 'operators': ['GT', 'LT'],
    }, format='json'))['id']


def _make_candidate(age=35):
    return Candidate.objects.create(name='规则测试候选人', age=age, phone='13900000001')


def test_create_rule(auth_client):
    tpl_id = _ensure_template(auth_client)
    resp = auth_client.post(BASE + 'rules/', {
        'name': '年龄门槛', 'scene': 'FILTER', 'logic': 'AND',
        'conditions': [{'templateId': tpl_id, 'operator': 'GT', 'value': '30'}],
    }, format='json')
    assert resp.status_code == 201
    body = _unwrap(resp)
    assert body['name'] == '年龄门槛'
    assert body['enabled'] is True
    # resp.data 处于序列化层为 snake_case（camelCase 仅发生在最终 JSON 渲染）
    assert body['condition_count'] == 1
    assert MetricRule.objects.filter(id=body['id']).exists()


def test_update_rule(auth_client):
    tpl_id = _ensure_template(auth_client)
    created = _unwrap(auth_client.post(BASE + 'rules/', {
        'name': '可调阈值', 'scene': 'FILTER', 'logic': 'AND', 'conditions': [
            {'templateId': tpl_id, 'operator': 'GT', 'value': '30'}],
    }, format='json'))
    resp = auth_client.patch(f"{BASE}rules/{created['id']}/", {
        'conditions': [{'templateId': tpl_id, 'operator': 'GT', 'value': '40'}],
    }, format='json')
    assert resp.status_code == 200
    assert MetricRule.objects.get(id=created['id']).conditions[0]['value'] == '40'


def test_toggle_rule(auth_client):
    tpl_id = _ensure_template(auth_client)
    created = _unwrap(auth_client.post(BASE + 'rules/', {
        'name': '可启停', 'scene': 'FILTER', 'logic': 'AND', 'conditions': [
            {'templateId': tpl_id, 'operator': 'GT', 'value': '30'}],
    }, format='json'))
    assert created['enabled'] is True

    resp = auth_client.post(f"{BASE}rules/{created['id']}/toggle/")
    assert resp.status_code == 200
    assert _unwrap(resp)['enabled'] is False
    assert MetricRule.objects.get(id=created['id']).enabled is False

    # 再切回来（幂等）
    resp2 = auth_client.post(f"{BASE}rules/{created['id']}/toggle/")
    assert _unwrap(resp2)['enabled'] is True


def test_delete_rule(auth_client):
    tpl_id = _ensure_template(auth_client)
    created = _unwrap(auth_client.post(BASE + 'rules/', {
        'name': '待删除', 'scene': 'FILTER', 'logic': 'AND', 'conditions': [
            {'templateId': tpl_id, 'operator': 'GT', 'value': '30'}],
    }, format='json'))
    resp = auth_client.delete(f"{BASE}rules/{created['id']}/")
    assert resp.status_code in (200, 204)


def test_run_saved_rule_on_real_candidate(auth_client):
    """按持久化规则对真实候选人执行（业务触发点的统一入口）。"""
    tpl_id = _ensure_template(auth_client)
    cand = _make_candidate(age=35)
    created = _unwrap(auth_client.post(BASE + 'rules/', {
        'name': '入池门槛', 'scene': 'TALENT_POOL', 'logic': 'AND', 'conditions': [
            {'templateId': tpl_id, 'operator': 'GT', 'value': '30'}],
    }, format='json'))

    resp = auth_client.post(f"{BASE}rules/{created['id']}/run/", {
        'candidateId': str(cand.pk),
    }, format='json')
    assert resp.status_code == 200
    result = _unwrap(resp)
    assert result['pass'] is True
    assert result['steps'][0]['actual'] == 35


def test_run_requires_candidate_id(auth_client):
    tpl_id = _ensure_template(auth_client)
    created = _unwrap(auth_client.post(BASE + 'rules/', {
        'name': '缺参', 'scene': 'FILTER', 'logic': 'AND', 'conditions': [
            {'templateId': tpl_id, 'operator': 'GT', 'value': '30'}],
    }, format='json'))
    resp = auth_client.post(f"{BASE}rules/{created['id']}/run/", {}, format='json')
    assert resp.status_code == 400


def test_run_unknown_candidate_returns_404(auth_client):
    tpl_id = _ensure_template(auth_client)
    created = _unwrap(auth_client.post(BASE + 'rules/', {
        'name': '幽灵候选人', 'scene': 'FILTER', 'logic': 'AND', 'conditions': [
            {'templateId': tpl_id, 'operator': 'GT', 'value': '30'}],
    }, format='json'))
    resp = auth_client.post(f"{BASE}rules/{created['id']}/run/", {
        'candidateId': 'ghost',
    }, format='json')
    assert resp.status_code == 404


def test_rule_rejects_empty_conditions(auth_client):
    resp = auth_client.post(BASE + 'rules/', {'name': '空条件'}, format='json')
    assert resp.status_code == 400


def test_rule_rejects_bad_operator(auth_client):
    tpl_id = _ensure_template(auth_client)
    resp = auth_client.post(BASE + 'rules/', {
        'name': '非法运算符',
        'conditions': [{'templateId': tpl_id, 'operator': 'NOT_AN_OP', 'value': '1'}],
    }, format='json')
    assert resp.status_code == 400


def test_rule_rejects_missing_template(auth_client):
    resp = auth_client.post(BASE + 'rules/', {
        'name': '模板不存在',
        'conditions': [{'templateId': 'ghost-template', 'operator': 'GT', 'value': '1'}],
    }, format='json')
    assert resp.status_code == 400


def test_list_rules(auth_client):
    tpl_id = _ensure_template(auth_client)
    auth_client.post(BASE + 'rules/', {
        'name': '列表用规则', 'scene': 'SCORING', 'logic': 'AND', 'conditions': [
            {'templateId': tpl_id, 'operator': 'GT', 'value': '30'}],
    }, format='json')
    resp = auth_client.get(BASE + 'rules/')
    assert resp.status_code == 200
    assert any(r['name'] == '列表用规则' for r in _unwrap(resp))


def test_execute_endpoint_still_works(auth_client):
    """回归：一次性执行端点未被 rules/{pk}/ 详情路由抢走。"""
    tpl_id = _ensure_template(auth_client)
    resp = auth_client.post(BASE + 'rules/execute/', {
        'conditions': [{'templateId': tpl_id, 'operator': 'GT', 'value': '30'}],
        'data': {'candidate': {'age': 32}},
    }, format='json')
    assert resp.status_code == 200
    assert _unwrap(resp)['pass'] is True
