"""mou 家族的动作执行器（Phase 4，2026-09-01）。

mou 原生 TCA 家族：trigger=BUSINESS_EVENT，action=SET_PERMISSION（与 MouAdapter 读
路径一致）。mou 当前无独立 evaluator（设计文档 §3.6），其 conditions/actions 为 JSON dict，
由本执行器（被统一引擎派发时）自行解析并 best-effort 应用。

注册：模块底部 import 时自动注册到全局 action_registry；register_mou_executors() 幂等。

注意：RULE_ENGINE_DISPATCH 默认 False，本执行器不会在现网被实际派发；Phase 4 仅完成
「注册 + 双写镜像」，mou 派发委托的激活推迟到后续 Phase。
"""

from __future__ import annotations

import logging

from ..models import UnifiedActionType
from ..services import ActionExecutor, ActionResult, action_registry

logger = logging.getLogger(__name__)

# 模块级注册标记，保证 register_mou_executors 幂等
_REGISTERED = False


class MouPermissionExecutor(ActionExecutor):
    """SET_PERMISSION 执行器（mou 权限类动作，best-effort）。

    mou 的 actions 为 JSON dict，无统一 evaluator；本执行器在被派发时解析
    action.params_json['actions'] 并记录，不阻断主链路（mou 权限实际生效由 permissions-v2
    既有逻辑负责，统一引擎仅做可观测聚合）。
    """

    action_type = UnifiedActionType.SET_PERMISSION

    def supports(self, action_type: str) -> bool:
        return action_type == self.action_type

    def execute(self, context, action, rule) -> ActionResult:
        actions = (action.params_json or {}).get('actions')
        # best-effort：仅记录 + 返回成功，绝不阻断
        logger.info(
            'MouPermissionExecutor applied rule=%s actions=%r candidate=%s',
            getattr(rule, 'legacy_id', rule.id), actions, context.candidate_id,
        )
        return ActionResult(
            success=True,
            action_type=self.action_type,
            message='mou permission applied (best-effort)',
            data={'actions': actions},
        )


def register_mou_executors(registry=action_registry) -> None:
    """把 mou 执行器注册到 action_registry（幂等）。"""
    global _REGISTERED
    if _REGISTERED:
        return
    registry.register(MouPermissionExecutor())
    _REGISTERED = True


# import 时即注册，确保统一引擎委托派发前执行器已就位
register_mou_executors()
