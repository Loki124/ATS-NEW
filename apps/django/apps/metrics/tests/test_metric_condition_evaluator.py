"""evaluate_metric_condition 单元/集成测试（INF-4 统一指标条件求值器）。

覆盖：
    - 原子指标 GT 命中 / 未命中
    - IS_EMPTY / IS_NOT_EMPTY 对 None 字段
    - 模板不支持的运算符 → pass False + error
    - 禁用 / 软删模板 → degraded True + pass False
    - 派生指标缺底层数据（base_path 不在快照）→ pass False + degraded
全部使用 @pytest.mark.django_db，测试内自建最小对象，不依赖外部 fixture。
"""
import pytest
from django.utils import timezone

from apps.candidate.models import Candidate
from apps.metrics.models import AtomicMetric, DerivedMetric, MetricTemplate
from apps.metrics.services.metric_engine import MetricEngine
from nanoid import generate as nanoid_generate


def _cid() -> str:
    return nanoid_generate(size=21)


def _make_candidate(age=None, **fields) -> Candidate:
    return Candidate.objects.create(
        id=_cid(), name='测试候选人', phone='13900000099', age=age, **fields,
    )


def _make_atomic_template(name, source_path, data_type='number', operators=None, unit='', **mt_kwargs):
    metric = AtomicMetric.objects.create(
        name=f'am_{name}_{_cid()}', source_path=source_path, data_type=data_type, unit=unit,
    )
    return MetricTemplate.objects.create(
        name=f'{name}_{_cid()}', atomic_metric=metric,
        operators=operators or ['GT', 'LT', 'EQ', 'IS_EMPTY', 'IS_NOT_EMPTY'],
        **mt_kwargs,
    )


@pytest.mark.django_db
def test_atomic_gt_hit():
    """原子指标 GT 命中：age=32 > 30 → pass True。"""
    tpl = _make_atomic_template('年龄限制', 'candidate.age', 'number', ['GT', 'LT'], '岁')
    cand = _make_candidate(age=32)
    res = MetricEngine.evaluate_metric_condition(tpl.id, {'candidate_id': cand.id}, 'GT', '30')
    assert res['pass'] is True
    assert res['degraded'] is False
    assert res['template_id'] == str(tpl.id)
    assert res['actual'] == 32
    assert res['error'] == ''


@pytest.mark.django_db
def test_atomic_gt_miss():
    """原子指标 GT 未命中：age=20 < 30 → pass False。"""
    tpl = _make_atomic_template('年龄限制', 'candidate.age', 'number', ['GT', 'LT'], '岁')
    cand = _make_candidate(age=20)
    res = MetricEngine.evaluate_metric_condition(tpl.id, {'candidate_id': cand.id}, 'GT', '30')
    assert res['pass'] is False
    assert res['degraded'] is False
    assert res['error'] == ''


@pytest.mark.django_db
def test_is_empty_on_none_field():
    """IS_EMPTY 对 None 字段 → pass True（_compare 正常处理 None，不降级）。"""
    tpl = _make_atomic_template('年龄限制', 'candidate.age', 'number', ['IS_EMPTY', 'IS_NOT_EMPTY'])
    cand = _make_candidate(age=None)
    res = MetricEngine.evaluate_metric_condition(tpl.id, {'candidate_id': cand.id}, 'IS_EMPTY', None)
    assert res['pass'] is True
    assert res['degraded'] is False


@pytest.mark.django_db
def test_is_not_empty_on_none_field():
    """IS_NOT_EMPTY 对 None 字段 → pass False。"""
    tpl = _make_atomic_template('年龄限制', 'candidate.age', 'number', ['IS_EMPTY', 'IS_NOT_EMPTY'])
    cand = _make_candidate(age=None)
    res = MetricEngine.evaluate_metric_condition(
        tpl.id, {'candidate_id': cand.id}, 'IS_NOT_EMPTY', None,
    )
    assert res['pass'] is False
    assert res['degraded'] is False


@pytest.mark.django_db
def test_unsupported_operator_reports_error():
    """模板不支持的运算符 → pass False + error（degraded=False，属预期业务拒绝）。"""
    tpl = _make_atomic_template('年龄限制', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=32)
    res = MetricEngine.evaluate_metric_condition(tpl.id, {'candidate_id': cand.id}, 'BETWEEN', None)
    assert res['pass'] is False
    assert res['error'] == '模板不支持该运算符'
    assert res['degraded'] is False


@pytest.mark.django_db
def test_disabled_template_degraded():
    """禁用模板 → degraded True + pass False。"""
    tpl = _make_atomic_template('年龄限制', 'candidate.age', 'number', ['GT'])
    tpl.status = 'disabled'
    tpl.save(update_fields=['status'])
    cand = _make_candidate(age=32)
    res = MetricEngine.evaluate_metric_condition(tpl.id, {'candidate_id': cand.id}, 'GT', '30')
    assert res['pass'] is False
    assert res['degraded'] is True
    assert res['error'] == '模板不存在或已失效'


@pytest.mark.django_db
def test_soft_deleted_template_degraded():
    """软删模板 → degraded True + pass False。"""
    tpl = _make_atomic_template('年龄限制', 'candidate.age', 'number', ['GT'])
    tpl.deleted_at = timezone.now()
    tpl.save(update_fields=['deleted_at'])
    cand = _make_candidate(age=32)
    res = MetricEngine.evaluate_metric_condition(tpl.id, {'candidate_id': cand.id}, 'GT', '30')
    assert res['pass'] is False
    assert res['degraded'] is True


@pytest.mark.django_db
def test_derived_missing_base_data_degraded():
    """派生指标 base_path 不在快照 → FieldResolveError → pass False + degraded(True)。"""
    metric = DerivedMetric.objects.create(
        name='空窗期', calc_func='MAX_GAP',
        base_path='candidate.nonexistentPath', data_type='number', unit='月',
    )
    tpl = MetricTemplate.objects.create(
        name='空窗期限制', derived_metric=metric, operators=['GT'],
    )
    cand = _make_candidate(age=32)
    res = MetricEngine.evaluate_metric_condition(tpl.id, {'candidate_id': cand.id}, 'GT', '6')
    assert res['pass'] is False
    assert res['degraded'] is True


@pytest.mark.django_db
def test_contains_on_string_metric():
    """METRIC 源 CONTAINS 字符串指标（审查补充覆盖）：name 含 '测试' → pass True。"""
    metric = AtomicMetric.objects.create(
        name=f'am_name_{_cid()}', source_path='candidate.name', data_type='string',
    )
    tpl = MetricTemplate.objects.create(
        name=f'name_{_cid()}', atomic_metric=metric,
        operators=['CONTAINS', 'NOT_CONTAINS'],
    )
    # _make_candidate 默认 name='测试候选人'，含子串 '测试'
    cand = _make_candidate()
    res = MetricEngine.evaluate_metric_condition(
        tpl.id, {'candidate_id': cand.id}, 'CONTAINS', '测试',
    )
    assert res['pass'] is True
    assert res['degraded'] is False


@pytest.mark.django_db
def test_between_via_meta():
    """METRIC 源 BETWEEN（审查补充覆盖）：age=40 在 [18,60] 内 → pass True（meta 承载 min/max）。"""
    tpl = _make_atomic_template('年龄区间', 'candidate.age', 'number', ['BETWEEN'])
    cand = _make_candidate(age=40)
    res = MetricEngine.evaluate_metric_condition(
        tpl.id, {'candidate_id': cand.id}, 'BETWEEN', None, meta={'min': 18, 'max': 60},
    )
    assert res['pass'] is True
    assert res['degraded'] is False


# ---------------------------------------------------------------------------
# 方案 B：指标 vs 指标（rightTemplateId 右操作数）
# ---------------------------------------------------------------------------
def _make_position_template(name, source_path, data_type='number', operators=None):
    """建 position.* 原子指标 + 模板（用于画像对比）。"""
    metric = AtomicMetric.objects.create(
        name=f'pos_{name}_{_cid()}', source_path=source_path, data_type=data_type,
    )
    return MetricTemplate.objects.create(
        name=f'pos_{name}_{_cid()}', atomic_metric=metric,
        operators=operators or ['GT', 'GTE', 'LT', 'LTE', 'EQ', 'NEQ', 'IS_EMPTY', 'IS_NOT_EMPTY'],
    )


def _exec_mv_m(left_tpl, right_tpl, data, operator='LTE'):
    return MetricEngine.execute(
        [{'templateId': left_tpl.id, 'operator': operator, 'rightTemplateId': right_tpl.id}],
        data,
    )


@pytest.mark.django_db
def test_metric_vs_metric_hit():
    """指标 vs 指标命中：candidate.age(32) <= position.salary_max(50) → pass True。"""
    left = _make_atomic_template('候选年龄', 'candidate.age', 'number', ['GT', 'GTE', 'LT', 'LTE'])
    right = _make_position_template('职位薪资上限', 'position.salary_max', 'number')
    data = {'candidate': {'age': 32}, 'position': {'salary_max': 50}}
    res = _exec_mv_m(left, right, data)
    step = res['steps'][0]
    assert res['pass'] is True
    assert step['degraded'] is False
    assert step['actual'] == 32
    assert step['expected'] == right.name  # metric-vs-metric 右值展示为对比模板名


@pytest.mark.django_db
def test_metric_vs_metric_miss():
    """指标 vs 指标未命中：candidate.age(32) > position.salary_max(20) → pass False。"""
    left = _make_atomic_template('候选年龄', 'candidate.age', 'number', ['GT', 'GTE', 'LT', 'LTE'])
    right = _make_position_template('职位薪资上限', 'position.salary_max', 'number')
    data = {'candidate': {'age': 32}, 'position': {'salary_max': 20}}
    res = _exec_mv_m(left, right, data)
    step = res['steps'][0]
    assert res['pass'] is False
    assert step['degraded'] is False


@pytest.mark.django_db
def test_metric_vs_metric_type_mismatch_degraded():
    """类型不一致（number vs string）→ 降级 degraded=True + pass False。"""
    left = _make_atomic_template('候选年龄', 'candidate.age', 'number', ['GT', 'GTE', 'LT', 'LTE'])
    right = _make_position_template('职位职级', 'position.level', 'string', ['EQ', 'NEQ'])
    data = {'candidate': {'age': 32}, 'position': {'level': 'P6'}}
    res = _exec_mv_m(left, right, data)
    step = res['steps'][0]
    assert res['pass'] is False
    assert step['degraded'] is True
    assert '类型不一致' in (step['error'] or '')


@pytest.mark.django_db
def test_metric_vs_metric_right_template_missing_degraded():
    """右模板不存在 → 降级 degraded=True + pass False。"""
    left = _make_atomic_template('候选年龄', 'candidate.age', 'number', ['GT', 'GTE', 'LT', 'LTE'])
    data = {'candidate': {'age': 32}, 'position': {}}
    res = MetricEngine.execute(
        [{'templateId': left.id, 'operator': 'LTE', 'rightTemplateId': 'nonexistent-id'}], data,
    )
    step = res['steps'][0]
    assert res['pass'] is False
    assert step['degraded'] is True
    assert '对比指标模板' in (step['error'] or '')


@pytest.mark.django_db
def test_metric_vs_metric_with_position_snapshot():
    """端到端：evaluate_metric_condition 经 position 快照解析右指标（职位薪资上限）。"""
    from apps.core.models import Department, User
    from apps.position.models import Position, PositionState
    from apps.process.models import RecruitmentProcess, StageStatus

    user = User.objects.create(username='mvm', email='mvm@x.com')
    dept = Department.objects.create(id='d-mvm-001', name='MVM', code='MVM')
    process = RecruitmentProcess.objects.create(
        id='p-mvm-001', code='MVMP', name='MVM 流程', current_version='V1.0',
        is_template=False, is_enabled=True, is_latest=True, status=StageStatus.ENABLED,
    )
    pos = Position.objects.create(
        id='pos-mvm-001', code='POSMVM', title='MVM 职位', department=dept,
        hiring_manager=user, owner=user, headcount=1, state=PositionState.DRAFT,
        process=process, salary_max=50,
    )
    left = _make_atomic_template('候选年龄', 'candidate.age', 'number', ['GT', 'GTE', 'LT', 'LTE'])
    right = _make_position_template('职位薪资上限', 'position.salary_max', 'number')
    cand = _make_candidate(age=32)
    res = MetricEngine.evaluate_metric_condition(
        left.id, {'candidate_id': cand.id, 'position_id': pos.id}, 'LTE', None,
        right_template_id=right.id,
    )
    assert res['pass'] is True
    assert res['degraded'] is False
    assert res['actual'] == 32
    assert res['expected'] == right.name  # metric-vs-metric 右值展示为对比模板名
