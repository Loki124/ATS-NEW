"""EntryConditionFieldCatalogView 返回 METRIC 源（INF-1/2/3）集成测试。

覆盖：
    - sources 中存在 source == 'METRIC'，其 fields 只含 enabled + 未软删模板
    - 抽查 FieldDef：field == str(id)、label 以 〔原子〕/〔派生〕 结尾、operators == template.operators
    - value_type / options 正确（枚举型 → enum + 下拉）
    - param_config 的 min/max/step 仅在存在时带上
    - common_operators 现含 14 项
"""
import pytest
from django.utils import timezone
from nanoid import generate as nanoid_generate
from rest_framework.test import APIRequestFactory

from apps.metrics.models import AtomicMetric, DerivedMetric, MetricTemplate
from apps.process.views import EntryConditionFieldCatalogView


def _cid() -> str:
    return nanoid_generate(size=21)


def _make_atomic_metric(name, source_path, data_type='number'):
    return AtomicMetric.objects.create(name=name, source_path=source_path, data_type=data_type)


@pytest.mark.django_db
def test_catalog_has_metric_source_and_14_operators():
    # 1) enabled 原子模板（带 param_config）
    am_age = _make_atomic_metric('am_age', 'candidate.age', 'number')
    tpl_age = MetricTemplate.objects.create(
        name='年龄(目录)', atomic_metric=am_age,
        operators=['GT', 'LT', 'EQ', 'IS_EMPTY'],
        param_config={'min': 18, 'max': 60, 'step': 1},
    )

    # 2) enabled 派生模板（带枚举）
    dm_edu = DerivedMetric.objects.create(
        name='dm_edu', calc_func='HIGHEST_EDU', base_path='candidate.education',
        data_type='string',
    )
    tpl_edu = MetricTemplate.objects.create(
        name='学历(目录)', derived_metric=dm_edu,
        operators=['EQ', 'IN'], param_enums=['本科', '硕士', '博士'],
    )

    # 3) disabled 模板 —— 不应出现在 METRIC 源
    am_gender = _make_atomic_metric('am_gender', 'candidate.gender', 'string')
    tpl_disabled = MetricTemplate.objects.create(
        name='性别(禁用)', atomic_metric=am_gender, operators=['EQ'], status='disabled',
    )

    # 4) 软删模板 —— 不应出现
    am_del = _make_atomic_metric('am_del', 'candidate.del', 'string')
    tpl_deleted = MetricTemplate.objects.create(
        name='软删(不应出现)', atomic_metric=am_del, operators=['EQ'],
    )
    tpl_deleted.deleted_at = timezone.now()
    tpl_deleted.save(update_fields=['deleted_at'])

    view = EntryConditionFieldCatalogView()
    req = APIRequestFactory().get('/api/v1/expressions/fields')
    resp = view.get(req)
    data = resp.data['data']

    # common_operators 现含 14 项
    assert len(data['common_operators']) == 14

    # sources 含 METRIC 源
    metric_sources = [s for s in data['sources'] if s.get('source') == 'METRIC']
    assert metric_sources, 'catalog 缺少 METRIC 源'
    fields = metric_sources[0]['fields']

    # 仅含 enabled + 未软删模板：2 个（年龄原子 + 学历派生）
    field_ids = {f['field'] for f in fields}
    assert str(tpl_age.id) in field_ids
    assert str(tpl_edu.id) in field_ids
    assert str(tpl_disabled.id) not in field_ids
    assert str(tpl_deleted.id) not in field_ids

    # 抽查原子 FieldDef
    age_field = next(f for f in fields if f['field'] == str(tpl_age.id))
    assert age_field['label'].endswith('〔原子〕')
    assert age_field['operators'] == ['GT', 'LT', 'EQ', 'IS_EMPTY']
    assert age_field['value_type'] == 'number'
    assert age_field['min'] == 18 and age_field['max'] == 60 and age_field['step'] == 1

    # 抽查派生 FieldDef（枚举 → enum + options + metricKind）
    edu_field = next(f for f in fields if f['field'] == str(tpl_edu.id))
    assert edu_field['label'].endswith('〔派生〕')
    assert edu_field['value_type'] == 'enum'
    assert edu_field['metricKind'] == 'derived'
    assert edu_field['options'] == [
        {'label': '本科', 'value': '本科'},
        {'label': '硕士', 'value': '硕士'},
        {'label': '博士', 'value': '博士'},
    ]


@pytest.mark.django_db
def test_catalog_metric_boolean_has_yes_no_options():
    """METRIC 目录布尔模板（无枚举参数）带 是/否 下拉（F2 必修）。

    对齐 CANDIDATE 目录的 是/否 选项，前端渲染下拉而非自由文本，与 METRIC EQ
    'true'/'false' 契约一致。
    """
    am_black = _make_atomic_metric('am_black', 'candidate.is_blacklisted', 'boolean')
    tpl_black = MetricTemplate.objects.create(
        name='是否黑名单(目录)', atomic_metric=am_black, operators=['EQ', 'NEQ'],
    )

    view = EntryConditionFieldCatalogView()
    req = APIRequestFactory().get('/api/v1/expressions/fields')
    resp = view.get(req)
    data = resp.data['data']

    metric_sources = [s for s in data['sources'] if s.get('source') == 'METRIC']
    assert metric_sources, 'catalog 缺少 METRIC 源'
    field = next(
        (f for f in metric_sources[0]['fields'] if f['field'] == str(tpl_black.id)),
        None,
    )
    assert field is not None, '布尔模板应出现在 METRIC 源'
    assert field['value_type'] == 'boolean'
    assert field['options'] == [
        {'label': '是', 'value': 'true'},
        {'label': '否', 'value': 'false'},
    ]
