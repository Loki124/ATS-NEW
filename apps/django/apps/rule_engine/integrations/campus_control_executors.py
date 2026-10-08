"""campus_control 家族的动作执行器（Phase 4，2026-09-01）。

campus_control 是 CONSTRAINT 家族：校验「提交 Offer 时」的占比/人数约束，命中后
- 硬约束 → 抛异常阻断（BLOCK_HARD）
- 软约束 → 放行 + 提示（BLOCK_SOFT）

统一侧每条镜像规则携带一条 BLOCK_HARD / BLOCK_SOFT 动作；本执行器在
RULE_ENGINE_DISPATCH=True 时被统一引擎派发，委托回 campus_control.calc 的
``validate_offer_against_rules`` 完成真实校验（占比数学不重写，见设计文档 §3.5 / D3）。

所有业务 import 均函数体内懒加载，避免 rule_engine 模块被 import 时触发循环依赖。
注册：模块底部 import 时自动注册到全局 action_registry；register_campus_executors()
幂等，可重复调用。

注意：Phase 4 仅注册执行器 + 镜像校验事件（见 bridge.mirror_campus_offer_validation）；
campus 校验是「全局计数」例程，无法由通用 per-rule ConditionEvaluator 复现，故完整的
OFFER_SUBMITTED 统一引擎派发委托推迟到后续 Phase（RULE_ENGINE_DISPATCH 默认 False，
现网行为不变）。
"""

from __future__ import annotations

import logging

from ..models import UnifiedActionType
from ..services import ActionExecutor, ActionResult, action_registry

logger = logging.getLogger(__name__)

# 模块级注册标记，保证 register_campus_executors 幂等
_REGISTERED = False


class ConstraintValidator(ActionExecutor):
    """CONSTRAINT 校验执行器：BLOCK_HARD / BLOCK_SOFT 共用。

    被统一引擎派发时，委托回 campus_control.validate_offer_against_rules 完成真实
    占比/人数校验（懒加载，避免循环依赖）。解析不到足够上下文或任意异常时，按
    best-effort 返回 success=True（不阻断），确保派发路径异常不影响现网。
    """

    # 同时支持硬/软两种约束动作
    action_types = (UnifiedActionType.BLOCK_HARD, UnifiedActionType.BLOCK_SOFT)

    def supports(self, action_type: str) -> bool:
        return action_type in self.action_types

    def execute(self, context, action, rule) -> ActionResult:
        from apps.campus_control.services import (
            ControlRuleViolation,
            validate_offer_against_rules,
        )

        # 解析上下文：candidate 必填；position/level/start_date 尽量从 extra 取
        candidate_id = context.candidate_id
        if not candidate_id:
            return ActionResult(success=True, action_type=self.action_types[0],
                                message='no_candidate_id')
        try:
            from apps.candidate.models import Candidate
            from apps.position.models import Position
            candidate = Candidate.objects.get(id=candidate_id)
            position = None
            position_id = context.extra.get('position_id')
            if position_id:
                position = Position.objects.filter(id=position_id).first()
            level = context.extra.get('level')
            start_date = context.extra.get('start_date')
        except (AttributeError, TypeError) as exc:  # 上下文解析失败 → 不阻断
            logger.exception('ConstraintValidator context resolve failed: %s', exc)
            return ActionResult(success=True, action_type=action.action_type,
                                message=f'context_unavailable: {exc}')

        try:
            validate_offer_against_rules(
                candidate=candidate,
                position=position,
                level=level,
                position_title=context.extra.get('position_title', '') or '',
                start_date=start_date,
            )
            return ActionResult(
                success=True, action_type=action.action_type, message='allowed',
            )
        except ControlRuleViolation as e:
            # 硬约束阻断 / 软约束提示：翻译为执行结果
            return ActionResult(
                success=False, action_type=action.action_type,
                message=e.message,
                data={'blocks': e.blocks, 'warnings': e.warnings},
            )
        except Exception as exc:  # noqa: BLE001 — 校验异常不应阻断派发主链路
            logger.exception('ConstraintValidator validate failed: %s', exc)
            return ActionResult(success=True, action_type=action.action_type,
                                message=f'validate_error: {exc}')


def register_campus_executors(registry=action_registry) -> None:
    """把 campus_control 执行器注册到 action_registry（幂等）。"""
    global _REGISTERED
    if _REGISTERED:
        return
    registry.register(ConstraintValidator())
    _REGISTERED = True


# import 时即注册，确保统一引擎委托派发前执行器已就位
register_campus_executors()
