"""entry_condition 家族的动作执行器（Phase 3，2026-08-31）。

entry_condition 的语义是「命中任一规则即放行，否则拦截」；统一引擎侧每条镜像规则
携带一条 ALLOW 动作——命中即放行（无副作用，仅作为派发标记）。未命中（统一引擎记
UNMATCHED）的拦截语义由 legacy 委托 wrapper（entry_condition/services.py 的
RuleEngine 委托分支）翻译为 REJECT + reject_message，因此本执行器无需产生副作用。

注册：模块底部在 import 时自动注册到全局 action_registry；register_entry_condition_executors()
幂等，可重复调用。
"""
from __future__ import annotations

import logging

from ..models import UnifiedActionType
from ..services import ActionExecutor, ActionResult, action_registry

logger = logging.getLogger(__name__)

# 模块级注册标记，保证 register_entry_condition_executors 幂等
_REGISTERED = False


class AllowExecutor(ActionExecutor):
    """ALLOW：放行（无任何副作用，仅标记命中）。"""

    action_type = UnifiedActionType.ALLOW

    def supports(self, action_type: str) -> bool:
        return action_type == self.action_type

    def execute(self, context, action, rule) -> ActionResult:
        return ActionResult(
            success=True,
            action_type=self.action_type,
            message='allowed',
        )


def register_entry_condition_executors(registry=action_registry) -> None:
    """把 entry_condition 执行器注册到 action_registry（幂等）。"""
    global _REGISTERED
    if _REGISTERED:
        return
    registry.register(AllowExecutor())
    _REGISTERED = True


# import 时即注册，确保统一引擎委托派发前执行器已就位
register_entry_condition_executors()
