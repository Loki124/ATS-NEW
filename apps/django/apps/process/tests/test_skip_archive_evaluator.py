"""evaluate_stage_skip_archive 纯函数单元测试（P1-1）。

覆盖：
- skip_rules 命中 → decision.skip True（METRIC 项经 MetricEngine 求值）
- archive_rules 命中 → decision.archive True
- 无 StageRule / 规则全禁用 / 规则不命中 → 皆 False
- 优先级：skip + archive 同时命中 → archive 覆盖 skip（decision.skip=False）
- 降级：单条规则求值异常 → 不命中 + warning（不抛 500）
- 整函数兜底：StageRule 查询异常 → 返回「不触发」（不抛 500）
- context=None 时也能从 candidate 推导 candidate_id
"""
import logging

import pytest

from apps.candidate.models import Candidate
from apps.metrics.models import AtomicMetric, MetricTemplate
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
)
from apps.process.services.skip_archive_evaluator import (
    SkipArchiveDecision,
    evaluate_stage_skip_archive,
)
from nanoid import generate as nanoid_generate


def _cid() -> str:
    return nanoid_generate(size=21)


def _make_candidate(age=None, **fields) -> Candidate:
    return Candidate.objects.create(
        id=_cid(), name='测试', phone='13900000088', age=age, **fields,
    )


def _make_atomic_template(name, source_path, data_type='number', operators=None) -> MetricTemplate:
    metric = AtomicMetric.objects.create(
        name=f'am_{name}_{_cid()}', source_path=source_path, data_type=data_type,
    )
    return MetricTemplate.objects.create(
        name=f'{name}_{_cid()}', atomic_metric=metric,
        operators=operators or ['GT', 'LT', 'EQ'],
    )


def _make_link_with_rule(skip_rules=None, archive_rules=None) -> StageRule:
    process = RecruitmentProcess.objects.create(
        code='W_SAEVAL', name='跳过归档求值测试流程',
        current_version='V1.0', version_seq=1, is_latest=True,
    )
    stage = RecruitmentStage.objects.create(
        code='P_SAEVAL', name='跳过归档求值测试阶段', stage_type='SCREEN',
    )
    link = ProcessStageLink.objects.create(process=process, stage=stage, order=0)
    return StageRule.objects.create(
        link=link, skip_rules=skip_rules or [], archive_rules=archive_rules or [],
    )


def _context(candidate, **extra) -> dict:
    ctx = {'candidate_id': candidate.id}
    ctx.update(extra)
    return ctx


def _metric_skip_rule(rule_id: str, tpl_id: str, value: str = '30') -> dict:
    return {
        'id': rule_id, 'name': f'{rule_id}-name', 'enabled': True, 'expression': '1',
        'items': [
            {
                'id': f'{rule_id}_i1', 'item_seq': 1, 'condition_type': 'METRIC',
                'field': str(tpl_id), 'operator': 'GT', 'value': value,
            },
        ],
    }


@pytest.mark.django_db
def test_skip_rule_hit():
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)
    rule = _make_link_with_rule(skip_rules=[_metric_skip_rule('sk1', tpl.id)])
    decision = evaluate_stage_skip_archive(rule.link, cand, _context(cand))
    assert decision.skip is True
    assert decision.archive is False
    assert decision.skip_rule is not None
    assert decision.skip_rule['id'] == 'sk1'
    assert 'skip' in decision.detail


@pytest.mark.django_db
def test_skip_rule_hit_without_context():
    """context=None 时从 candidate 推导 candidate_id，仍能正确求值。"""
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)
    rule = _make_link_with_rule(skip_rules=[_metric_skip_rule('sk1', tpl.id)])
    decision = evaluate_stage_skip_archive(rule.link, cand, None)
    assert decision.skip is True


@pytest.mark.django_db
def test_archive_rule_hit():
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)
    rule = _make_link_with_rule(archive_rules=[_metric_skip_rule('ar1', tpl.id)])
    decision = evaluate_stage_skip_archive(rule.link, cand, _context(cand))
    assert decision.archive is True
    assert decision.skip is False
    assert decision.archive_rule is not None
    assert decision.archive_rule['id'] == 'ar1'
    assert 'archive' in decision.detail


@pytest.mark.django_db
def test_no_stage_rule():
    process = RecruitmentProcess.objects.create(
        code='W_SAEVAL2', name='n', current_version='V1.0', version_seq=1, is_latest=True,
    )
    stage = RecruitmentStage.objects.create(code='P_SAEVAL2', name='n', stage_type='SCREEN')
    link = ProcessStageLink.objects.create(process=process, stage=stage, order=0)
    cand = _make_candidate(age=40)
    decision = evaluate_stage_skip_archive(link, cand, _context(cand))
    assert decision.skip is False
    assert decision.archive is False


@pytest.mark.django_db
def test_disabled_rule_not_evaluated():
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)
    disabled_rule = dict(_metric_skip_rule('sk1', tpl.id))
    disabled_rule['enabled'] = False
    rule = _make_link_with_rule(skip_rules=[disabled_rule])
    decision = evaluate_stage_skip_archive(rule.link, cand, _context(cand))
    assert decision.skip is False


@pytest.mark.django_db
def test_skip_rule_miss():
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=20)  # 20 > 30 不成立
    rule = _make_link_with_rule(skip_rules=[_metric_skip_rule('sk1', tpl.id)])
    decision = evaluate_stage_skip_archive(rule.link, cand, _context(cand))
    assert decision.skip is False
    assert decision.archive is False


@pytest.mark.django_db
def test_archive_priority_over_skip():
    """同一阶段 skip 与 archive 同时命中 → archive 优先（decision.skip=False）。"""
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)
    rule = _make_link_with_rule(
        skip_rules=[_metric_skip_rule('sk1', tpl.id)],
        archive_rules=[_metric_skip_rule('ar1', tpl.id)],
    )
    decision = evaluate_stage_skip_archive(rule.link, cand, _context(cand))
    assert decision.archive is True
    assert decision.skip is False
    assert decision.skip_rule is None
    assert decision.archive_rule is not None


@pytest.mark.django_db
def test_rule_eval_exception_degraded(monkeypatch, caplog):
    """单条规则求值异常 → 记不命中 + warning，不抛 500。"""
    cand = _make_candidate(age=40)
    rule = _make_link_with_rule(skip_rules=[{'id': 'sk1', 'name': 'n', 'enabled': True, 'expression': '1', 'items': []}])

    def boom(rule_json, ctx):  # noqa: ANN001, ANN201
        raise RuntimeError('boom')

    monkeypatch.setattr(
        'apps.process.services.skip_archive_evaluator.RuleItemEvaluator.evaluate_rule', boom,
    )
    with caplog.at_level(logging.WARNING):
        decision = evaluate_stage_skip_archive(rule.link, cand, _context(cand))
    assert decision.skip is False
    assert any('求值异常' in r.message for r in caplog.records)


@pytest.mark.django_db
def test_stagerule_query_exception_returns_no_trigger(monkeypatch, caplog):
    """StageRule 查询异常 → 整函数兜底返回「不触发」，绝不 500。"""
    cand = _make_candidate(age=40)
    rule = _make_link_with_rule()

    def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        raise RuntimeError('db down')

    monkeypatch.setattr(StageRule.objects, 'filter', boom)
    with caplog.at_level(logging.WARNING):
        decision = evaluate_stage_skip_archive(rule.link, cand, _context(cand))
    assert isinstance(decision, SkipArchiveDecision)
    assert decision.skip is False
    assert decision.archive is False
    # 取 StageRule 失败被内侧兜底捕获，记 warning 且不抛 500
    assert any('取 StageRule 失败' in r.message for r in caplog.records)
