"""指标库 API 测试 —— 请求用 camelCase（验证 CamelCaseParser 契约），
断言统一经 _unwrap 解信封（项目响应为 {success, data, pagination}）。
"""
import pytest

pytestmark = pytest.mark.django_db

BASE = '/api/v1/metrics/'


def _unwrap(resp):
    """兼容裸响应与标准信封两种形态。"""
    body = resp.data
    if isinstance(body, dict) and 'success' in body and 'data' in body:
        return body['data']
    return body


def _create_atomic(auth_client, name='年龄(接口测试)', path='candidate.age', unit='岁'):
    return auth_client.post(BASE + 'atomic-metrics/', {
        'name': name, 'sourcePath': path, 'dataType': 'number', 'unit': unit,
    }, format='json')


def test_operator_catalog(auth_client):
    resp = auth_client.get(BASE + 'operators/')
    assert resp.status_code == 200
    ops = _unwrap(resp)
    values = {o['value'] for o in ops}
    # 复用统一规则引擎 11 种运算符，含 PRD 缺失的 BETWEEN
    assert {'GT', 'LT', 'EQ', 'BETWEEN', 'IN', 'IS_EMPTY'} <= values


def test_derived_func_catalog(auth_client):
    resp = auth_client.get(BASE + 'derived-funcs/')
    assert resp.status_code == 200
    funcs = _unwrap(resp)
    names = {f['name'] for f in funcs}
    assert {'MAX_GAP', 'COUNT_IN_WINDOW', 'HIGHEST_EDU'} <= names


def test_sample_data(auth_client):
    resp = auth_client.get(BASE + 'sample-data/')
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert data['candidate']['age'] == 32


def test_create_atomic_metric_rejects_path_without_dot(auth_client):
    resp = _create_atomic(auth_client, path='age')
    assert resp.status_code == 400


def test_create_and_list_atomic_metric(auth_client):
    assert _create_atomic(auth_client).status_code == 201
    resp = auth_client.get(BASE + 'atomic-metrics/')
    assert resp.status_code == 200
    rows = _unwrap(resp)
    # 注意：resp.data 处于序列化层为 snake_case（camelCase 仅发生在最终 JSON 渲染）
    assert any(r['source_path'] == 'candidate.age' for r in rows)


def test_ac03_delete_atomic_in_use_rejected(auth_client):
    """AC-03：被模板引用的原子指标拒绝删除，返回 400 JSON（不 500）。"""
    created = _unwrap(_create_atomic(auth_client))
    metric_id = created['id']
    tpl = auth_client.post(BASE + 'templates/', {
        'name': '年龄限制', 'atomicMetric': metric_id, 'operators': ['GT', 'LT'],
    }, format='json')
    assert tpl.status_code == 201

    resp = auth_client.delete(f'{BASE}atomic-metrics/{metric_id}/')
    assert resp.status_code == 400
    assert '被 1 个模板引用' in str(resp.data)


def test_delete_unused_atomic_metric_ok(auth_client):
    created = _unwrap(_create_atomic(auth_client, name='未使用指标'))
    resp = auth_client.delete(f'{BASE}atomic-metrics/{created["id"]}/')
    assert resp.status_code in (200, 204)


def test_p1_delete_template_in_use_rejected(auth_client):
    """【P1/B-2 回归】被规则引用的模板软删也成功（D1：destroy 不再 400 拦截）。

    删除前的事前披露（受影响规则清单）由前端 LIFE-2 弹窗负责，后端 destroy 仅软删
    （置 deleted_at，不物理删行），因此即便模板被规则 conditions 引用也能安全删除，
    引用字符串依旧有效、版本快照因行在而不被 CASCADE 清掉，可随后经 restore 真撤销。
    """
    created = _unwrap(_create_atomic(auth_client))
    metric_id = created['id']
    tpl = auth_client.post(BASE + 'templates/', {
        'name': 'B2模板', 'atomicMetric': metric_id, 'operators': ['GT'],
    }, format='json')
    assert tpl.status_code == 201
    tpl_id = _unwrap(tpl)['id']

    # 用 ORM 建一条引用该模板的规则（聚焦删除保护，绕过规则保存的完整校验）
    from apps.metrics.models import MetricRule, MetricRuleScene
    MetricRule.objects.create(
        name='B2规则', scene=MetricRuleScene.TALENT_POOL, logic='AND',
        conditions=[{'templateId': tpl_id, 'operator': 'GT', 'value': '30'}],
    )

    # D1：被引用模板也能软删成功（不再 400）
    resp = auth_client.delete(f'{BASE}templates/{tpl_id}/')
    assert resp.status_code == 204
    # 软删（非硬删）：默认 manager 过滤 → 列表/retrieve 不可见，但 all_objects 仍可取
    from apps.metrics.models import MetricTemplate
    assert not MetricTemplate.objects.filter(id=tpl_id).exists()
    assert MetricTemplate.all_objects.filter(id=tpl_id).exists()


def test_p1_delete_unused_template_ok(auth_client):
    """【P1/B-2 无假阳性】无引用的模板可正常删除（204）。"""
    created = _unwrap(_create_atomic(auth_client))
    tpl = auth_client.post(BASE + 'templates/', {
        'name': 'B2未用模板', 'atomicMetric': created['id'], 'operators': ['GT'],
    }, format='json')
    assert tpl.status_code == 201
    tpl_id = _unwrap(tpl)['id']
    resp = auth_client.delete(f'{BASE}templates/{tpl_id}/')
    assert resp.status_code == 204
    from apps.metrics.models import MetricTemplate
    assert not MetricTemplate.objects.filter(id=tpl_id).exists()


def test_template_must_reference_exactly_one_metric(auth_client):
    created = _unwrap(_create_atomic(auth_client))
    resp = auth_client.post(BASE + 'templates/', {
        'name': '两个指标', 'atomicMetric': created['id'],
        'derivedMetric': created['id'], 'operators': ['GT'],
    }, format='json')
    assert resp.status_code == 400


def test_template_rejects_unknown_operator(auth_client):
    created = _unwrap(_create_atomic(auth_client))
    resp = auth_client.post(BASE + 'templates/', {
        'name': '非法运算符', 'atomicMetric': created['id'], 'operators': ['NOT_A_OP'],
    }, format='json')
    assert resp.status_code == 400


def test_execute_endpoint_end_to_end(auth_client):
    """端到端：建原子指标 → 建模板 → 执行「年龄 > 30」→ PASS。"""
    created = _unwrap(_create_atomic(auth_client))
    tpl = _unwrap(auth_client.post(BASE + 'templates/', {
        'name': '年龄限制', 'atomicMetric': created['id'], 'operators': ['GT', 'LT'],
    }, format='json'))

    resp = auth_client.post(BASE + 'rules/execute/', {
        'conditions': [{'templateId': tpl['id'], 'operator': 'GT', 'value': '30'}],
        'logic': 'AND',
        'data': {'candidate': {'age': 32}},
    }, format='json')
    assert resp.status_code == 200
    result = _unwrap(resp)
    assert result['pass'] is True
    assert result['steps'][0]['pass'] is True


def test_execute_endpoint_never_500_on_bad_input(auth_client):
    """非功能要求：任何非法输入都返回 JSON 错误，绝不 500。"""
    resp = auth_client.post(BASE + 'rules/execute/', {
        'conditions': [{'templateId': 'ghost', 'operator': 'GT', 'value': '30'}],
        'data': {'candidate': {'age': 32}},
    }, format='json')
    assert resp.status_code == 200
    result = _unwrap(resp)
    assert result['pass'] is False
    assert '不存在' in result['steps'][0]['error']


def test_execute_rejects_empty_conditions(auth_client):
    resp = auth_client.post(BASE + 'rules/execute/', {
        'conditions': [], 'data': {},
    }, format='json')
    assert resp.status_code == 400
