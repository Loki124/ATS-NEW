"""RuleItemEvaluator 消费方派发器测试（skip/archive 接入 METRIC，T05）。

覆盖：
    - METRIC 条件项 命中 / 未命中（seed 模板 + 原子指标 + 候选人）
    - legacy CANDIDATE（field=candidate.age）命中 / 未命中
    - evaluate_rule 用 expression '(1 AND 2)' 组合两条 item
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from apps.candidate.models import Candidate
from apps.metrics.models import AtomicMetric, MetricTemplate
from apps.process.services.rule_item_evaluator import RuleItemEvaluator
from nanoid import generate as nanoid_generate


def _cid() -> str:
    return nanoid_generate(size=21)


def _make_candidate(age=None, **fields) -> Candidate:
    return Candidate.objects.create(
        id=_cid(), name='测试', phone='13900000088', age=age, **fields,
    )


def _make_atomic_template(name, source_path, data_type='number', operators=None):
    metric = AtomicMetric.objects.create(
        name=f'am_{name}_{_cid()}', source_path=source_path, data_type=data_type,
    )
    return MetricTemplate.objects.create(
        name=f'{name}_{_cid()}', atomic_metric=metric,
        operators=operators or ['GT', 'LT', 'EQ'],
    )


@pytest.mark.django_db
def test_metric_item_hit():
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)
    res = RuleItemEvaluator.evaluate_item(
        {'condition_type': 'METRIC', 'field': str(tpl.id), 'operator': 'GT', 'value': '30'},
        {'candidate_id': cand.id},
    )
    assert res['pass'] is True
    assert res['template_id'] == str(tpl.id)
    assert res['degraded'] is False


@pytest.mark.django_db
def test_metric_item_miss():
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=20)
    res = RuleItemEvaluator.evaluate_item(
        {'condition_type': 'METRIC', 'field': str(tpl.id), 'operator': 'GT', 'value': '30'},
        {'candidate_id': cand.id},
    )
    assert res['pass'] is False


@pytest.mark.django_db
def test_legacy_candidate_hit():
    _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)
    res = RuleItemEvaluator.evaluate_item(
        {'condition_type': 'CANDIDATE', 'field': 'candidate.age', 'operator': 'GT', 'value': '30'},
        {'candidate_id': cand.id},
    )
    assert res['pass'] is True
    assert res['degraded'] is False


@pytest.mark.django_db
def test_legacy_candidate_miss():
    _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=20)
    res = RuleItemEvaluator.evaluate_item(
        {'condition_type': 'CANDIDATE', 'field': 'candidate.age', 'operator': 'GT', 'value': '30'},
        {'candidate_id': cand.id},
    )
    assert res['pass'] is False


@pytest.mark.django_db
def test_evaluate_rule_combines_items():
    _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)

    # (1 AND 2)：age>30 且 age<50 → 全命中
    rule_pass = {
        'items': [
            {'condition_type': 'CANDIDATE', 'field': 'candidate.age', 'operator': 'GT', 'value': '30'},
            {'condition_type': 'CANDIDATE', 'field': 'candidate.age', 'operator': 'LT', 'value': '50'},
        ],
        'expression': '(1 AND 2)',
    }
    assert RuleItemEvaluator.evaluate_rule(rule_pass, {'candidate_id': cand.id}) is True

    # (1 AND 2)：age>100（未命中）且 age<50（命中）→ AND 失败
    rule_fail = {
        'items': [
            {'condition_type': 'CANDIDATE', 'field': 'candidate.age', 'operator': 'GT', 'value': '100'},
            {'condition_type': 'CANDIDATE', 'field': 'candidate.age', 'operator': 'LT', 'value': '50'},
        ],
        'expression': '(1 AND 2)',
    }
    assert RuleItemEvaluator.evaluate_rule(rule_fail, {'candidate_id': cand.id}) is False


@pytest.mark.django_db
def test_evaluate_rule_empty_expression_all_and():
    _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)
    rule = {
        'items': [
            {'condition_type': 'CANDIDATE', 'field': 'candidate.age', 'operator': 'GT', 'value': '30'},
            {'condition_type': 'CANDIDATE', 'field': 'candidate.age', 'operator': 'LT', 'value': '50'},
        ],
        'expression': '',
    }
    assert RuleItemEvaluator.evaluate_rule(rule, {'candidate_id': cand.id}) is True


@pytest.mark.django_db
def test_legacy_candidate_enum_eq():
    """legacy CANDIDATE 枚举字段（gender=string）EQ 命中（审查补充覆盖）：
    gender=='女' → pass True。"""
    _make_atomic_template('性别', 'candidate.gender', 'string', ['EQ', 'NEQ', 'IN'])
    cand = _make_candidate(gender='女')
    res = RuleItemEvaluator.evaluate_item(
        {'condition_type': 'CANDIDATE', 'field': 'candidate.gender',
         'operator': 'EQ', 'value': '女'},
        {'candidate_id': cand.id},
    )
    assert res['pass'] is True
    assert res['degraded'] is False


@pytest.mark.django_db
def test_legacy_candidate_between_hit():
    """legacy CANDIDATE BETWEEN 命中（F1 必修）：age=40 在 [18,60] 内 → pass True。

    修复前 blanket type_cast(value) 把 [18,60] 当整体转换失败兜底成列表，再交给
    MetricEngine._compare 的 BETWEEN 分支（要求 2 元素元组）抛 ValueError → 被顶层
    except 捕获返回 {pass:False, degraded:True}，把 40 在 [18,60] 内静默误判为未命中。
    """
    _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT', 'BETWEEN'])
    cand = _make_candidate(age=40)
    res = RuleItemEvaluator.evaluate_item(
        {'condition_type': 'CANDIDATE', 'field': 'candidate.age',
         'operator': 'BETWEEN', 'value': [18, 60]},
        {'candidate_id': cand.id},
    )
    assert res['pass'] is True
    assert res['degraded'] is False


@pytest.mark.django_db
def test_legacy_candidate_in_hit():
    """legacy CANDIDATE IN 命中（F1 必修）：gender 在枚举列表 ['女','男'] 内 → pass True。

    验证字符串枚举列表逐元素按 data_type 转换，不再让 type_cast 把列表当整体
    转换为 str 后退化成「子串匹配」造成假阳性。
    """
    _make_atomic_template('性别', 'candidate.gender', 'string', ['EQ', 'NEQ', 'IN'])
    cand = _make_candidate(gender='女')
    res = RuleItemEvaluator.evaluate_item(
        {'condition_type': 'CANDIDATE', 'field': 'candidate.gender',
         'operator': 'IN', 'value': ['女', '男']},
        {'candidate_id': cand.id},
    )
    assert res['pass'] is True
    assert res['degraded'] is False


# ============================================================
# F4 回归：legacy data_type 降级推断（AtomicMetric 查询失败/缺失时按值推断）
# ============================================================
@pytest.mark.django_db
def test_f4_legacy_numeric_when_atomic_metric_query_raises():
    """F4 修复（异常分支）：AtomicMetric 查询抛 Exception → 按 actual 值推断 data_type=number。

    candidate.age GT 30, actual=40 → pass True，且 actual/expected 为 Decimal（数值比较正确），
    不再因退化为 string 做字典序比较（'40'<'9' 误判）。
    """
    fake_metric_cls = MagicMock()
    fake_metric_cls.objects.filter.return_value.first.side_effect = Exception('db down')

    with patch('apps.metrics.models.AtomicMetric', fake_metric_cls), \
         patch('apps.process.services.rule_item_evaluator.build_candidate_snapshot',
               return_value={'candidate': {'age': 40}}):
        res = RuleItemEvaluator.evaluate_item(
            {'condition_type': 'CANDIDATE', 'field': 'candidate.age',
             'operator': 'GT', 'value': '30'},
            {'candidate_id': 'any-cid'},
        )

    assert res['pass'] is True
    assert res['degraded'] is False
    assert isinstance(res['actual'], Decimal), f'actual 应为 Decimal, 实际 {type(res["actual"])}'
    assert isinstance(res['expected'], Decimal), f'expected 应为 Decimal, 实际 {type(res["expected"])}'
    assert res['actual'] == Decimal('40')
    assert res['expected'] == Decimal('30')


@pytest.mark.django_db
def test_f4_legacy_numeric_when_atomic_metric_missing():
    """F4 修复（缺失分支）：AtomicMetric 查询返回 None → 按 actual 值推断 data_type=number。

    数值比较正确（40>30 命中），actual/expected 为 Decimal。
    """
    fake_metric_cls = MagicMock()
    fake_metric_cls.objects.filter.return_value.first.return_value = None

    with patch('apps.metrics.models.AtomicMetric', fake_metric_cls), \
         patch('apps.process.services.rule_item_evaluator.build_candidate_snapshot',
               return_value={'candidate': {'age': 40}}):
        res = RuleItemEvaluator.evaluate_item(
            {'condition_type': 'CANDIDATE', 'field': 'candidate.age',
             'operator': 'GT', 'value': '30'},
            {'candidate_id': 'any-cid'},
        )

    assert res['pass'] is True
    assert res['degraded'] is False
    assert res['actual'] == Decimal('40')
    assert res['expected'] == Decimal('30')


@pytest.mark.django_db
def test_f4_legacy_between_numeric_list_when_metric_missing():
    """F4 修复：AtomicMetric 缺失 + BETWEEN 数值列表 [18,60]，actual=40 → 数值区间命中 pass True。

    _infer_data_type_from_value 对 list 取首元素 18 递归推断为 number，兼容 BETWEEN/IN 数值列表。
    """
    fake_metric_cls = MagicMock()
    fake_metric_cls.objects.filter.return_value.first.return_value = None

    with patch('apps.metrics.models.AtomicMetric', fake_metric_cls), \
         patch('apps.process.services.rule_item_evaluator.build_candidate_snapshot',
               return_value={'candidate': {'age': 40}}):
        res = RuleItemEvaluator.evaluate_item(
            {'condition_type': 'CANDIDATE', 'field': 'candidate.age',
             'operator': 'BETWEEN', 'value': [18, 60]},
            {'candidate_id': 'any-cid'},
        )

    assert res['pass'] is True
    assert res['degraded'] is False
    # BETWEEN 期望值应为数值序列（_jsonable 将元组归一为列表，内部比较仍用 (min,max) 元组）
    assert isinstance(res['expected'], (list, tuple)), \
        f'BETWEEN 期望值应为数值序列, 实际 {type(res["expected"])}'
    assert list(res['expected']) == [Decimal('18'), Decimal('60')]


@pytest.mark.django_db
def test_f4_legacy_metric_hit_path_unchanged():
    """F4 对照组：AtomicMetric 命中（正常路径）仍用 metric.data_type='number'，行为不变。

    数值比较正确，actual 为 Decimal（证明走 metric.data_type 分支而非回退分支）。
    """
    _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT', 'BETWEEN'])
    cand = _make_candidate(age=40)
    res = RuleItemEvaluator.evaluate_item(
        {'condition_type': 'CANDIDATE', 'field': 'candidate.age',
         'operator': 'GT', 'value': '30'},
        {'candidate_id': cand.id},
    )
    assert res['pass'] is True
    assert res['degraded'] is False
    assert res['actual'] == Decimal('40')
    assert res['expected'] == Decimal('30')
