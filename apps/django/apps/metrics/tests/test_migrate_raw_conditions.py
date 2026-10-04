"""LIFE-3 迁移命令测试：migrate_raw_conditions_to_metric。

覆盖：
    (a) test_dry_run_no_writes        —— dry-run 默认不写库，仅报告。
    (b) test_apply_migrates_with_atomic —— --apply 将进入条件 + 阶段规则裸路径项改写为 METRIC + 模板 id。
    (c) test_skip_when_no_atomic      —— 无对应 enabled AtomicMetric 的裸路径被 SKIP（不硬造 data_type）。
    (d) test_idempotent               —— 连续两次 --apply，第二次 migrated=0（幂等）。
    (e) test_evaluation_unchanged     —— 迁移前后同一 candidate 数据，METRIC 与裸路径解析出的 actual 一致（同源等价，无行为变化）。
    (f) test_normalize_legacy_path_unit —— _normalize_legacy_path 单元：仅规范化「全大写+下划线+无点」，其余原样。
    (g) test_legacy_upper_const_migrates —— legacy 大写常量 DEMAND_LEVEL 命中 demand.level 的 enabled AtomicMetric，可迁移。
    (h) test_legacy_upper_const_still_skips —— DEMAND_UNKNOWN 规范化后仍无匹配 → 仍 SKIP，不建模板、不改写。
    (i) test_standard_dot_path_unaffected  —— 标准点路径 candidate.age 走精确匹配，行为与修复前一致（回归）。
    (j) test_stage_rule_legacy_upper_json  —— StageRule skip_rules 里的 DEMAND_LEVEL 项同样被改写。
    (k) test_apply_never_produces_operator_incompatible —— 既有模板 operators 不含 EQ 时，
        --apply 要么迁到兼容模板（MetricEngine 求值不得报「模板不支持该运算符」），要么 SKIP；
        绝不允许「迁移成功但 operator 不在目标模板 operators 内」。
    (l) test_prefers_compatible_template   —— 存在兼容模板时优先复用兼容项（而非排序靠前的不兼容项）。
    (m) test_invalid_operator_skips        —— operator 不是合法 UnifiedOperator → SKIP，不建模板不改写。
    (n) test_apply_reports_normalized_hits —— --apply 分支也打印兜底映射提示并在报告汇总命中条数。
    (o) test_new_template_falls_back_to_second_candidate_name —— AtomicMetric.name 与既有模板
        同名 → 首个候选名撞 unique 触发 IntegrityError → 重试落到第二个候选名 `X (LIFE-3)`。
        （dev 真实路径：需求级别 am 与迁移 0018 种子模板天然同名，--apply 必走此分支。）
    (p) test_new_template_all_candidates_fail_skips —— 全部候选名都撞名 → 返回 None/SKIP，
        且因 create 包在 transaction.atomic() savepoint 内，嵌套事务下不抛
        TransactionManagementError、事务仍可用（QA 发现的 savepoint 缺失项）。
    (q) test_apply_merges_only_missing_operator —— P1 策略：无兼容模板时复用既有模板并**只**
        把缺失的那 1 个 operator 追加进 operators，不新建重复模板、不开全集。
    (r) test_dry_run_reports_merge_plan_without_writing —— dry-run 预测「复用既有模板并入 EQ」
        且零写入（既有模板 operators 不变、不新建模板、不改条件）。
    (s) test_new_template_operators_minimal_not_full_set —— 无任何既有模板时新建的模板
        operators 只含实际需要的那 1 个算子（绝不是 UnifiedOperator 全集 14 项）。
    (t) test_merge_preserves_existing_operators_and_conditions —— 并入是 append-only：
        既有算子全保留、引用该模板的既有 METRIC 条件不受影响、仍可正常求值。
    (u)(v)(w) E-1 可审计性：--apply 输出区分「并入/复用/新建」+ dry-run 计划清单。
    (x) E-2：STRING 字段 + 数值算子(GT) → SKIP，不并入、不建模板、不改写（禁假绿）。
    (y) E-2 回归：STRING 字段 + EQ → **仍并入**（dev 真实路径零影响）。
    (z) E-2：数值类(NUMBER)字段 + GT → **不受限，仍并入**（证明只对字符串类限制）。
    (A) E-2 单元：_operator_merge_policy 类型 × 算子允许/拒绝矩阵。
    (B) E-2 纵深防御：_create_minimal_template 自身也过门禁，字符串类字段遇数值/区间算子直接拒绝，
        绝不造出坏模板（即便不经 _resolve_template 直接调用）。

fixture 必填字段照搬同目录 test_template_impact.py 已验证可跑通的组合。
纯后端数据命令，使用 pytest + pytest.mark.django_db，必要模型直接 ORM 创建。
"""
import io

import pytest
from django.core.management import call_command
from django.db import transaction
from nanoid import generate as nanoid_generate

from apps.entry_condition.models import ConditionItem, EntryConditionRule
from apps.metrics.management.commands import migrate_raw_conditions_to_metric as cmd_mod
from apps.metrics.management.commands.migrate_raw_conditions_to_metric import (
    _is_string_data_type,
    _normalize_legacy_path,
    _operator_merge_policy,
    _resolve_atomic_metric,
)
from apps.metrics.models import (
    AtomicMetric,
    MetricDataType,
    MetricTemplate,
)
from apps.metrics.services.field_resolver import FieldResolverRegistry
from apps.metrics.services.metric_engine import MetricEngine
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
)
from apps.rule_engine.models import UnifiedOperator

pytestmark = pytest.mark.django_db

SOURCE_PATH = 'candidate.age'


def _new_id() -> str:
    return nanoid_generate(size=21)


def _build_context():
    """构造一套可落库的 流程 / 阶段 / 关联 上下文，返回 (process, stage, link)。"""
    process = RecruitmentProcess.objects.create(
        code=_new_id()[:12], name='tst_life3_流程',
        current_version='V1.0', version_seq=1, is_latest=True, status='ENABLED',
    )
    stage = RecruitmentStage.objects.create(
        code=_new_id()[:10], name='tst_life3_阶段', stage_type='SCREEN',
    )
    link = ProcessStageLink.objects.create(process=process, stage=stage, order=1)
    return process, stage, link


def _make_atomic() -> AtomicMetric:
    # 名称带 nanoid 后缀 → 跨 pytest 运行（--reuse-db 复用库）也能隔离，避免与历史残留模板冲突
    return AtomicMetric.objects.create(
        name=f'tst_life3_atomic_{_new_id()}', source_path=SOURCE_PATH,
        data_type=MetricDataType.NUMBER, status='enabled',
    )


def _make_atomic_at(source_path: str) -> AtomicMetric:
    """在指定 source_path 上创建 enabled AtomicMetric（名称带 nanoid 后缀以跨运行隔离）。

    用于 legacy 大写常量场景：AtomicMetric 存的是标准点路径（demand.level），
    而 ConditionItem.field 存的是 legacy 大写常量（DEMAND_LEVEL）。
    """
    return AtomicMetric.objects.create(
        name=f'tst_life3_atomic_{_new_id()}', source_path=source_path,
        data_type=MetricDataType.STRING, status='enabled',
    )


def _make_atomic_typed(source_path: str, data_type: str) -> AtomicMetric:
    """在指定 source_path 上创建**指定 data_type** 的 enabled AtomicMetric。

    用于 E-2「类型 × 算子」分级门禁：字符串类 vs 数值类字段必须走不同分支。
    """
    return AtomicMetric.objects.create(
        name=f'tst_life3_atomic_{_new_id()}', source_path=source_path,
        data_type=data_type, status='enabled',
    )


def _make_atomic_named(name: str, source_path: str) -> AtomicMetric:
    """创建**指定名称**的 enabled AtomicMetric（用于复刻「am.name 与既有模板同名」场景）。"""
    return AtomicMetric.objects.create(
        name=name, source_path=source_path,
        data_type=MetricDataType.STRING, status='enabled',
    )


def _make_raw_condition(link, field: str, operator: str, value, seq: int = 1) -> ConditionItem:
    """在给定 link 上建一条待迁移的裸路径进入条件项。"""
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name=f'tst_life3_rule_{_new_id()}',
    )
    return ConditionItem.objects.create(
        rule=rule, item_seq=seq, condition_type='DEMAND',
        field=field, operator=operator, value=value,
    )


def _run(stdout: io.StringIO, *args):
    call_command('migrate_raw_conditions_to_metric', *args, stdout=stdout)


# ============================================================================
# (a) dry-run 不写库
# ============================================================================
def test_dry_run_no_writes():
    am = _make_atomic()
    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_dryrun_rule',
    )
    ci = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='CANDIDATE',
        field=SOURCE_PATH, operator='GT', value=18,
    )

    out = io.StringIO()
    _run(out)  # 默认 dry-run

    # 未改写
    ci.refresh_from_db()
    assert ci.condition_type == 'CANDIDATE'
    assert ci.field == SOURCE_PATH
    # 未新建模板（dry-run 不写库，故不会触发 find-or-create）
    # 用「引用本测试 AtomicMetric 的模板数」做隔离断言（复用库可能已有其它种子模板）
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 0
    # 报告含 [DRY-RUN] 与 migrated 计数
    text = out.getvalue()
    assert '[DRY-RUN]' in text
    assert '已迁移：进入条件 1 条' in text


# ============================================================================
# (b) --apply 迁移进入条件 + 阶段规则
# ============================================================================
def test_apply_migrates_with_atomic():
    am = _make_atomic()
    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_apply_rule',
    )
    ci = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='CANDIDATE',
        field=SOURCE_PATH, operator='GT', value=18,
    )
    sr = StageRule.objects.create(
        link=link,
        skip_rules=[{
            'id': 'skip-1', 'name': 'tst_apply_skip', 'enabled': True,
            'scope': 'ALL', 'expression': '1', 'action': 'SKIP',
            'items': [
                {'condition_type': 'CANDIDATE', 'field': SOURCE_PATH,
                 'operator': 'GT', 'value': 18},
            ],
        }],
    )

    out = io.StringIO()
    _run(out, '--apply')

    # 进入条件项改写
    ci.refresh_from_db()
    assert ci.condition_type == 'METRIC'
    template = MetricTemplate.objects.get(atomic_metric=am)
    assert ci.field == str(template.id)
    # operator / value 不变
    assert ci.operator == 'GT'
    assert ci.value == 18

    # 阶段规则 skip_rules 项改写
    sr.refresh_from_db()
    item = sr.skip_rules[0]['items'][0]
    assert item['condition_type'] == 'METRIC'
    assert item['field'] == str(template.id)
    assert item['operator'] == 'GT'
    assert item['value'] == 18

    # 报告含 migrated 计数
    assert '已迁移：进入条件 1 条' in out.getvalue()
    assert 'skip/archive 项 1 条' in out.getvalue()


# ============================================================================
# (c) 无对应 enabled AtomicMetric → SKIP（不硬造）
# ============================================================================
def test_skip_when_no_atomic():
    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_skip_rule',
    )
    ci = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='CANDIDATE',
        field='candidate.unknown_field', operator='GT', value=18,
    )
    # 注意：未创建任何 AtomicMetric

    # 基线：复用库可能已有种子模板，故只断言本命令未新增模板（count 不变）
    before = MetricTemplate.objects.count()

    out = io.StringIO()
    _run(out, '--apply')

    # 未改写（仍 CANDIDATE，field 仍是未知路径）
    ci.refresh_from_db()
    assert ci.condition_type == 'CANDIDATE'
    assert ci.field == 'candidate.unknown_field'
    # 未新建任何模板（无对应 AtomicMetric，SKIP 分支不触发 find-or-create）
    assert MetricTemplate.objects.count() == before
    # 报告列出该路径
    assert 'candidate.unknown_field' in out.getvalue()


# ============================================================================
# (d) 幂等：连续两次 --apply，第二次 migrated=0
# ============================================================================
def test_idempotent():
    am = _make_atomic()
    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_idem_rule',
    )
    ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='CANDIDATE',
        field=SOURCE_PATH, operator='GT', value=18,
    )
    StageRule.objects.create(
        link=link,
        skip_rules=[{
            'id': 'skip-1', 'name': 'tst_idem_skip', 'enabled': True,
            'scope': 'ALL', 'expression': '1', 'action': 'SKIP',
            'items': [
                {'condition_type': 'CANDIDATE', 'field': SOURCE_PATH,
                 'operator': 'GT', 'value': 18},
            ],
        }],
    )

    out1 = io.StringIO()
    _run(out1, '--apply')
    assert '已迁移：进入条件 1 条' in out1.getvalue()

    out2 = io.StringIO()
    _run(out2, '--apply')
    text2 = out2.getvalue()
    # 第二次全部已是 METRIC，不再改写
    assert '已迁移：进入条件 0 条' in text2
    assert 'skip/archive 项 0 条' in text2
    # 模板仅 1 个（find-or-create，无重复创建；复用库可能已有其它种子模板，故按 atomic_metric 隔离断言）
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 1


# ============================================================================
# (e) 强证据：迁移不改变求值语义（同源等价）
# ============================================================================
def test_evaluation_unchanged():
    """迁移前后对同一份 candidate 数据，METRIC 路径与裸路径经 MetricEngine 解析出的 actual 一致。

    METRIC 求值最终按模板指向的 AtomicMetric.source_path 取值（与裸路径按同一点路径取值
    使用同一个 FieldResolverRegistry），故 actual 值应完全相同 —— 证明迁移零行为变化。
    """
    am = _make_atomic()
    template = MetricTemplate.objects.create(
        name=f'tst_life3_eval_template_{_new_id()}', atomic_metric=am,
        operators=list(UnifiedOperator.values), status='enabled',
    )

    # 同一份 candidate 快照数据（结构与 build_candidate_snapshot 产出一致）
    data = {'candidate': {'age': 30}}

    # 迁移前：裸路径 CANDIDATE 按 'candidate.age' 取值
    raw_actual = FieldResolverRegistry.resolve(SOURCE_PATH, data)
    # 迁移后：METRIC 经统一引擎取值（原子分支走 atomic_metric.source_path）
    engine_actual = MetricEngine._resolve_metric_value(template, template.metric, data)

    # 同源等价：actual 完全一致
    assert raw_actual == 30
    assert engine_actual == raw_actual

    # 比较语义一致：GT 18 在两种源下结果相同
    assert MetricEngine._compare('GT', raw_actual, 18, {}) is True
    assert MetricEngine._compare('GT', engine_actual, 18, {}) is True

    # 关键不变量：模板指向的 source_path 必须等于原裸路径（否则就不是同源迁移）
    assert template.metric_path == SOURCE_PATH


# ============================================================================
# (f) 单元：legacy 大写常量规范化（只作用于「全大写 + 含下划线 + 无点」）
# ============================================================================
def test_normalize_legacy_path_unit():
    # legacy 大写常量 → 标准点路径（只把**第一个**下划线换成点，整体转小写）
    assert _normalize_legacy_path('DEMAND_LEVEL') == 'demand.level'
    assert _normalize_legacy_path('CANDIDATE_WORK_YEARS') == 'candidate.work_years'
    assert _normalize_legacy_path('POSITION_CITY') == 'position.city'

    # 标准点路径：完全不受影响（原样返回）
    assert _normalize_legacy_path('candidate.age') == 'candidate.age'
    assert _normalize_legacy_path('demand.level') == 'demand.level'
    assert _normalize_legacy_path('candidate.workExperience.0.company') == (
        'candidate.workExperience.0.company')

    # 无下划线 / 非全大写 / 空 / 非字符串：一律原样返回
    assert _normalize_legacy_path('DEMANDLEVEL') == 'DEMANDLEVEL'
    assert _normalize_legacy_path('demand_level') == 'demand_level'
    assert _normalize_legacy_path('Demand_Level') == 'Demand_Level'
    assert _normalize_legacy_path('') == ''
    assert _normalize_legacy_path(None) is None
    assert _normalize_legacy_path(123) == 123

    # 解析函数：命中走规范化兜底，未命中返回 (None, 规范化候选 path)
    am = _make_atomic_at('demand.level')
    resolved_am, resolved_path = _resolve_atomic_metric('DEMAND_LEVEL')
    assert resolved_am is not None and resolved_am.pk == am.pk
    assert resolved_path == 'demand.level'

    # 精确匹配优先：即使可规范化，也优先返回原 field 路径
    am2 = _make_atomic_at('candidate.age')
    r_am, r_path = _resolve_atomic_metric('candidate.age')
    assert r_am is not None and r_am.pk == am2.pk
    assert r_path == 'candidate.age'

    # 查不到 → (None, 规范化候选 path)，调用方继续 SKIP
    miss_am, miss_path = _resolve_atomic_metric('DEMAND_UNKNOWN')
    assert miss_am is None
    assert miss_path == 'demand.unknown'


# ============================================================================
# (g) legacy 大写常量风格可迁移（原先被误判 SKIP 的真缺陷）
# ============================================================================
def test_legacy_upper_const_migrates():
    am = _make_atomic_at('demand.level')  # source_path 是标准点路径形态
    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_legacy_rule',
    )
    ci = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='DEMAND',
        field='DEMAND_LEVEL', operator='EQ', value='P1',
    )

    # --- dry-run：应报告「将改写」，不再被误判为 SKIP ---
    out = io.StringIO()
    _run(out)
    text = out.getvalue()
    assert f'将改写 ConditionItem {ci.id}' in text
    assert '已迁移：进入条件 1 条' in text
    assert 'SKIP(无对应 enabled AtomicMetric)' not in text
    # dry-run 零写入：不改写、不建模板
    ci.refresh_from_db()
    assert ci.condition_type == 'DEMAND'
    assert ci.field == 'DEMAND_LEVEL'
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 0

    # --- --apply：改写为 METRIC + 指向 demand.level 的模板 id ---
    out2 = io.StringIO()
    _run(out2, '--apply')
    ci.refresh_from_db()
    assert ci.condition_type == 'METRIC'
    template = MetricTemplate.objects.get(atomic_metric=am)
    assert ci.field == str(template.id)
    # 同源不变量：模板指向的 source_path 必须等于规范化后的 demand.level
    assert template.metric_path == 'demand.level'
    # operator / value 不变
    assert ci.operator == 'EQ'
    assert ci.value == 'P1'
    assert '已迁移：进入条件 1 条' in out2.getvalue()


# ============================================================================
# (h) 规范化后仍查不到 → 仍 SKIP（禁假绿不变）
# ============================================================================
def test_legacy_upper_const_still_skips():
    _make_atomic_at('demand.level')  # 只有 demand.level，没有 demand.unknown
    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_legacy_skip_rule',
    )
    ci = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='DEMAND',
        field='DEMAND_UNKNOWN', operator='EQ', value='X',
    )
    before = MetricTemplate.objects.count()

    out = io.StringIO()
    _run(out, '--apply')
    text = out.getvalue()

    # 不改写、不建模板
    ci.refresh_from_db()
    assert ci.condition_type == 'DEMAND'
    assert ci.field == 'DEMAND_UNKNOWN'
    assert MetricTemplate.objects.count() == before
    # 报告仍以原始 field 为键，并注明已尝试规范化为 demand.unknown
    assert 'DEMAND_UNKNOWN' in text
    assert '已迁移：进入条件 0 条' in text
    assert 'demand.unknown' in text


# ============================================================================
# (i) 回归：标准点路径走精确匹配，行为与修复前一致
# ============================================================================
def test_standard_dot_path_unaffected():
    am = _make_atomic()  # source_path = candidate.age
    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_dot_rule',
    )
    ci = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='CANDIDATE',
        field=SOURCE_PATH, operator='GT', value=18,
    )

    out = io.StringIO()
    _run(out)  # dry-run
    text = out.getvalue()
    assert f'将改写 ConditionItem {ci.id}' in text
    # 精确匹配即命中：不应出现「经规范化匹配」兜底标注
    assert '经规范化匹配' not in text

    _run(io.StringIO(), '--apply')
    ci.refresh_from_db()
    assert ci.condition_type == 'METRIC'
    template = MetricTemplate.objects.get(atomic_metric=am)
    assert ci.field == str(template.id)
    assert template.metric_path == SOURCE_PATH


# ============================================================================
# (j) StageRule JSON 路径：skip_rules 中的 DEMAND_LEVEL 项同样被改写
# ============================================================================
def test_stage_rule_legacy_upper_json():
    am = _make_atomic_at('demand.level')
    _, _, link = _build_context()
    sr = StageRule.objects.create(
        link=link,
        skip_rules=[{
            'id': 'skip-1', 'name': 'tst_legacy_skip', 'enabled': True,
            'scope': 'ALL', 'expression': '1', 'action': 'SKIP',
            'items': [
                {'condition_type': 'DEMAND', 'field': 'DEMAND_LEVEL',
                 'operator': 'EQ', 'value': 'P1'},
            ],
        }],
    )

    # --- dry-run ---
    out = io.StringIO()
    _run(out)
    text = out.getvalue()
    assert '将改写 StageRule' in text
    assert 'skip/archive 项 1 条' in text
    assert 'SKIP(无对应 enabled AtomicMetric)' not in text
    sr.refresh_from_db()  # dry-run 零写入
    assert sr.skip_rules[0]['items'][0]['condition_type'] == 'DEMAND'
    assert sr.skip_rules[0]['items'][0]['field'] == 'DEMAND_LEVEL'
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 0

    # --- --apply ---
    out2 = io.StringIO()
    _run(out2, '--apply')
    sr.refresh_from_db()
    item = sr.skip_rules[0]['items'][0]
    template = MetricTemplate.objects.get(atomic_metric=am)
    assert item['condition_type'] == 'METRIC'
    assert item['field'] == str(template.id)
    assert item['operator'] == 'EQ'
    assert item['value'] == 'P1'
    assert 'skip/archive 项 1 条' in out2.getvalue()


# ============================================================================
# (k) P0 防回归：绝不产出「operator 不在目标模板 operators 内」的迁移结果
# ============================================================================
def test_apply_never_produces_operator_incompatible():
    """既有 enabled 模板的 operators **不含 EQ** 时，--apply 必须二选一：

      - 迁到兼容模板（EQ ∈ template.operators，MetricEngine 求值不得报「模板不支持该运算符」）；
      - 或 SKIP（不迁移、不改写、不建不兼容模板）。

    dev 库真实场景：demand.level 的模板 C_dnKVVu2ONuR0mbaaKcx operators 不含 'EQ'，
    而待迁项 operator 全是 'EQ' —— 修复前会无脑复用，产出恒 False 的坏条件（静默拦截候选人）。
    """
    am = _make_atomic_at('demand.level')
    # 复刻 dev 库形态：指向该 am 的 enabled 模板，operators 不含 'EQ'
    incompatible = MetricTemplate.objects.create(
        name=f'tst_life3_nocompat_{_new_id()}', atomic_metric=am,
        operators=['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], status='enabled',
    )
    assert 'EQ' not in (incompatible.operators or [])

    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_nocompat_rule',
    )
    ci = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='DEMAND',
        field='demand.level', operator='EQ', value='1',
    )

    out = io.StringIO()
    _run(out, '--apply')
    ci.refresh_from_db()

    if ci.condition_type == 'METRIC':
        # 分支一：迁移成功 → 目标模板**必须是兼容的**（EQ 在白名单内）
        target = MetricTemplate.objects.get(pk=ci.field)
        assert 'EQ' in (target.operators or []), (
            f'迁移到不兼容模板 {target.id}，operators={target.operators}')
        # 硬证据：统一求值器不得再报「模板不支持该运算符」
        result = MetricEngine.evaluate_metric_condition(str(target.id), {}, 'EQ', '1')
        assert '模板不支持该运算符' not in (result.get('error') or ''), result
    else:
        # 分支二：SKIP → 不改写、不新建不兼容模板
        assert ci.condition_type == 'DEMAND'
        assert ci.field == 'demand.level'
        assert MetricTemplate.objects.filter(atomic_metric=am).count() == 1

    # 全局不变量：任何被本命令写出的 METRIC 项，其 operator 必在目标模板白名单内
    for migrated_ci in ConditionItem.objects.filter(condition_type='METRIC'):
        tpl = MetricTemplate.objects.filter(pk=migrated_ci.field).first()
        if tpl is not None:
            assert migrated_ci.operator in (tpl.operators or [])


# ============================================================================
# (l) 存在兼容模板时优先复用兼容项（而非排序靠前的不兼容项）
# ============================================================================
def test_prefers_compatible_template():
    """两个指向同一 am 的 enabled 模板：按 name 排序不兼容项在前，也必须选中兼容项。

    MetricTemplate.Meta.ordering = ['name']，故命名 A_*（不兼容，排前）/ Z_*（兼容，排后），
    修复前「取第一个」会命中 A_* → 恒 False；修复后必须命中 Z_*。
    """
    am = _make_atomic_at('demand.level')
    incompatible = MetricTemplate.objects.create(
        name=f'A_tst_life3_nocompat_{_new_id()}', atomic_metric=am,
        operators=['IS_EMPTY', 'IS_NOT_EMPTY'], status='enabled',
    )
    compatible = MetricTemplate.objects.create(
        name=f'Z_tst_life3_compat_{_new_id()}', atomic_metric=am,
        operators=list(UnifiedOperator.values), status='enabled',
    )
    assert 'EQ' not in (incompatible.operators or [])
    assert 'EQ' in (compatible.operators or [])

    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_prefer_rule',
    )
    ci = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='DEMAND',
        field='demand.level', operator='EQ', value='1',
    )

    out = io.StringIO()
    _run(out, '--apply')
    ci.refresh_from_db()

    assert ci.condition_type == 'METRIC'
    assert ci.field == str(compatible.id), '未优先复用兼容模板'
    assert ci.field != str(incompatible.id)
    # 未新建第三个模板（复用优先）
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 2
    # 求值器不再报运算符不支持
    result = MetricEngine.evaluate_metric_condition(str(compatible.id), {}, 'EQ', '1')
    assert '模板不支持该运算符' not in (result.get('error') or ''), result


# ============================================================================
# (m) operator 不是合法 UnifiedOperator → SKIP（不建模板、不改写）
# ============================================================================
def test_invalid_operator_skips():
    """全集模板也覆盖不了的非法运算符：dry-run 与 --apply 都按 SKIP 处理，绝不假绿迁移。"""
    am = _make_atomic_at('demand.level')
    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_badop_rule',
    )
    ci = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='DEMAND',
        field='demand.level', operator='NOT_A_REAL_OP', value='1',
    )

    # dry-run：预测即不可迁移，不计入 migrated
    out = io.StringIO()
    _run(out)
    text = out.getvalue()
    assert '已迁移：进入条件 0 条' in text
    assert 'SKIP(运算符不在任何可复用模板白名单' in text
    ci.refresh_from_db()
    assert ci.condition_type == 'DEMAND'
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 0

    # --apply：同样不改写、不建模板
    out2 = io.StringIO()
    _run(out2, '--apply')
    ci.refresh_from_db()
    assert ci.condition_type == 'DEMAND'
    assert ci.field == 'demand.level'
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 0
    assert '已迁移：进入条件 0 条' in out2.getvalue()


# ============================================================================
# (n) --apply 分支也留下兜底映射审计痕迹（P2）
# ============================================================================
def test_apply_reports_normalized_hits():
    """legacy 大写常量经规范化命中时，--apply 也要打印提示并在报告里汇总命中条数。"""
    _make_atomic_at('demand.level')
    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name='tst_audit_rule',
    )
    ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='DEMAND',
        field='DEMAND_LEVEL', operator='EQ', value='1',
    )

    out = io.StringIO()
    _run(out, '--apply')
    text = out.getvalue()

    # apply 分支打印兜底映射提示（不再只在 dry-run 出现）
    assert '已改写 ConditionItem' in text
    assert '经规范化匹配 DEMAND_LEVEL -> demand.level' in text
    # 报告新增汇总行
    assert '已用兜底映射命中：1 条' in text
    assert 'DEMAND_LEVEL -> demand.level: 1' in text


# ============================================================================
# (o) 覆盖 dev 真实路径：am.name 与既有模板同名 → 候选名重试（QA 覆盖缺口）
# ============================================================================
def test_new_template_falls_back_to_second_candidate_name():
    """AtomicMetric.name 与既有模板重名 → 首个候选名撞 unique → 重试落到第二个候选名。

    dev 真实形态：迁移 0018 把 `需求级别` 模板种子化，其 name 与 am.name 天然同名，
    --apply 时「新建模板」分支必走 IntegrityError 重试，此前无测试保护。
    """
    same_name = f'tst_life3_samename_{_new_id()[:8]}'
    # 占位模板：占用名字 same_name，但指向**另一个** am（故不构成兼容/并入候选）
    am_other = _make_atomic_named(f'{same_name}_other', 'candidate.other_path')
    MetricTemplate.objects.create(
        name=same_name, atomic_metric=am_other, operators=['IN'], status='enabled',
    )
    # 待迁移项指向的 am，其 name 与既有模板**同名**
    am = _make_atomic_named(same_name, 'demand.level')

    _, _, link = _build_context()
    ci = _make_raw_condition(link, 'demand.level', 'EQ', '1')

    out = io.StringIO()
    _run(out, '--apply')

    ci.refresh_from_db()
    assert ci.condition_type == 'METRIC'
    created = MetricTemplate.objects.get(atomic_metric=am)
    assert ci.field == str(created.id)
    # 第一个候选名撞 unique → 落到第二个候选名（可辨识后缀）
    assert created.name == f'{same_name} (LIFE-3)'
    # 只含实际需要的算子（非全集）
    assert created.operators == ['EQ']
    # 没把「同名占位模板」（指向另一个 am）误当成目标模板
    placeholder = MetricTemplate.objects.get(name=same_name)
    assert placeholder.atomic_metric_id == am_other.pk
    assert ci.field == str(created.id) != str(placeholder.id)
    # savepoint 生效：重试后事务仍可用，未被 needs_rollback 污染（否则此处会抛
    # TransactionManagementError —— 这正是 QA 指出的 savepoint 缺失症状）
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 1
    assert '已迁移：进入条件 1 条' in out.getvalue()


# ============================================================================
# (p) 全部候选名都失败 → 返回 None/SKIP，且嵌套事务下不炸（savepoint 缺失项）
# ============================================================================
def test_new_template_all_candidates_fail_skips(monkeypatch):
    """候选名全部撞 unique：不迁移、不改写、不新建模板，且事务保持可用。

    若 create 不包 transaction.atomic()，IntegrityError 会把连接置为 needs_rollback，
    在 pytest 的 atomic 包裹（或任何外层事务）中后续查询会抛 TransactionManagementError。
    """
    am = _make_atomic_at('demand.level')
    n1 = f'tst_life3_c1_{_new_id()[:8]}'
    n2 = f'tst_life3_c2_{_new_id()[:8]}'
    am_other = _make_atomic_named(f'{n1}_other', 'candidate.other_path')
    MetricTemplate.objects.create(
        name=n1, atomic_metric=am_other, operators=['IN'], status='enabled')
    MetricTemplate.objects.create(
        name=n2, atomic_metric=am_other, operators=['IN'], status='enabled')

    # 所有候选名都被占用（确定性构造，避免依赖随机串）
    monkeypatch.setattr(
        cmd_mod.Command, '_candidate_template_names',
        staticmethod(lambda base_name: [n1, n2]),
    )

    _, _, link = _build_context()
    ci = _make_raw_condition(link, 'demand.level', 'EQ', '1')
    before = MetricTemplate.objects.count()

    out = io.StringIO()
    # 显式再包一层事务：模拟「本命令被别的事务包裹调用」的真实风险场景
    with transaction.atomic():
        _run(out, '--apply')

    text = out.getvalue()
    # SKIP：不改写、不新建模板
    ci.refresh_from_db()
    assert ci.condition_type == 'DEMAND'
    assert ci.field == 'demand.level'
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 0
    assert MetricTemplate.objects.count() == before
    assert '已迁移：进入条件 0 条' in text
    assert 'SKIP(运算符不在任何可复用模板白名单' in text
    # 外层事务未被污染：命令跑完仍可正常查询（savepoint 生效的硬证据）
    assert MetricTemplate.objects.filter(name=n1).exists()


# ============================================================================
# (q) P1 新策略：无兼容模板 → 复用既有模板并**只**并入缺失的那 1 个算子
# ============================================================================
def test_apply_merges_only_missing_operator():
    """dev 真实形态（需求级别模板 operators 不含 EQ）下的最小侵入整改：
    不新建重复命名模板，只在既有模板上追加缺失的 EQ。
    """
    am = _make_atomic_at('demand.level')
    base_ops = ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN']
    existing = MetricTemplate.objects.create(
        name=f'tst_life3_existing_{_new_id()}', atomic_metric=am,
        operators=list(base_ops), status='enabled',
    )
    assert 'EQ' not in existing.operators

    _, _, link = _build_context()
    ci = _make_raw_condition(link, 'demand.level', 'EQ', '1')

    out = io.StringIO()
    _run(out, '--apply')

    ci.refresh_from_db()
    assert ci.condition_type == 'METRIC'
    assert ci.field == str(existing.id), '应复用既有模板，而非新建重复命名模板'
    # 未新建第二个模板
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 1
    # append-only：既有算子全保留，只多出缺失的 EQ
    existing.refresh_from_db()
    assert existing.operators == base_ops + ['EQ']
    assert len(existing.operators) == len(base_ops) + 1
    # 绝不开放无关算子（尤其不能是 UnifiedOperator 全集）
    for op in ('GT', 'GTE', 'LT', 'LTE', 'BETWEEN', 'REGEX_MATCH', 'CONTAINS'):
        assert op not in existing.operators
    assert set(existing.operators) != set(UnifiedOperator.values)
    # 迁移结果可求值：统一求值器不得报「模板不支持该运算符」
    result = MetricEngine.evaluate_metric_condition(str(existing.id), {}, 'EQ', '1')
    assert '模板不支持该运算符' not in (result.get('error') or ''), result
    assert '已迁移：进入条件 1 条' in out.getvalue()


# ============================================================================
# (r) dry-run 预测「并入既有模板」且严格零写入
# ============================================================================
def test_dry_run_reports_merge_plan_without_writing():
    am = _make_atomic_at('demand.level')
    base_ops = ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN']
    existing = MetricTemplate.objects.create(
        name=f'tst_life3_dryexisting_{_new_id()}', atomic_metric=am,
        operators=list(base_ops), status='enabled',
    )
    _, _, link = _build_context()
    ci = _make_raw_condition(link, 'demand.level', 'EQ', '1')

    out = io.StringIO()
    _run(out)  # 默认 dry-run
    text = out.getvalue()

    # 预测文案指向「复用既有模板 + 并入 EQ」，且彻底不再出现「全算子」
    assert '将复用既有模板' in text
    assert '并仅并入 EQ' in text
    assert '全算子' not in text
    assert '[DRY-RUN]' in text
    # 零写入：既有模板 operators 未被改动、未新建模板、条件未改写
    existing.refresh_from_db()
    assert existing.operators == base_ops
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 1
    ci.refresh_from_db()
    assert ci.condition_type == 'DEMAND'
    assert ci.field == 'demand.level'


# ============================================================================
# (s) 无既有模板时新建：operators 只含实际需要的算子（绝不是全集 14 项）
# ============================================================================
def test_new_template_operators_minimal_not_full_set():
    am = _make_atomic_at('demand.level')  # 该 am 下无任何模板
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 0

    _, _, link = _build_context()
    ci = _make_raw_condition(link, 'demand.level', 'EQ', '1')

    out = io.StringIO()
    _run(out, '--apply')

    ci.refresh_from_db()
    assert ci.condition_type == 'METRIC'
    created = MetricTemplate.objects.get(atomic_metric=am)
    assert ci.field == str(created.id)
    # 只含实际需要的 1 个算子，绝不是 UnifiedOperator 全集
    assert created.operators == ['EQ']
    assert len(created.operators) == 1
    assert set(UnifiedOperator.values) - set(created.operators)
    # 迁移结果仍可求值
    result = MetricEngine.evaluate_metric_condition(str(created.id), {}, 'EQ', '1')
    assert '模板不支持该运算符' not in (result.get('error') or ''), result


# ============================================================================
# (t) 并入是 append-only：既有算子与既有引用条件均不受影响
# ============================================================================
def test_merge_preserves_existing_operators_and_conditions():
    """评估「并入既有模板 operators 是否影响既有引用条件」的回归锁定：

    operators 只是启用算子白名单，追加 = 放宽。既有条件原本允许的运算符全部保留，
    其 operator / value / 目标模板 / 取值路径一字不改，故既有条件不会被破坏。
    """
    am = _make_atomic_at('demand.level')
    base_ops = ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN']
    existing = MetricTemplate.objects.create(
        name=f'tst_life3_ref_{_new_id()}', atomic_metric=am,
        operators=list(base_ops), status='enabled',
    )

    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name=f'tst_life3_ref_rule_{_new_id()}',
    )
    # 迁移前就已存在的 METRIC 条件，引用该模板、用 IN
    legacy_ref = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='METRIC',
        field=str(existing.id), operator='IN', value=['P1', 'P2'],
    )
    # 待迁移的裸路径项（EQ，不在既有白名单内）
    ConditionItem.objects.create(
        rule=rule, item_seq=2, condition_type='DEMAND',
        field='demand.level', operator='EQ', value='1',
    )

    out = io.StringIO()
    _run(out, '--apply')

    # 既有算子全部保留（append-only，绝不删改）
    existing.refresh_from_db()
    for op in base_ops:
        assert op in existing.operators
    assert 'EQ' in existing.operators

    # 既有引用条件一字未改，且仍可正常求值
    legacy_ref.refresh_from_db()
    assert legacy_ref.condition_type == 'METRIC'
    assert legacy_ref.field == str(existing.id)
    assert legacy_ref.operator == 'IN'
    assert legacy_ref.value == ['P1', 'P2']
    result = MetricEngine.evaluate_metric_condition(
        str(existing.id), {}, 'IN', ['P1', 'P2'])
    assert '模板不支持该运算符' not in (result.get('error') or ''), result


# ============================================================================
# (u) E-1：--apply 输出必须能区分「并入放宽 / 复用兼容 / 新建」
# ============================================================================
def test_apply_output_distinguishes_merge_from_reuse():
    """并入是对全局共享模板的永久配置面变更且不可回滚，故 apply 输出 + 报告都必须留痕。

    修复前 --apply 只有 `[模板 X]`，与「复用了本就兼容的模板」字面完全无法区分，
    事后无法回答「这条命令到底改了哪些模板、从几个算子变到几个」。
    """
    am = _make_atomic_at('demand.level')
    base_ops = ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN']
    existing = MetricTemplate.objects.create(
        name=f'tst_life3_audit_{_new_id()}', atomic_metric=am,
        operators=list(base_ops), status='enabled',
    )
    _, _, link = _build_context()
    ci = _make_raw_condition(link, 'demand.level', 'EQ', '1')

    out = io.StringIO()
    _run(out, '--apply')
    text = out.getvalue()

    # 1) 单条输出明确写出「并入 + 算子」与 operators 前后变化
    assert f'并入 +EQ 到既有模板 {existing.id}' in text
    assert 'operators 4→5' in text
    # 与「复用本就兼容的模板」字面可区分（后者仍为 `[模板 X]`）
    assert f'[模板 {existing.id}]' not in text
    # 2) 报告汇总「已放宽既有模板白名单」（含模板名/id 与前后白名单）
    assert '已放宽既有模板白名单（共享实体，不可回滚）：1 个' in text
    assert f'{existing.name} ({existing.id})' in text
    assert (
        '[IS_EMPTY, IS_NOT_EMPTY, IN, NOT_IN] → '
        '[IS_EMPTY, IS_NOT_EMPTY, IN, NOT_IN, EQ]'
    ) in text
    # 3) 输出层改动不得影响写入行为（回归锁定）
    ci.refresh_from_db()
    assert ci.condition_type == 'METRIC'
    assert ci.field == str(existing.id)
    existing.refresh_from_db()
    assert existing.operators == base_ops + ['EQ']


# ============================================================================
# (v) E-1：新建 / 复用 同样字面可区分；无放宽时报告显式打印 0 个
# ============================================================================
def test_apply_output_marks_new_and_reuse_separately():
    """同一 am 下两条同算子条件：首条新建模板、次条复用它 —— 输出必须各自可辨。"""
    am = _make_atomic()
    _, _, link = _build_context()
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process_id,
        workflow_version='V1.0', rule_name=f'tst_life3_newreuse_{_new_id()}',
    )
    ci1 = ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='CANDIDATE',
        field=SOURCE_PATH, operator='GT', value=18,
    )
    ci2 = ConditionItem.objects.create(
        rule=rule, item_seq=2, condition_type='CANDIDATE',
        field=SOURCE_PATH, operator='GT', value=20,
    )

    out = io.StringIO()
    _run(out, '--apply')
    text = out.getvalue()

    created = MetricTemplate.objects.get(atomic_metric=am)
    # 新建：写出模板 id 与实际写入的 operators
    assert f'新建模板 {created.id} operators=[GT]' in text
    # 复用（同一模板被第二条命中兼容）：回落到 `[模板 X]`，不重复报「新建」
    assert f'[模板 {created.id}]' in text
    assert '并入' not in text
    # 无共享模板被放宽 → 报告显式打印 0 个（可证明「没改任何既有模板」）
    assert '已放宽既有模板白名单：0 个' in text
    for migrated_ci, expected in ((ci1, 18), (ci2, 20)):
        migrated_ci.refresh_from_db()
        assert migrated_ci.condition_type == 'METRIC'
        assert migrated_ci.field == str(created.id)
        assert migrated_ci.value == expected


# ============================================================================
# (w) E-1：dry-run 报告给出同一份「计划放宽」清单，且仍严格零写入
# ============================================================================
def test_dry_run_report_lists_planned_relaxed_templates():
    """dry-run 也要显示「哪些共享模板会被放宽」的计划，与 apply 口径一致。"""
    am = _make_atomic_at('demand.level')
    base_ops = ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN']
    existing = MetricTemplate.objects.create(
        name=f'tst_life3_plan_{_new_id()}', atomic_metric=am,
        operators=list(base_ops), status='enabled',
    )
    _, _, link = _build_context()
    ci = _make_raw_condition(link, 'demand.level', 'EQ', '1')

    out = io.StringIO()
    _run(out)  # 默认 dry-run
    text = out.getvalue()

    # 计划清单（措辞为「将放宽」，与 apply 的「已放宽」区分）
    assert '将放宽既有模板白名单（共享实体，不可回滚）：1 个' in text
    assert f'{existing.name} ({existing.id})' in text
    assert (
        '[IS_EMPTY, IS_NOT_EMPTY, IN, NOT_IN] → '
        '[IS_EMPTY, IS_NOT_EMPTY, IN, NOT_IN, EQ]'
    ) in text
    # 既有 dry-run 文案保持不变（不引入矛盾）
    assert '将复用既有模板' in text
    assert '并仅并入 EQ' in text
    # 零写入不变：白名单未改、未新建模板、条件未改写
    existing.refresh_from_db()
    assert existing.operators == base_ops
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 1
    ci.refresh_from_db()
    assert ci.condition_type == 'DEMAND'
    assert ci.field == 'demand.level'


# ============================================================================
# (x) E-2：STRING 字段 + 数值算子 GT → SKIP，不并入、不建模板、不改写
# ============================================================================
def test_string_field_numeric_operator_skips():
    """「职级 > 5」这类配置绝不能由本命令产出：字符串类字段 + 数值/区间算子 → SKIP。

    并入「缺失的那 1 个算子」把风险幅度从 14 降到 1，但风险类别没变：仍是把算子写进
    全局共享模板白名单（经 apps/process/views.py:958 透传给前端运算符下拉）。若待迁项
    operator 是 GT 而目标字段是字符串类（demand.level = CharField 职级），并入会让
    「职级 > 5」变成可配配置 → 字符串比较 → **求值静默 False**（配置能存、求值恒 False
    的假及格）。故必须 SKIP + 报告，绝不硬造。

    本测试同时覆盖两条「写白名单」的路径：
      - 有既有模板 → 拒绝**并入**（operators 保持原样）；
      - 无既有模板 → 拒绝**新建**（模板数保持 0）。
    """
    base_ops = ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN']
    # 场景一：有既有启用模板可并入（GT 不在其白名单内）
    am_merge = _make_atomic_typed('demand.level', MetricDataType.STRING)
    existing = MetricTemplate.objects.create(
        name=f'tst_life3_strmerge_{_new_id()}', atomic_metric=am_merge,
        operators=list(base_ops), status='enabled',
    )
    # 场景二：该 am 下无任何模板（否则会走「新建最小算子模板」路径）
    am_new = _make_atomic_typed('demand.grade', MetricDataType.STRING)
    assert MetricTemplate.objects.filter(atomic_metric=am_new).count() == 0

    _, _, link = _build_context()
    ci_merge = _make_raw_condition(link, 'demand.level', 'GT', 5, seq=1)
    ci_new = _make_raw_condition(link, 'demand.grade', 'GT', 5, seq=2)

    # --- dry-run：两条都被预测为 SKIP，且计划文案点明「类型不适用」 ---
    out = io.StringIO()
    _run(out)
    text = out.getvalue()
    assert '已迁移：进入条件 0 条' in text
    assert 'SKIP 运算符 GT 不适用于 STRING 字段 demand.level' in text
    assert 'SKIP 运算符 GT 不适用于 STRING 字段 demand.grade' in text
    # 报告给出对应提示（独立桶，与「无兼容模板」桶区分）
    assert 'SKIP(运算符不适用于该字段数据类型' in text
    assert 'demand.level [GT]: 1' in text
    # 零写入：白名单未改、未新建模板、条件未改写
    existing.refresh_from_db()
    assert existing.operators == base_ops
    assert MetricTemplate.objects.filter(atomic_metric=am_new).count() == 0
    for ci in (ci_merge, ci_new):
        ci.refresh_from_db()
        assert ci.condition_type == 'DEMAND'

    # --- --apply：同样不并入、不建模板、不改写 ---
    out2 = io.StringIO()
    _run(out2, '--apply')
    text2 = out2.getvalue()
    assert '已迁移：进入条件 0 条' in text2
    assert 'SKIP(运算符不适用于该字段数据类型' in text2
    existing.refresh_from_db()
    assert existing.operators == base_ops, 'GT 绝不能被并入字符串类字段的共享白名单'
    assert MetricTemplate.objects.filter(atomic_metric=am_merge).count() == 1
    assert MetricTemplate.objects.filter(atomic_metric=am_new).count() == 0
    for ci in (ci_merge, ci_new):
        ci.refresh_from_db()
        assert ci.condition_type == 'DEMAND'
        assert ci.field in ('demand.level', 'demand.grade')
        assert ci.operator == 'GT'


# ============================================================================
# (y) E-2 回归：STRING 字段 + EQ → 仍并入（dev 真实路径零影响）
# ============================================================================
def test_string_field_eq_still_merges():
    """门禁不得误伤 dev 真实路径：字符串类字段 + 字符串安全算子 EQ → 照旧并入。

    dev 库那 3 条待迁项全是 DEMAND_LEVEL + EQ，修复后必须**仍然走并入**，
    输出与修复前完全一致（[将复用既有模板 X 并仅并入 EQ] + 「将放宽」1 个 + 4→5）。
    """
    am = _make_atomic_typed('demand.level', MetricDataType.STRING)
    base_ops = ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN']
    existing = MetricTemplate.objects.create(
        name=f'tst_life3_eqmerge_{_new_id()}', atomic_metric=am,
        operators=list(base_ops), status='enabled',
    )
    _, _, link = _build_context()
    ci = _make_raw_condition(link, 'demand.level', 'EQ', '1')

    # --- dry-run：仍是「并入 EQ」的预测，绝无类型门禁痕迹 ---
    out = io.StringIO()
    _run(out)
    text = out.getvalue()
    assert f' [将复用既有模板 {existing.id} 并仅并入 EQ]' in text
    assert '不适用于 STRING 字段' not in text
    assert '已迁移：进入条件 1 条' in text
    assert '将放宽既有模板白名单（共享实体，不可回滚）：1 个' in text
    assert (
        '[IS_EMPTY, IS_NOT_EMPTY, IN, NOT_IN] → '
        '[IS_EMPTY, IS_NOT_EMPTY, IN, NOT_IN, EQ]'
    ) in text

    # --- --apply：照旧并入（append-only） ---
    out2 = io.StringIO()
    _run(out2, '--apply')
    text2 = out2.getvalue()
    ci.refresh_from_db()
    assert ci.condition_type == 'METRIC'
    assert ci.field == str(existing.id)
    existing.refresh_from_db()
    assert existing.operators == base_ops + ['EQ']
    assert f'并入 +EQ 到既有模板 {existing.id}' in text2
    assert 'operators 4→5' in text2
    assert '已放宽既有模板白名单（共享实体，不可回滚）：1 个' in text2
    assert '不适用于 STRING 字段' not in text2


# ============================================================================
# (z) E-2：数值类字段 + GT → 不受限，仍并入（证明只对字符串类做限制）
# ============================================================================
def test_number_field_gt_still_merges():
    """数值类（NUMBER）字段不做任何限制：GT 照旧并入，行为与门禁前完全一致。"""
    am = _make_atomic_typed('candidate.age', MetricDataType.NUMBER)
    base_ops = ['EQ', 'NEQ', 'IS_EMPTY']
    existing = MetricTemplate.objects.create(
        name=f'tst_life3_nummerge_{_new_id()}', atomic_metric=am,
        operators=list(base_ops), status='enabled',
    )
    assert 'GT' not in existing.operators

    _, _, link = _build_context()
    ci = _make_raw_condition(link, 'candidate.age', 'GT', 18)

    # --- dry-run：预测仍是「并入 GT」 ---
    out = io.StringIO()
    _run(out)
    text = out.getvalue()
    assert f' [将复用既有模板 {existing.id} 并仅并入 GT]' in text
    assert '不适用于 NUMBER 字段' not in text
    assert '已迁移：进入条件 1 条' in text

    # --- --apply：照旧并入 ---
    out2 = io.StringIO()
    _run(out2, '--apply')
    ci.refresh_from_db()
    assert ci.condition_type == 'METRIC'
    assert ci.field == str(existing.id)
    existing.refresh_from_db()
    assert existing.operators == base_ops + ['GT']
    assert '已迁移：进入条件 1 条' in out2.getvalue()
    # 迁移结果可求值：统一求值器不得报「模板不支持该运算符」
    result = MetricEngine.evaluate_metric_condition(str(existing.id), {}, 'GT', 18)
    assert '模板不支持该运算符' not in (result.get('error') or ''), result


# ============================================================================
# (A) E-2 单元：「类型 × 算子」分级矩阵
# ============================================================================
def test_operator_merge_policy_matrix():
    """分级函数单元：覆盖各 data_type × 各算子的允许/拒绝要点。"""
    string_safe = ['EQ', 'NEQ', 'IN', 'NOT_IN', 'IS_EMPTY', 'IS_NOT_EMPTY',
                   'CONTAINS', 'NOT_CONTAINS', 'REGEX_MATCH']
    numeric_or_range = ['GT', 'GTE', 'LT', 'LTE', 'BETWEEN']

    # --- 字符串类：安全算子全部允许；数值/区间算子全部拒绝 ---
    for op in string_safe:
        allowed, reason = _operator_merge_policy(MetricDataType.STRING, op)
        assert allowed is True, f'STRING + {op} 应允许并入'
        assert reason == ''
    for op in numeric_or_range:
        allowed, reason = _operator_merge_policy(MetricDataType.STRING, op)
        assert allowed is False, f'STRING + {op} 必须拒绝（否则产出恒 False 配置）'
        assert f'运算符 {op} 不适用于 STRING 字段' == reason

    # --- 非字符串类：一律不做限制（行为不变）---
    for data_type in (MetricDataType.NUMBER, MetricDataType.DATE,
                      MetricDataType.BOOLEAN):
        for op in string_safe + numeric_or_range:
            allowed, reason = _operator_merge_policy(data_type, op)
            assert allowed is True, f'{data_type} + {op} 不应受门禁限制'
            assert reason == ''
    # 裸字符串形态（历史脏数据 / JSON 值）同样按数值类处理
    assert _operator_merge_policy('number', 'GT') == (True, '')
    assert _operator_merge_policy('date', 'BETWEEN') == (True, '')
    # 大小写/空格归一
    assert _operator_merge_policy('STRING', 'GT')[0] is False
    assert _operator_merge_policy(' String ', 'GT')[0] is False

    # --- 边界：空运算符不参与判定（交由既有「运算符为空」分支，零行为变化）---
    assert _operator_merge_policy(MetricDataType.STRING, '') == (True, '')
    assert _operator_merge_policy(MetricDataType.STRING, None) == (True, '')
    # --- 边界：非法运算符一律拒绝（纵深防御）---
    allowed, reason = _operator_merge_policy(MetricDataType.STRING, 'NOT_A_REAL_OP')
    assert allowed is False and '非合法 UnifiedOperator' in reason
    # --- 边界：data_type 取不到（None / 派生模板）→ 不限制，绝不误伤既有路径 ---
    assert _operator_merge_policy(None, 'GT') == (True, '')

    # --- 类型判定辅助函数 ---
    assert _is_string_data_type(MetricDataType.STRING) is True
    assert _is_string_data_type('string') is True
    assert _is_string_data_type('STRING') is True
    assert _is_string_data_type(MetricDataType.NUMBER) is False
    assert _is_string_data_type(MetricDataType.DATE) is False
    assert _is_string_data_type(MetricDataType.BOOLEAN) is False
    assert _is_string_data_type(None) is False


# ============================================================================
# (B) E-2 纵深防御不变量：_create_minimal_template 自身也过「类型 × 算子」门禁
# ============================================================================
def test_create_minimal_template_gate_blocks_string_numeric_operator():
    """_create_minimal_template 是写白名单的另一入口；即便不经 _resolve_template 直接调用，

    也必须在入口处拦下「字符串类字段 + 数值/区间算子」，绝不造出含 GT/BETWEEN 的模板

    （否则「职级 > 5」会变成可配却恒 False 的假及格配置）。

    这是 E-2 纵深防御的最后一环：让「没有任何写路径能绕过 _operator_merge_policy」成为可测不变量。
    """
    am = _make_atomic_typed('candidate.work_years', MetricDataType.STRING)
    # 最小命令实例：仅设置命令所需的 stdout/stderr 与审计状态（与生产 execute() 等价子集）
    cmd = cmd_mod.Command()
    cmd.stdout = io.StringIO()
    cmd.stderr = io.StringIO()
    cmd._reset_audit_state()

    # --- 字符串字段 + GT → 必须被门禁拦下，不建任何模板 ---
    created = cmd._create_minimal_template(am, 'GT')
    assert created is None
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 0

    # --- 字符串字段 + BETWEEN → 同样拒绝 ---
    created_range = cmd._create_minimal_template(am, 'BETWEEN')
    assert created_range is None
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 0

    # --- 字符串字段 + 安全算子 EQ → 仍正常建出「只含 EQ」的模板（不影响既有真路径）---
    created_ok = cmd._create_minimal_template(am, 'EQ')
    assert created_ok is not None
    assert created_ok.atomic_metric_id == am.id
    assert created_ok.operators == ['EQ']
    # 全库仅此一条新建模板（BETWEEN/GT 两次调用均未落库）
    assert MetricTemplate.objects.filter(atomic_metric=am).count() == 1

    # --- 数值类字段不受限：即便不经上游，新建 GT 也应放行（证明只对字符串类限制）---
    am_num = _make_atomic_typed('candidate.age', MetricDataType.NUMBER)
    cmd2 = cmd_mod.Command()
    cmd2.stdout = io.StringIO()
    cmd2.stderr = io.StringIO()
    cmd2._reset_audit_state()
    created_num = cmd2._create_minimal_template(am_num, 'GT')
    assert created_num is not None
    assert created_num.operators == ['GT']
