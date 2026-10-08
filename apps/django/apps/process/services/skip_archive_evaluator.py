"""阶段自动跳过 / 自动归档 求值器（P1-1，消费方纯函数）。

本模块是「阶段自动流转」规则的**条件求值入口**，与 T05 的 ``RuleItemEvaluator`` 配合：

    - 条件项求值（METRIC / legacy CANDIDATE·DEMAND·POSITION / STAGE_STATUS）全部委托
      ``RuleItemEvaluator``，零重复实现；
    - 整条规则 AND/OR 布尔求值委托 ``apps.process.expressions.evaluate``
      （经 ``RuleItemEvaluator.evaluate_rule``）。

设计为**纯函数**（不写库），便于单测与复用：调用方（``application/services``）拿到
``SkipArchiveDecision`` 后自行决定「置 SKIPPED 并推进」还是「整申请归档」。

降级铁律（项目 FAIL-not-500）：
    - 单条规则求值异常 → ``logger.warning`` + 记「不命中」，绝不抛 500；
    - 整函数意外异常 → 兜底返回「不触发」（``skip=False, archive=False``）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from apps.process.models import StageRule
from apps.process.services.rule_item_evaluator import RuleItemEvaluator

logger = logging.getLogger(__name__)


@dataclass
class SkipArchiveDecision:
    """阶段进入时的跳过 / 归档判定结果。

    ``skip`` / ``archive`` 二者最多一个为 ``True``（archive 优先级覆盖 skip）。
    ``skip_rule`` / ``archive_rule`` 保留命中的原始规则 dict，供调用方写审计。
    """

    skip: bool = False
    archive: bool = False
    skip_rule: Dict[str, Any] | None = None
    archive_rule: Dict[str, Any] | None = None
    detail: str = ''


def _enabled_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """过滤 enabled 规则（缺省视为启用，保证存量空 schema / 无 enabled 键不阻断）。"""
    out: List[Dict[str, Any]] = []
    for rule in (rules or []):
        if rule.get('enabled', True):
            out.append(rule)
    return out


def evaluate_stage_skip_archive(
    link: Any,
    candidate: Any,
    context: Dict[str, Any] | None = None,
) -> SkipArchiveDecision:
    """评估某 link（阶段）进入时的自动跳过 / 自动归档规则。

    Args:
        link: ``ProcessStageLink``（阶段-流程关联），其 ``stage_rule`` 持有
            ``skip_rules`` / ``archive_rules`` 两个 JSONField。
        candidate: ``Candidate`` 实例（提供 ``candidate_id``）。
        context: 求值上下文，至少含 ``candidate_id``，可选 ``demand_id`` / ``position_id``
            （供 METRIC / legacy DEMAND·POSITION 取值）。不传则仅用 ``candidate_id``。

    Returns:
        ``SkipArchiveDecision``：skip / archive 命中判定 + 命中规则。
        无 ``StageRule`` 或全规则不命中 → 二者皆 ``False``。

    降级：
        - 单条规则求值异常 → 记「不命中」+ ``warning``，不阻断其它规则；
        - 整函数意外异常 → 兜底返回「不触发」，绝不 500。
    """
    decision = SkipArchiveDecision(skip=False, archive=False)

    try:
        # 1) 取该 link 的 StageRule（无则直接返回「不触发」）
        try:
            stage_rule = StageRule.objects.filter(
                link=link, deleted_at__isnull=True,
            ).first()
        except Exception as exc:  # noqa: BLE001 — 取规则失败兜底不触发, 绝不 500
            logger.warning(
                'evaluate_stage_skip_archive 取 StageRule 失败 link=%s err=%s',
                getattr(link, 'id', None), exc,
            )
            return decision

        if stage_rule is None:
            return decision

        # 2) 归一化 context（保证 candidate_id 存在）
        ctx: Dict[str, Any] = dict(context or {})
        if candidate is not None and not ctx.get('candidate_id'):
            ctx['candidate_id'] = candidate.id

        # 3) 自动跳过：遍历 enabled 的 skip_rules，命中即记 skip 并 break
        for rule in _enabled_rules(stage_rule.skip_rules):
            try:
                hit = bool(RuleItemEvaluator.evaluate_rule(rule, ctx))
            except Exception as exc:  # noqa: BLE001 — 单条规则异常 → 不命中, 不阻断
                logger.warning(
                    'skip rule 求值异常 rule=%s err=%s', rule.get('id'), exc,
                )
                hit = False
            if hit:
                decision.skip = True
                decision.skip_rule = rule
                decision.detail = f"skip 命中规则: {rule.get('name', rule.get('id'))}"
                break

        # 4) 自动归档：遍历 enabled 的 archive_rules，命中即记 archive 并 break
        for rule in _enabled_rules(stage_rule.archive_rules):
            try:
                hit = bool(RuleItemEvaluator.evaluate_rule(rule, ctx))
            except Exception as exc:  # noqa: BLE001 — 单条规则异常 → 不命中, 不阻断
                logger.warning(
                    'archive rule 求值异常 rule=%s err=%s', rule.get('id'), exc,
                )
                hit = False
            if hit:
                decision.archive = True
                decision.archive_rule = rule
                decision.detail = f"archive 命中规则: {rule.get('name', rule.get('id'))}"
                break

        # 5) 优先级：archive 覆盖 skip（同一阶段二者同时命中 → 终态归档）
        if decision.archive:
            decision.skip = False
            decision.skip_rule = None

        return decision

    except Exception as exc:  # noqa: BLE001 — 整函数兜底: 任何意外 → 不触发, 绝不 500
        logger.warning(
            'evaluate_stage_skip_archive 意外异常 link=%s err=%s',
            getattr(link, 'id', None), exc,
        )
        return SkipArchiveDecision(skip=False, archive=False)
