"""日期型出参的单位与值域约束测试。

规范口径（见 docs/SPEC_日期类型指标_出参单位与值域.md）：
  1. 日期型出参的「单位」是日期粒度（年/月/日），不是量纲单位
  2. 日期型出参的「值域」是可选日期区间（起止边界 + 步进粒度），不是数值刻度
     - 边界可为绝对日期或相对今天 T±N（年/月/日）
     - step 必须为正整数
"""
from datetime import date

import pytest

from apps.metrics.serializers import _shift_months, resolve_date_bound

pytestmark = pytest.mark.django_db

BASE = '/api/v1/metrics/'


def _unwrap(resp):
    body = resp.data
    if isinstance(body, dict) and 'success' in body and 'data' in body:
        return body['data']
    return body


def _create_date_metric(auth_client, name='出生日期(日期测试)'):
    return _unwrap(auth_client.post(BASE + 'atomic-metrics/', {
        'name': name, 'sourcePath': 'candidate.birth_date', 'dataType': 'date',
    }, format='json'))


def _seg(from_, to_, step=1, step_unit='年'):
    return {'from': from_, 'to': to_, 'step': step, 'stepUnit': step_unit, 'label': ''}


ABS = lambda d: {'type': 'absolute', 'date': d}          # noqa: E731
REL = lambda n, u: {'type': 'relative', 'n': n, 'unit': u}  # noqa: E731


# ---- 边界解析（纯函数）----

def test_resolve_absolute_bound():
    assert resolve_date_bound(ABS('1950-01-01'), date(2026, 1, 1)) == date(1950, 1, 1)
    # 粒度截断：年 → 1月1日，月 → 当月1日
    assert resolve_date_bound(ABS('1950'), date(2026, 1, 1)) == date(1950, 1, 1)
    assert resolve_date_bound(ABS('1950-06'), date(2026, 1, 1)) == date(1950, 6, 1)
    assert resolve_date_bound(ABS(''), date(2026, 1, 1)) is None
    assert resolve_date_bound(ABS('不是日期'), date(2026, 1, 1)) is None


def test_resolve_relative_bound():
    today = date(2026, 3, 15)
    assert resolve_date_bound(REL(-30, '年'), today) == date(1996, 3, 15)
    assert resolve_date_bound(REL(3, '月'), today) == date(2026, 6, 15)
    assert resolve_date_bound(REL(-7, '日'), today) == date(2026, 3, 8)
    assert resolve_date_bound(REL(0, '日'), today) == today


def test_shift_months_clamps_month_end():
    """月末溢出取该月最后一天：1月31日 +1月 → 2月28/29日。"""
    assert _shift_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert _shift_months(date(2024, 1, 31), 1) == date(2024, 2, 29)  # 闰年
    assert _shift_months(date(2026, 1, 15), -13) == date(2024, 12, 15)


# ---- 接口层：日期值域约束 ----

def test_date_template_accepts_date_domain(auth_client):
    """合法日期区间：绝对起止 + 相对边界都接受。"""
    metric_id = _create_date_metric(auth_client)['id']
    resp = auth_client.post(BASE + 'templates/', {
        'name': '出生年月范围', 'atomicMetric': metric_id, 'operators': ['BETWEEN'],
        'unit': '年',
        'valueDomain': {'segments': [
            _seg(ABS('1950-01-01'), ABS('1989-12-31')),
            # 相对段：今天-30年 ~ 今天，与上一段不重叠
            _seg(REL(-30, '年'), REL(0, '日'), step=1, step_unit='月'),
        ]},
    }, format='json')
    assert resp.status_code == 201, resp.data
    segs = _unwrap(resp)['value_domain']['segments']
    assert len(segs) == 2
    assert segs[0]['from']['date'] == '1950-01-01'
    # 相对边界按原样落库（解析只在校验与前端枚举时发生）
    assert segs[1]['from'] == {'type': 'relative', 'n': -30, 'unit': '年'}


def test_date_template_rejects_numeric_domain(auth_client):
    """旧的数值 min/max 在日期口径下必须被拒（无法解释为日期）。"""
    metric_id = _create_date_metric(auth_client)['id']
    resp = auth_client.post(BASE + 'templates/', {
        'name': '出生年月范围', 'atomicMetric': metric_id, 'operators': ['GT'],
        'valueDomain': {'segments': [{'min': 1, 'max': 3, 'step': 1, 'label': ''}]},
    }, format='json')
    assert resp.status_code == 400
    assert '日期区间' in str(resp.data)


@pytest.mark.parametrize('bad_step,expect', [
    (0, '正整数'),
    (-1, '正整数'),
    (0.5, '正整数'),
])
def test_date_domain_step_must_be_positive_int(auth_client, bad_step, expect):
    metric_id = _create_date_metric(auth_client)['id']
    resp = auth_client.post(BASE + 'templates/', {
        'name': '日期步长校验', 'atomicMetric': metric_id, 'operators': ['GT'],
        'valueDomain': {'segments': [_seg(ABS('1950-01-01'), ABS('2000-01-01'), step=bad_step)]},
    }, format='json')
    assert resp.status_code == 400
    assert expect in str(resp.data)


def test_date_domain_from_must_precede_to(auth_client):
    metric_id = _create_date_metric(auth_client)['id']
    resp = auth_client.post(BASE + 'templates/', {
        'name': '日期先后校验', 'atomicMetric': metric_id, 'operators': ['GT'],
        'valueDomain': {'segments': [_seg(ABS('2000-01-01'), ABS('1950-01-01'))]},
    }, format='json')
    assert resp.status_code == 400
    assert '早于' in str(resp.data)


def test_date_domain_segments_must_not_overlap(auth_client):
    metric_id = _create_date_metric(auth_client)['id']
    resp = auth_client.post(BASE + 'templates/', {
        'name': '日期重叠校验', 'atomicMetric': metric_id, 'operators': ['GT'],
        'valueDomain': {'segments': [
            _seg(ABS('1950-01-01'), ABS('2000-12-31')),
            _seg(ABS('1990-01-01'), ABS('2010-12-31')),
        ]},
    }, format='json')
    assert resp.status_code == 400
    assert '重叠' in str(resp.data)


def test_date_template_unit_must_be_granularity(auth_client):
    """日期型出参单位只能是 年/月/日，量纲单位（岁/元）要被拒。"""
    metric_id = _create_date_metric(auth_client)['id']
    resp = auth_client.post(BASE + 'templates/', {
        'name': '日期单位校验', 'atomicMetric': metric_id, 'operators': ['GT'],
        'unit': '岁',
    }, format='json')
    assert resp.status_code == 400
    assert '日期粒度' in str(resp.data)


def test_numeric_template_still_uses_numeric_domain(auth_client):
    """非日期出参仍走原数值口径，不受日期分支影响（回归保护）。"""
    metric_id = _unwrap(auth_client.post(BASE + 'atomic-metrics/', {
        'name': '年龄(数值回归)', 'sourcePath': 'candidate.age', 'dataType': 'number', 'unit': '岁',
    }, format='json'))['id']
    resp = auth_client.post(BASE + 'templates/', {
        'name': '年龄限制', 'atomicMetric': metric_id, 'operators': ['GT'],
        'unit': '岁',
        'valueDomain': {'segments': [{'min': 18, 'max': 60, 'step': 1, 'label': ''}]},
    }, format='json')
    assert resp.status_code == 201, resp.data
    segs = _unwrap(resp)['value_domain']['segments']
    assert segs[0]['min'] == 18 and segs[0]['max'] == 60
