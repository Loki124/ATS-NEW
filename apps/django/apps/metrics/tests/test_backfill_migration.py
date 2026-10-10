"""动态字段 backfill 迁移（0027）的正向/反向逻辑验证。

直接调用 RunPython 函数而非 MigrationExecutor（原因见 dynamic_field/tests/migration_loader）。
覆盖的关键点:
    1. 编号与主键必须手工生成 —— 历史模型不含 AtomicMetric / MetricTemplate 的
       自定义 save()，而 code 是 unique、id 是 nanoid 主键，漏生成直接撞约束
    2. 与手工种子同路径时以既有指标为准（幂等，不重复建）
    3. 敏感字段与数组类板块字段被正确排除
    4. 反向只删 auto_generated=True，手工种子毫发无损；删除顺序先模板后指标
"""
import pytest

from apps.dynamic_field.tests.migration_loader import load_migration, run

pytestmark = pytest.mark.django_db

MIG = load_migration('metrics', '0027_backfill_dynamic_field_metrics.py')


@pytest.fixture
def silent_signals():
    """断开动态字段→指标同步信号，还原「历史字段在信号生效前就已存在」的真实场景。

    sender 必须用字符串 'dynamic_field.DynamicField' —— 与 signals.py 注册形式一致。
    """
    from django.db.models.signals import post_save

    from apps.dynamic_field.signals import sync_metric_on_field

    sender_ref = 'dynamic_field.DynamicField'
    post_save.disconnect(sync_metric_on_field, sender=sender_ref)
    try:
        yield
    finally:
        post_save.connect(sync_metric_on_field, sender=sender_ref)


def _module(resource, code, name):
    """复用清洗迁移已建的板块；不存在才建（(resource, code) 有唯一约束）。"""
    from apps.dynamic_field.models import FieldModule

    mod = FieldModule.objects.filter(resource=resource, code=code).first()
    if mod is None:
        mod = FieldModule.objects.create(
            id=f'bf_{resource}_{code}', resource=resource, code=code, name=name,
        )
    return mod


def _seed():
    from apps.dynamic_field.models import DynamicField
    from apps.metrics.models import AtomicMetric

    candidate_mod = _module('Candidate', 'candidate', '候选人信息')
    work_mod = _module('Candidate', 'work', '工作经历')

    # ── 应被回填 ──
    DynamicField.objects.create(
        resource='Candidate', field_key='source_channel', label='简历来源',
        field_type='SELECT', module=candidate_mod,
        options=[{'value': '内推', 'label': '内推'}, {'value': '猎头', 'label': '猎头'}],
    )
    DynamicField.objects.create(
        resource='Candidate', field_key='work_experience_years', label='工作年限',
        field_type='NUMBER', module=candidate_mod, options=[],
    )
    # ── 与既有手工指标同路径 → 应跳过 ──
    # 这里自建一条手工指标，而不是依赖库里的种子数据（如 candidate.name）：
    # 测试不应依赖外部种子，否则同库其他用例改动数据后本用例会跟着飘。
    AtomicMetric.objects.create(
        name='同路径手工指标', source_path='candidate.dup_case_field',
        data_type='string', status='enabled', auto_generated=False,
    )
    DynamicField.objects.create(
        resource='Candidate', field_key='dup_case_field', label='重复用例字段',
        field_type='TEXT', module=candidate_mod, options=[],
    )
    # ── 应被排除 ──
    DynamicField.objects.create(
        resource='Candidate', field_key='mobile', label='手机号',
        field_type='PHONE', module=candidate_mod, options=[],
    )
    DynamicField.objects.create(
        resource='Candidate', field_key='salary', label='薪资',
        field_type='NUMBER', module=candidate_mod, options=[],
    )
    DynamicField.objects.create(
        resource='Candidate', field_key='team_leader', label='汇报对象',
        field_type='TEXT', module=work_mod, options=[],
    )


def test_backfill_creates_metric_and_template(silent_signals):
    from apps.metrics.models import AtomicMetric, MetricTemplate

    _seed()
    run(MIG, 'forwards')

    metric = AtomicMetric.objects.get(source_path='candidate.source_channel')
    assert metric.auto_generated is True
    assert metric.code.startswith('AM'), f'编号应自动生成，实际 {metric.code!r}'

    tpl = MetricTemplate.objects.get(atomic_metric=metric)
    assert tpl.code.startswith('MT')
    assert tpl.param_enums == ['内推', '猎头'], '枚举字段的值域应落进模板'
    assert tpl.operators, '模板必须带运算符，否则规则条件无从选起'

    num = AtomicMetric.objects.get(source_path='candidate.work_experience_years')
    assert num.data_type == 'number'


def test_backfill_skips_duplicates_and_excluded(silent_signals):
    from apps.metrics.models import AtomicMetric

    _seed()
    run(MIG, 'forwards')

    # 同路径不重复建：手工那条原样保留，也没有自动生成副本
    assert AtomicMetric.objects.filter(
        source_path='candidate.dup_case_field', auto_generated=True,
    ).count() == 0
    assert AtomicMetric.objects.filter(source_path='candidate.dup_case_field').count() == 1

    assert not AtomicMetric.objects.filter(source_path__in=[
        'candidate.mobile', 'candidate.salary', 'candidate.team_leader',
    ]).exists()


def test_backfill_numbers_are_unique(silent_signals):
    from apps.metrics.models import AtomicMetric, MetricTemplate

    _seed()
    run(MIG, 'forwards')

    codes = list(AtomicMetric.objects.values_list('code', flat=True))
    codes += list(MetricTemplate.objects.values_list('code', flat=True))
    assert len(codes) == len(set(codes)), '编号必须全局唯一'


def test_backfill_is_idempotent(silent_signals):
    from apps.metrics.models import AtomicMetric, MetricTemplate

    _seed()
    run(MIG, 'forwards')
    before_metric = AtomicMetric.objects.count()
    before_tpl = MetricTemplate.objects.count()

    run(MIG, 'forwards')  # 重跑

    assert AtomicMetric.objects.count() == before_metric, '重跑不应重复建指标'
    assert MetricTemplate.objects.count() == before_tpl, '重跑不应重复建模板'


def test_backwards_only_removes_auto_generated(silent_signals):
    from apps.metrics.models import AtomicMetric, MetricTemplate

    _seed()
    run(MIG, 'forwards')

    seed = AtomicMetric.objects.get(source_path='candidate.dup_case_field')
    assert seed.auto_generated is False, '用例前提：该指标是手工维护的'
    assert AtomicMetric.objects.filter(auto_generated=True).exists()

    run(MIG, 'backwards')

    assert AtomicMetric.objects.filter(auto_generated=True).count() == 0
    assert AtomicMetric.objects.filter(pk=seed.pk).exists(), '手工种子被误删'
    # 模板先于指标删除（atomic_metric 是 on_delete=PROTECT），删完不留孤儿模板
    assert not MetricTemplate.objects.filter(
        atomic_metric__auto_generated=True,
    ).exists()