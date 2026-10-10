"""0029 迁移（纠正字符串类模板的值域 / 集合运算）正向与反向验证。

直接调用 RunPython 函数而非 MigrationExecutor，原因见 dynamic_field/tests/migration_loader。

关键点:
    1. 判定必须经 atomic_metric / derived_metric 取字段 —— MetricTemplate.data_type
       在真实模型上是 property，历史模型不含自定义 property，直接取会 AttributeError
    2. 只处理字符串类：数值 / 日期模板的运算符与值域不得被误伤
    3. 反向须把集合运算符加回，否则回滚后模板能力缺失
"""
import pytest

from apps.dynamic_field.tests.migration_loader import load_migration, run
from apps.metrics.models import AtomicMetric, MetricTemplate

pytestmark = pytest.mark.django_db

MIG = load_migration('metrics', '0029_strip_freetext_set_operators.py')


def _metric(name, data_type='string', is_enum=False, enum_values=None):
    return AtomicMetric.objects.create(
        name=name,
        source_path=f'candidate.{name}',
        data_type=data_type,
        is_enum=is_enum,
        enum_values=enum_values or [],
    )


def _tpl(name, metric, operators, value_domain=None, param_enums=None, status='enabled'):
    return MetricTemplate.objects.create(
        name=name,
        atomic_metric=metric,
        operators=operators,
        value_domain=value_domain if value_domain is not None else {'segments': []},
        param_enums=param_enums if param_enums is not None else [],
        status=status,
    )


# ---- 自由文本：集合运算符被移除，其他运算符保留 ----

def test_forwards_strips_set_operators_from_freetext():
    metric = _metric('职位名称_迁移')
    tpl = _tpl('职位名称模板_迁移', metric,
               ['EQ', 'IN', 'CONTAINS', 'NOT_IN', 'REGEX_MATCH', 'IS_EMPTY'])
    run(MIG, 'forwards')
    tpl.refresh_from_db()
    assert tpl.operators == ['EQ', 'CONTAINS', 'REGEX_MATCH', 'IS_EMPTY']


def test_forwards_clears_numeric_segments_on_freetext():
    """旧版前端给字符串渲染数值分段，落库即脏数据，须清空。"""
    metric = _metric('公司名称_迁移')
    tpl = _tpl('公司名称模板_迁移', metric, ['EQ'],
               value_domain={'segments': [{'min': 0, 'max': 10, 'step': 1}]})
    run(MIG, 'forwards')
    tpl.refresh_from_db()
    assert tpl.value_domain.get('segments') == []


def test_backwards_restores_set_operators():
    metric = _metric('技能标签_迁移')
    tpl = _tpl('技能标签模板_迁移', metric, ['EQ', 'CONTAINS'])
    run(MIG, 'forwards')
    run(MIG, 'backwards')
    tpl.refresh_from_db()
    assert 'IN' in tpl.operators and 'NOT_IN' in tpl.operators


# ---- 枚举：候选值为空则停用，有值则不动 ----

def test_forwards_disables_enum_without_candidates():
    metric = _metric('学历枚举_迁移', is_enum=True)
    tpl = _tpl('学历枚举模板_迁移', metric, ['EQ'], param_enums=[])
    run(MIG, 'forwards')
    tpl.refresh_from_db()
    assert tpl.status == 'disabled'
    # 集合运算符对枚举（有限域）语义成立，必须保留
    assert tpl.operators == ['EQ']


def test_forwards_keeps_enum_with_candidates():
    metric = _metric('渠道枚举_迁移', is_enum=True, enum_values=['内推', '官网'])
    tpl = _tpl('渠道枚举模板_迁移', metric, ['IN', 'NOT_IN'], param_enums=['内推', '官网'])
    run(MIG, 'forwards')
    tpl.refresh_from_db()
    assert tpl.status == 'enabled'
    assert tpl.operators == ['IN', 'NOT_IN']


def test_enum_candidates_can_come_from_metric_enum_values():
    """模板没配 param_enums 但指标声明了 enum_values 时，不该被停用。"""
    metric = _metric('来源枚举_迁移', is_enum=True, enum_values=['内推', '猎头'])
    tpl = _tpl('来源枚举模板_迁移', metric, ['EQ'], param_enums=[])
    run(MIG, 'forwards')
    tpl.refresh_from_db()
    assert tpl.status == 'enabled'


def test_backwards_reenables_enum():
    metric = _metric('类型枚举_迁移', is_enum=True)
    tpl = _tpl('类型枚举模板_迁移', metric, ['EQ'], param_enums=[])
    run(MIG, 'forwards')
    run(MIG, 'backwards')
    tpl.refresh_from_db()
    assert tpl.status == 'enabled'


# ---- 回归：数值 / 日期模板不得被误伤 ----

def test_number_template_untouched():
    metric = _metric('年龄_迁移', data_type='number')
    tpl = _tpl('年龄模板_迁移', metric, ['GT', 'BETWEEN', 'IN'],
               value_domain={'segments': [{'min': 20, 'max': 30, 'step': 1}]})
    run(MIG, 'forwards')
    tpl.refresh_from_db()
    assert tpl.operators == ['GT', 'BETWEEN', 'IN']
    assert tpl.value_domain['segments'][0]['min'] == 20


def test_date_template_untouched():
    metric = _metric('到岗日期_迁移', data_type='date')
    seg = {'from': {'type': 'absolute', 'date': '2026-01-01'},
           'to': {'type': 'absolute', 'date': '2026-12-31'},
           'step': 1, 'stepUnit': '日'}
    tpl = _tpl('到岗日期模板_迁移', metric, ['BETWEEN', 'IS_EMPTY'],
               value_domain={'segments': [seg]})
    run(MIG, 'forwards')
    tpl.refresh_from_db()
    assert tpl.value_domain['segments'][0]['step'] == 1
    assert tpl.status == 'enabled'


# ---- 幂等：连跑两次不应改变结果 ----

def test_forwards_is_idempotent():
    metric = _metric('备注_迁移')
    tpl = _tpl('备注模板_迁移', metric, ['EQ', 'IN', 'CONTAINS'])
    run(MIG, 'forwards')
    once = list(MetricTemplate.objects.get(pk=tpl.pk).operators)
    run(MIG, 'forwards')
    assert list(MetricTemplate.objects.get(pk=tpl.pk).operators) == once