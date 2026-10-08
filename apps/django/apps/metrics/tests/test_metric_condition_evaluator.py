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
from nanoid import generate as nanoid_generate

from apps.candidate.models import Candidate
from apps.metrics.models import AtomicMetric, DerivedMetric, MetricTemplate
from apps.metrics.services.metric_engine import MetricEngine


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


# ===========================================================================
# 🔴 穿透回归测试（P0 修复）——防止方案 B「指标 vs 指标」再次静默劣化
#
# 背景：此前所有方案B 测试都通过 _exec_mv_m() 直接手搓 dict 调MetricEngine.execute，
# 绕过了 MetricRule.to_engine_conditions 与 RuleExecuteView._normalize。
# 结果：rightTemplateId 在三处透传被丢弃，生产路径 100% 失效，而 250 个测试全绿。
#
# 以下用例走**真实落库链路**，是防止该缺陷回归的唯一有效防线。
# 纪律：凡改条件/参数透传链路，必须补「落库 → 转换 → 执行」穿透测试。
# ===========================================================================


@pytest.mark.django_db
def test_p0_right_template_id_survives_to_engine_conditions():
    """【透传契约】rightTemplateId 必须存活 to_engine_conditions。

    这是 P0 修复的核心断言：修复前 to_engine_conditions 只透传 4 个键，
    rightTemplateId 被丢弃 → 方案 B 退化为常量比较（行为与配置无关）。
    """
    from apps.metrics.models import MetricRule, MetricRuleScene

    rule = MetricRule.objects.create(
        name=f'透传契约_{_cid()}',
        scene=MetricRuleScene.TALENT_POOL,
        logic='AND',
        conditions=[{
            'templateId': 'left-tpl-id',
            'operator': 'GTE',
            'rightTemplateId': 'right-tpl-id',
        }],
    )

    out = rule.to_engine_conditions()

    assert len(out) == 1
    assert out[0]['rightTemplateId'] == 'right-tpl-id', (
        'rightTemplateId 在 to_engine_conditions 中被丢弃 —— 方案 B 将退化为常量比较'
    )
    # 同时确认既有键未被破坏（防修复引入回归）
    assert out[0]['templateId'] == 'left-tpl-id'
    assert out[0]['operator'] == 'GTE'


@pytest.mark.django_db
def test_p0_right_template_id_survives_rule_execute_normalize():
    """【视图层透传契约】RuleExecuteView._normalize / _to_engine_conditions 必须保留 right_template_id。

    修复前 _normalize 只透传 4 键，导致 /rules/execute/ 端点也不支持方案 B，
    且 DRF 校验器（ConditionInputSerializer）根本拿不到该字段做类型校验。
    """
    from apps.metrics.views import RuleExecuteView

    payload = {
        'conditions': [{
            'templateId': 'left-tpl-id',
            'operator': 'GTE',
            'rightTemplateId': 'right-tpl-id',
        }],
    }

    normalized = RuleExecuteView._normalize(payload)
    assert normalized['conditions'][0]['right_template_id'] == 'right-tpl-id', (
        '_normalize 丢失 right_template_id —— 序列化器校验与方案 B 执行均失效'
    )

    engine_conds = RuleExecuteView._to_engine_conditions(normalized['conditions'])
    assert engine_conds[0]['rightTemplateId'] == 'right-tpl-id', (
        '_to_engine_conditions 丢失 rightTemplateId —— 配置即执行路径不支持方案 B'
    )


@pytest.mark.django_db
def test_p0_metric_vs_metric_end_to_end_via_persisted_rule():
    """【端到端穿透】落库规则 → to_engine_conditions → MetricEngine.execute 必须真正走指标 vs 指标。

    修复前：条件退化为「left >= value(None)」→ 恒定 pass False → VETO 规则拦截所有人。
    修复后：age(32) <= salary_max(50) → pass True。
    """
    from apps.metrics.models import MetricRule, MetricRuleScene

    left = _make_atomic_template('端到端年龄', 'candidate.age', 'number', ['GT', 'GTE', 'LT', 'LTE'])
    right = _make_position_template('端到端薪资上限', 'position.salary_max', 'number')

    rule = MetricRule.objects.create(
        name=f'端到端透传_{_cid()}',
        scene=MetricRuleScene.TALENT_POOL,
        logic='AND',
        conditions=[{
            'templateId': left.id,
            'operator': 'LTE',
            'rightTemplateId': right.id,
        }],
    )

    # 关键：走落库 → 转换 → 执行，而非手搓 dict
    res = MetricEngine.execute(
        rule.to_engine_conditions(),
        {'candidate': {'age': 32}, 'position': {'salary_max': 50}},
    )

    assert res['pass'] is True, '真实链路下方案 B 仍未生效（右值被丢弃 → 退化为常量比较）'
    step = res['steps'][0]
    assert step['degraded'] is False
    assert step['actual'] == 32
    assert step['expected'] == right.name  # 右值取自对比模板，而非常量


@pytest.mark.django_db
def test_p0_serializer_rejects_type_mismatch_on_persist():
    """【配置期守卫】左右指标类型不一致必须在**保存时**被拒（配置期拦截）。

    修复前：raise ValidationError 写在 try 块内被自己的 except Exception 吞掉，
    第一道防线失效。

    ⚠️ 变异测试发现（2026-10-07）：把比较移回 try 内后本用例**仍不红**——
    因为 services/rule_validators.py:101-112 另有一道独立校验（errors.append，不受 except 影响）。
    故 serializers 这道属**冗余加固**。本用例的价值在于：锁定 serializers 层行为，
    防止未来有人重构时把 raise 挪进 try 而无人察觉。两道防线需保持一致。
    """
    from apps.metrics.serializers import MetricRuleSerializer

    left = _make_atomic_template('守卫年龄', 'candidate.age', 'number', ['GT', 'GTE'])
    right = _make_position_template('守卫职级', 'position.level', 'string', ['EQ', 'NEQ'])

    serializer = MetricRuleSerializer(data={
        'name': f'类型守卫_{_cid()}',
        'scene': 'TALENT_POOL',
        'logic': 'AND',
        'conditions': [{
            'templateId': left.id,
            'operator': 'GTE',
            'rightTemplateId': right.id,
        }],
    })

    assert not serializer.is_valid(), '类型不一致却校验通过—— 守卫仍在被吞掉'
    assert '类型不一致' in str(serializer.errors)


@pytest.mark.django_db
def test_p0_serializer_allows_matching_types_on_persist():
    """【无假阳性】类型一致时必须放行（守卫不能变成「一律拒绝」）。"""
    from apps.metrics.serializers import MetricRuleSerializer

    left = _make_atomic_template('放行年龄', 'candidate.age', 'number', ['GT', 'GTE'])
    right = _make_position_template('放行薪资上限', 'position.salary_max', 'number')

    serializer = MetricRuleSerializer(data={
        'name': f'类型放行_{_cid()}',
        'scene': 'TALENT_POOL',
        'logic': 'AND',
        'conditions': [{
            'templateId': left.id,
            'operator': 'GTE',
            'rightTemplateId': right.id,
        }],
    })

    assert serializer.is_valid(), f'类型一致却被误拦: {serializer.errors}'


@pytest.mark.django_db
def test_p1_execute_degrades_disabled_template():
    """【P1/S-2 回归】主执行路径(_evaluate_condition)遇禁用模板必须降级，而非继续求值阻断业务。

    修复前 _evaluate_condition 只判 `template is None`，漏了禁用态判定 ——
    与 evaluate_metric_condition（进入条件路径，已判 status）方向相反。
    后果：管理员禁用模板后，入池/评分/筛选类规则仍用已失效模板求值并阻断业务（该关的没关）。

    本用例走 MetricEngine.execute 主路径（非 evaluate_metric_condition），是修复前零覆盖的漏洞点。
    """
    tpl = _make_atomic_template('S2年龄限制', 'candidate.age', 'number', ['GT'])
    tpl.status = 'disabled'
    tpl.save(update_fields=['status'])

    res = MetricEngine.execute(
        [{'templateId': tpl.id, 'operator': 'GT', 'value': '30'}],
        {'candidate': {'age': 32}},
    )
    assert res['pass'] is False
    assert res['steps'][0]['degraded'] is True, '禁用模板未被降级 —— 修复前会照常求值并阻断'
    assert res['steps'][0]['error'] == '模板不存在或已失效'


@pytest.mark.django_db
def test_p1_execute_degrades_soft_deleted_template():
    """【P1/S-2 回归】主执行路径(_evaluate_condition)遇软删模板必须降级。"""
    tpl = _make_atomic_template('S2软删', 'candidate.age', 'number', ['GT'])
    tpl.deleted_at = timezone.now()
    tpl.save(update_fields=['deleted_at'])

    res = MetricEngine.execute(
        [{'templateId': tpl.id, 'operator': 'GT', 'value': '30'}],
        {'candidate': {'age': 32}},
    )
    assert res['pass'] is False
    assert res['steps'][0]['degraded'] is True, '软删模板未被降级'
    assert res['steps'][0]['error'] == '模板不存在或已失效'


@pytest.mark.django_db
def test_p1_execute_enabled_template_still_evaluates():
    """【P1/S-2 无假阳性】启用态模板在主路径正常求值，禁用检查不得变成「一律拒绝」。"""
    tpl = _make_atomic_template('S2启用', 'candidate.age', 'number', ['GT'])
    # 默认 status='enabled'，无需改动

    res = MetricEngine.execute(
        [{'templateId': tpl.id, 'operator': 'GT', 'value': '30'}],
        {'candidate': {'age': 32}},
    )
    assert res['pass'] is True, '启用模板被误拦'
    assert res['steps'][0]['degraded'] is False
