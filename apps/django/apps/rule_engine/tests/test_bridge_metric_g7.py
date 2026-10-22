"""G7：bridge 携带 metric_template —— 镜像规则与源规则的指标求值口径一致。

背景
====
entry_condition 把「指标模板 id」直接存在 ``ConditionItem.field`` 里
（见 ``entry_condition.services._resolve_metric_template``），源侧求值时
``_get_actual_value`` 先按 field 查 MetricTemplate，命中就走 MetricEngine。

镜像到统一表（``sync_entry_condition_rule_to_unified``）时若不把这个语义带过去，
统一侧 ``ConditionEvaluator._is_metric_condition`` 看不到 ``value_type=METRIC`` /
``metric_template``，会把 field 当普通字段名解析 —— 于是
**同一条源规则，源侧走指标引擎、镜像侧走字段解析，两者结论可能不一致**。
这就是评估文档 §5 登记的 G7「一致性缺口」。

覆盖点
======
1. field 命中指标模板 -> 镜像 Condition 带 value_type=METRIC + metric_template=FK。
2. field 未命中（存量字段名 / legacy 键）-> value_type=FIELD + metric_template=None，
   存量行为零变化（双读兼容）。
3. 镜像幂等：二次同步后 METRIC 语义仍在（bridge 会 delete 后重建条件，必须每次重算）。
4. 模板解析异常 -> 按 FIELD 镜像且不抛（bridge 是 best-effort，不得因指标模块异常整体失败）。
5. 同一规则内 FIELD + METRIC 混合条件，逐条独立判定。
6. 软删模板 -> 视为非指标条件（与源侧 ``_resolve_metric_template`` 同口径）。
"""
from unittest.mock import MagicMock, patch

import pytest

from apps.entry_condition.models import ConditionItem, EntryConditionRule
from apps.metrics.models import AtomicMetric, MetricTemplate
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage
from apps.rule_engine.bridge import (
    _condition_metric_fields,
    sync_entry_condition_rule_to_unified,
)
from apps.rule_engine.models import ConditionValueType

pytestmark = pytest.mark.django_db

METRIC_LOOKUP = 'apps.metrics.models.MetricTemplate.objects.filter'


def _uniq(prefix: str) -> str:
    import uuid
    return f'{prefix}{uuid.uuid4().hex[:8]}'


def _make_link():
    proc = RecruitmentProcess.objects.create(
        code=_uniq('G7W'), name=_uniq('G7流程'),
        current_version='V1.0', version_seq=1,
        is_latest=True, status='ENABLED',
    )
    stage = RecruitmentStage.objects.create(
        code=_uniq('G7S'), name=_uniq('G7阶段'), stage_type='SCREEN',
    )
    link = ProcessStageLink.objects.create(
        process=proc, stage=stage, order=1, is_required=True,
    )
    return proc, stage, link


def _make_rule(link, **kwargs):
    defaults = dict(
        link=link, process_id=link.process.id, workflow_version='V1.0',
        rule_name=_uniq('G7准入'), rule_seq=1, status='ENABLED',
        expression='1', reject_message='不满足条件',
    )
    defaults.update(kwargs)
    return EntryConditionRule.objects.create(**defaults)


def _make_metric_template(source_path='candidate.age'):
    """建一条真实的原子指标模板（FK 必须是真实实例，不能用 mock）。"""
    metric = AtomicMetric.objects.create(
        name=f'am_{_uniq("g7")}', source_path=source_path,
        data_type='number', unit='岁',
    )
    return MetricTemplate.objects.create(
        name=_uniq('G7模板'), atomic_metric=metric,
        operators=['GT', 'LT', 'EQ'],
    )


def _item(rule, *, seq=1, condition_type='METRIC', field=None, operator='GT', value=18):
    return ConditionItem.objects.create(
        rule=rule, item_seq=seq, condition_type=condition_type,
        field=field if field is not None else _uniq('fld'),
        operator=operator, value=value,
    )


# ---------------------------------------------------------------------------
# 1) 命中指标模板 -> METRIC 语义被携带
# ---------------------------------------------------------------------------

def test_bridge_carries_metric_template():
    """field=模板 id 的条件项，镜像后应带 value_type=METRIC + metric_template FK。"""
    _, _, link = _make_link()
    rule = _make_rule(link)
    tpl = _make_metric_template()
    _item(rule, field=tpl.pk)

    unified = sync_entry_condition_rule_to_unified(rule)

    cond = unified.conditions.get(seq=1)
    assert cond.value_type == ConditionValueType.METRIC, \
        '指标条件镜像后必须标记为 METRIC，否则统一侧会当普通字段名解析（G7 缺口）'
    assert cond.metric_template_id == tpl.pk, \
        'metric_template FK 必须带上，供 _is_metric_condition 双读命中'
    # 原始字段仍保留（双读：field 继续存模板 id，与源侧口径一致）
    assert cond.field == tpl.pk


def test_bridge_non_metric_stays_field():
    """未命中模板的存量字段名 -> value_type=FIELD + metric_template=None（零行为变更）。"""
    _, _, link = _make_link()
    rule = _make_rule(link)
    _item(rule, condition_type='CANDIDATE', field='GENDER', operator='EQ', value='M')

    unified = sync_entry_condition_rule_to_unified(rule)

    cond = unified.conditions.get(seq=1)
    assert cond.value_type == ConditionValueType.FIELD
    assert cond.metric_template_id is None
    assert cond.field == 'GENDER'


# ---------------------------------------------------------------------------
# 2) 幂等：二次同步仍带 METRIC 语义
# ---------------------------------------------------------------------------

def test_bridge_metric_is_idempotent():
    """bridge 会 delete 后重建条件，METRIC 语义必须每次重算出来，不能只在首次生效。"""
    _, _, link = _make_link()
    rule = _make_rule(link)
    tpl = _make_metric_template()
    _item(rule, field=tpl.pk)

    first = sync_entry_condition_rule_to_unified(rule)
    second = sync_entry_condition_rule_to_unified(rule)

    assert second.id == first.id, '镜像应幂等复用同一条 Rule'
    cond = second.conditions.get(seq=1)
    assert cond.value_type == ConditionValueType.METRIC
    assert cond.metric_template_id == tpl.pk


# ---------------------------------------------------------------------------
# 3) 指标模块异常不得阻断镜像
# ---------------------------------------------------------------------------

def test_bridge_survives_metric_lookup_error():
    """指标模板查询抛异常 -> 按 FIELD 镜像且不抛，bridge 保持 best-effort。"""
    _, _, link = _make_link()
    rule = _make_rule(link)
    _item(rule, field='some_template_id')

    def _boom(*args, **kwargs):
        raise RuntimeError('metrics 模块炸了')

    with patch(METRIC_LOOKUP, side_effect=_boom):
        unified = sync_entry_condition_rule_to_unified(rule)

    cond = unified.conditions.get(seq=1)
    assert cond.value_type == ConditionValueType.FIELD, '解析失败按非指标条件处理'
    assert cond.metric_template_id is None
    assert unified.conditions.count() == 1, '镜像本身必须成功，不得因指标异常丢规则'


# ---------------------------------------------------------------------------
# 4) 混合规则逐条独立判定
# ---------------------------------------------------------------------------

def test_bridge_mixed_field_and_metric():
    """同一规则内 FIELD 与 METRIC 条件并存，逐条独立判定，互不影响。"""
    _, _, link = _make_link()
    rule = _make_rule(link, expression='1 AND 2')
    tpl = _make_metric_template()
    _item(rule, seq=1, condition_type='CANDIDATE', field='GENDER', operator='EQ', value='M')
    _item(rule, seq=2, condition_type='METRIC', field=tpl.pk)

    unified = sync_entry_condition_rule_to_unified(rule)

    conds = {c.seq: c for c in unified.conditions.all()}
    assert conds[1].value_type == ConditionValueType.FIELD
    assert conds[1].metric_template_id is None
    assert conds[2].value_type == ConditionValueType.METRIC
    assert conds[2].metric_template_id == tpl.pk


# ---------------------------------------------------------------------------
# 5) 软删模板按非指标处理（与源侧 _resolve_metric_template 口径一致）
# ---------------------------------------------------------------------------

def test_bridge_soft_deleted_template_treated_as_field():
    """模板被软删后源侧已查不到 -> 镜像侧同样按 FIELD，不得出现悬空 METRIC。"""
    _, _, link = _make_link()
    rule = _make_rule(link)
    tpl = _make_metric_template()
    _item(rule, field=tpl.pk)
    MetricTemplate.objects.filter(pk=tpl.pk).update(deleted_at='2026-01-01T00:00:00Z')

    unified = sync_entry_condition_rule_to_unified(rule)

    cond = unified.conditions.get(seq=1)
    assert cond.value_type == ConditionValueType.FIELD, \
        '软删模板应与源侧一致地回退为字段条件'
    assert cond.metric_template_id is None


# ---------------------------------------------------------------------------
# 6) _condition_metric_fields 纯函数层
# ---------------------------------------------------------------------------

def test_condition_metric_fields_non_string_field():
    """field 非字符串（None/数字/空/列表）-> 不查库，直接按 FIELD。"""
    for bad in (None, 123, '', ['x']):
        item = MagicMock()
        item.field = bad
        with patch(METRIC_LOOKUP) as mock_lookup:
            out = _condition_metric_fields(item)
        assert out == {'value_type': ConditionValueType.FIELD, 'metric_template': None}
        mock_lookup.assert_not_called()


def test_condition_metric_fields_resolves_template():
    """field 命中模板 -> 返回 METRIC + 该模板实例。"""
    tpl = _make_metric_template()
    item = MagicMock()
    item.field = tpl.pk
    out = _condition_metric_fields(item)
    assert out['value_type'] == ConditionValueType.METRIC
    assert out['metric_template'].pk == tpl.pk