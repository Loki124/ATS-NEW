"""字符串类出参（自由文本 / 枚举）的值域与运算符约束测试。

背景（2026-10 指标值域治理）:
    值域的含义是「有限候选集」—— 只有数值（可按区间枚举）、日期（可按粒度枚举）成立。
    前端旧实现只按「是不是日期」二分，非日期一律渲染 min/max/步长，于是自由文本字段
    （如 demand.position_title）被配上数值值域，保存时报「请填写步长」——填不了也存不了。

本文件锁住修正后的三条口径:
    1. 自由文本（string 且非枚举）不接受数值分段的值域
    2. 自由文本禁用「属于集合 / 不属于集合」（枚举不出全集，配了必然漏匹配）
    3. 枚举型的候选值清单（param_enums）必填 —— 它是条件目录渲染校验值下拉的唯一数据源
       （process.views._build_metric_template_catalog），空清单会让规则配置者面对空下拉
"""
import pytest

from apps.metrics.models import MetricTemplate

pytestmark = pytest.mark.django_db

BASE = '/api/v1/metrics/'
TPL = BASE + 'templates/'

TEXT_OPS = ['EQ', 'CONTAINS', 'REGEX_MATCH']
TEXT_OPS_FULL = ['EQ', 'NEQ', 'CONTAINS', 'NOT_CONTAINS', 'REGEX_MATCH', 'IS_EMPTY', 'IS_NOT_EMPTY']


def _unwrap(resp):
    body = resp.data
    if isinstance(body, dict) and 'success' in body and 'data' in body:
        return body['data']
    return body


def _metric(auth_client, name, data_type='string', is_enum=False, enum_values=None):
    return _unwrap(auth_client.post(BASE + 'atomic-metrics/', {
        'name': name,
        'sourcePath': f'candidate.{name}',
        'dataType': data_type,
        'isEnum': is_enum,
        'enumValues': enum_values or [],
    }, format='json'))


def _template(auth_client, metric_id, name, operators, **extra):
    payload = {
        'name': name,
        'atomicMetric': metric_id,
        'operators': operators,
    }
    payload.update(extra)
    return auth_client.post(TPL, payload, format='json')


def _err(resp):
    """取出错误文本。

    统一异常处理器把 DRF 的校验错误塞进 {success:False, code, message, errors}，
    其中 errors 是 {non_field_errors: [...]} 或 {field: [...]}（见 apps.common.exceptions）。
    """
    body = resp.data
    if isinstance(body, dict) and 'errors' in body:
        return str(body['errors'])
    return str(body)


# ---- 自由文本：数值分段的值域应被拒绝 ----

def test_freetext_rejects_numeric_segments(auth_client):
    m = _metric(auth_client, '职位名称_值域治理')
    resp = _template(auth_client, m['id'], '职位名称模板', TEXT_OPS,
                     valueDomain={'segments': [{'min': 0, 'max': 10, 'step': 1}]})
    assert resp.status_code == 400, resp.data
    assert '字符串' in _err(resp)


def test_freetext_accepts_empty_domain(auth_client):
    m = _metric(auth_client, '公司名称_值域治理')
    resp = _template(auth_client, m['id'], '公司名称模板', TEXT_OPS_FULL,
                     valueDomain={'segments': []})
    assert resp.status_code == 201, resp.data
    # 直接查库断言真正持久化的值，避免依赖响应体的命名风格
    saved = MetricTemplate.objects.get(name='公司名称模板')
    assert saved.value_domain.get('segments') == []


def test_freetext_omits_value_domain_entirely(auth_client):
    m = _metric(auth_client, '技能标签_值域治理')
    resp = _template(auth_client, m['id'], '技能标签模板', TEXT_OPS)
    assert resp.status_code == 201, resp.data


# ---- 自由文本：集合运算符应被拒绝 ----

@pytest.mark.parametrize('op', ['IN', 'NOT_IN'])
def test_freetext_rejects_set_operators(auth_client, op):
    m = _metric(auth_client, f'自由文本_{op}_治理')
    resp = _template(auth_client, m['id'], f'自由文本模板_{op}', [op])
    assert resp.status_code == 400, resp.data
    err = _err(resp)
    # 错误文案要能替代引导：指出改用「包含」或「正则匹配」
    assert '包含' in err and '正则' in err


@pytest.mark.parametrize('op', TEXT_OPS)
def test_freetext_allows_contains_style_operators(auth_client, op):
    m = _metric(auth_client, f'文本允许_{op}_治理')
    resp = _template(auth_client, m['id'], f'文本允许模板_{op}', [op])
    assert resp.status_code == 201, resp.data


# ---- 枚举型：候选值清单必填（param_enums） ----

def test_enum_requires_candidates(auth_client):
    m = _metric(auth_client, '学历枚举_治理', is_enum=True)
    resp = _template(auth_client, m['id'], '学历枚举模板', ['EQ'], paramEnums=[])
    assert resp.status_code == 400, resp.data
    assert '候选值' in _err(resp)


def test_enum_rejects_numeric_segments(auth_client):
    m = _metric(auth_client, '渠道枚举_治理', is_enum=True)
    resp = _template(auth_client, m['id'], '渠道枚举模板', ['EQ'], paramEnums=['内推'],
                     valueDomain={'segments': [{'min': 1, 'max': 5, 'step': 1}]})
    assert resp.status_code == 400, resp.data
    assert '字符串' in _err(resp)


def test_enum_rejects_duplicate_candidates(auth_client):
    m = _metric(auth_client, '状态枚举_治理', is_enum=True)
    resp = _template(auth_client, m['id'], '状态枚举模板', ['EQ'], paramEnums=['在职', '离职', '在职'])
    assert resp.status_code == 400, resp.data
    assert '重复' in _err(resp)


def test_enum_rejects_blank_candidate(auth_client):
    m = _metric(auth_client, '类型枚举_治理', is_enum=True)
    resp = _template(auth_client, m['id'], '类型枚举模板', ['EQ'], paramEnums=['全职', '  '])
    assert resp.status_code == 400, resp.data


def test_enum_accepts_candidates_and_set_operators(auth_client):
    """枚举是有限域 —— 集合运算符在这里语义成立，不该被自由文本的规则误伤。"""
    m = _metric(auth_client, '来源枚举_治理', is_enum=True, enum_values=['内推', '猎头'])
    resp = _template(auth_client, m['id'], '来源枚举模板', ['IN', 'NOT_IN'],
                     paramEnums=['内推', '猎头', '官网'])
    assert resp.status_code == 201, resp.data
    saved = MetricTemplate.objects.get(name='来源枚举模板')
    assert saved.param_enums == ['内推', '猎头', '官网']


# ---- 回归：数值的既有口径不受影响 ----

def test_number_segments_still_accepted(auth_client):
    m = _metric(auth_client, '年龄_值域治理', data_type='number')
    resp = _template(auth_client, m['id'], '年龄模板', ['BETWEEN'],
                     valueDomain={'segments': [{'min': 20, 'max': 30, 'step': 1}]})
    assert resp.status_code == 201, resp.data


def test_number_rejects_invalid_segment_range(auth_client):
    m = _metric(auth_client, '薪资_值域治理', data_type='number')
    resp = _template(auth_client, m['id'], '薪资模板', ['BETWEEN'],
                     valueDomain={'segments': [{'min': 30, 'max': 20, 'step': 1}]})
    assert resp.status_code == 400, resp.data