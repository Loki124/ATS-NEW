"""LIFE-3 迁移命令测试：migrate_raw_conditions_to_metric。

覆盖：
    (a) test_dry_run_no_writes        —— dry-run 默认不写库，仅报告。
    (b) test_apply_migrates_with_atomic —— --apply 将进入条件 + 阶段规则裸路径项改写为 METRIC + 模板 id。
    (c) test_skip_when_no_atomic      —— 无对应 enabled AtomicMetric 的裸路径被 SKIP（不硬造 data_type）。
    (d) test_idempotent               —— 连续两次 --apply，第二次 migrated=0（幂等）。
    (e) test_evaluation_unchanged     —— 迁移前后同一 candidate 数据，METRIC 与裸路径解析出的 actual 一致（同源等价，无行为变化）。

fixture 必填字段照搬同目录 test_template_impact.py 已验证可跑通的组合。
纯后端数据命令，使用 pytest + pytest.mark.django_db，必要模型直接 ORM 创建。
"""
import io

import pytest
from django.core.management import call_command
from nanoid import generate as nanoid_generate

from apps.entry_condition.models import ConditionItem, EntryConditionRule
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
