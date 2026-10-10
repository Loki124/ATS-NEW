"""动态字段 → 指标定义同步的运行时验证（2026-10 全量治理）。

覆盖 signals.sync_metric_on_field 的关键行为：
    1. 建字段时同步产出 AtomicMetric + MetricTemplate（模板是规则条件字段目录的唯一来源）
    2. 归一化后拦截薪资/联系方式（PII 类型与标签式 key 都不能漏进来）
    3. 非 snake_case / 空 field_type 的字段不自动映射（避免制造指向不存在路径的脏指标）
    4. 幂等：重复触发不重复建；update 路径（软删复活）也能补齐
    5. 数组条目类板块（工作经历等）的字段不自动映射
"""
import pytest

from apps.dynamic_field.models import DynamicField, FieldModule
from apps.metrics.models import AtomicMetric, MetricTemplate

pytestmark = pytest.mark.django_db


def _make_field(field_key, field_type='TEXT', resource='Candidate', label=None, module=None):
    return DynamicField.objects.create(
        resource=resource,
        field_key=field_key,
        label=label or field_key,
        field_type=field_type,
        module=module,
        options=[],
    )


def test_creates_metric_and_template_together():
    """同步建指标的同时必须建模板，否则规则条件里选不到这个字段。"""
    _make_field('years_of_experience', 'NUMBER')

    metric = AtomicMetric.objects.get(source_path='candidate.years_of_experience')
    assert metric.auto_generated is True
    assert metric.data_type == 'number'

    tpl = MetricTemplate.objects.get(atomic_metric=metric)
    assert tpl.status == 'enabled'
    assert 'GT' in tpl.operators, '数值型应带上范围运算符'


def test_enum_field_carries_value_domain_into_template():
    """枚举字段的值域要落到 param_enums，否则规则条件无值可选。"""
    field = DynamicField.objects.create(
        resource='Candidate',
        field_key='highest_degree',
        label='最高学历',
        field_type='SELECT',
        options=[{'value': '本科', 'label': '本科'}, {'value': '硕士', 'label': '硕士研究生'}],
    )
    metric = AtomicMetric.objects.get(source_path='candidate.highest_degree')
    assert metric.is_enum is True
    tpl = MetricTemplate.objects.get(atomic_metric=metric)
    assert tpl.param_enums == ['本科', '硕士']


@pytest.mark.parametrize('field_key,field_type', [
    ('expected_salary', 'NUMBER'),   # 薪资：snake_case 也必须拦
    ('salary_max', 'NUMBER'),
    ('wechat', 'TEXT'),              # 联系方式
])
def test_sensitive_keys_are_blocked(field_key, field_type):
    _make_field(field_key, field_type)
    assert not AtomicMetric.objects.filter(source_path=f'candidate.{field_key}').exists()


@pytest.mark.parametrize('field_key,field_type', [
    ('Mobile', 'PHONE'),     # PII 类型
    ('Email', 'EMAIL'),
    ('ID number', 'ID_CARD'),
])
def test_sensitive_types_are_blocked(field_key, field_type):
    """注意这里 key 是标签式 —— 正是旧实现漏掉的形态（当时精确匹配 'phone' 匹配不到 'Mobile'）。"""
    _make_field(field_key, field_type)
    assert AtomicMetric.objects.filter(source_path=f'candidate.{field_key}').exists() is False


@pytest.mark.parametrize('field_key,field_type', [
    ('Birth Date (Age)', 'DATE'),      # 含空格括号，非 snake_case
    ('Political affiliation', 'TEXT'), # 含空格
])
def test_non_snake_case_key_is_blocked(field_key, field_type):
    _make_field(field_key, field_type)
    assert not AtomicMetric.objects.filter(source_path=f'candidate.{field_key}').exists()


def test_empty_field_type_is_blocked():
    """field_type 为空无法推断指标类型，应跳过并留待人工配置，而非造出 string 脏指标。"""
    field = DynamicField(resource='Candidate', field_key='orphan_field', label='孤儿字段', field_type='TEXT')
    field.field_type = ''
    field.save()
    assert not AtomicMetric.objects.filter(source_path='candidate.orphan_field').exists()


def test_idempotent_on_repeated_signal():
    """幂等：同 source_path 重复触发不重复建指标，也不重复建模板。"""
    field = _make_field('source_channel', 'SELECT')
    first = AtomicMetric.objects.get(source_path='candidate.source_channel')

    from apps.dynamic_field.signals import sync_metric_on_field
    sync_metric_on_field(sender=DynamicField, instance=field, created=False)

    assert AtomicMetric.objects.filter(source_path='candidate.source_channel').count() == 1
    assert MetricTemplate.objects.filter(atomic_metric=first).count() == 1


def test_update_path_backfills_missing_metric():
    """update 路径（软删复活 / 编辑）也能补齐缺失的指标 —— 旧实现 created-only 会漏。"""
    field = _make_field('available_date', 'DATE')
    # MetricTemplate.atomic_metric 是 on_delete=PROTECT：必须先删模板才能删指标，
    # 任何数据回滚迁移也必须遵循同样的顺序。
    MetricTemplate.objects.filter(atomic_metric__source_path='candidate.available_date').delete()
    AtomicMetric.objects.filter(source_path='candidate.available_date').delete()

    from apps.dynamic_field.signals import sync_metric_on_field
    sync_metric_on_field(sender=DynamicField, instance=field, created=False)

    assert AtomicMetric.objects.filter(source_path='candidate.available_date').exists()
    assert MetricTemplate.objects.filter(name='available_date').exists()


def test_array_section_module_is_not_auto_mapped():
    """数组条目类板块（工作经历…）的字段路径需索引，信号不自动映射。"""
    # code 用 'experience' 而非 'work'：后者已被 0023 清洗迁移建过，
    # (resource, code) 唯一约束下会直接插入失败
    module = FieldModule.objects.create(
        resource='Candidate', code='experience', name='工作经历（用例）',
    )
    _make_field('company_size', 'TEXT', module=module)

    assert not AtomicMetric.objects.filter(source_path='candidate.company_size').exists()


@pytest.mark.parametrize('resource,prefix', [
    ('Demand', 'demand'),
    ('Position', 'position'),
])
def test_demand_and_position_are_now_synced(resource, prefix):
    """同步范围已从「仅 Candidate」扩到全部业务资源。"""
    _make_field('headcount_count', 'NUMBER', resource=resource)
    assert AtomicMetric.objects.filter(source_path=f'{prefix}.headcount_count').exists()


def test_soft_deleted_field_not_exposed_in_reference_list():
    """软删字段不应出现在可引用字段清单里。"""
    field = _make_field('ghost_field', 'TEXT')
    field.delete()

    from apps.metrics.services.candidate_snapshot import list_candidate_paths
    paths = [p['path'] for p in list_candidate_paths()]
    assert 'candidate.ghost_field' not in paths

@pytest.mark.parametrize('field_key,label', [
    ('salary_budget', '薪资范围'),      # 精确名单拦不住的变体（真实漏网案例）
    ('budget_salary', '薪资预算'),
    ('avg_salary', '平均年薪'),
])
def test_salary_key_variants_are_blocked_by_substring_fallback(field_key, label):
    """语义兜底：只靠精确名单时 'salary_budget' 曾漏进规则条件（0028 清理过一条）。"""
    _make_field(field_key, 'NUMBER', label=label)
    assert not AtomicMetric.objects.filter(source_path=f'candidate.{field_key}').exists()


def test_salary_key_is_blocked_by_label_even_when_key_is_clean():
    """key 名不敏感但 label 是薪资，也必须拦 —— 换个英文名就能绕过 key 判定。"""
    _make_field('compensation_plan', 'NUMBER', label='薪酬方案')
    assert not AtomicMetric.objects.filter(source_path='candidate.compensation_plan').exists()


def test_normal_field_is_not_blocked():
    """兜底不能误伤：不含薪资语义的正常字段仍应放行。

    直接断言判定函数而非「指标是否存在」，避免依赖库中既有种子指标。
    """
    from apps.dynamic_field import signals as sync_signals

    for key, label in [('company_scale', '公司规模'), ('degree', '学历'), ('school', '院校名称')]:
        field = _make_field(key, 'TEXT', label=label)
        assert sync_signals._block_reason(field) == '', f'{key} 不该被拦截'
