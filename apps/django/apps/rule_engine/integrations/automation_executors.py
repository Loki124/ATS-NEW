"""automation 家族的 4 个动作执行器（Phase 2，2026-08-31）。

复用 automation 业务侧已有逻辑（与 apps/automation/services.py 的 _action_* 一一对应），
而非重新实现：
- AUTO_ADVANCE  -> advance_application_to_next_stage
- SKIP_TO       -> jump_application_to_stage
- REMIND        -> send_notification
- REJECT_TO_POOL-> move_candidate_to_pool

所有业务 import 均为函数体内懒加载，确保 rule_engine 模块被 import 时不会触发对
automation 的循环依赖。

注册：模块底部在 import 时自动注册到全局 action_registry；register_automation_executors()
幂等，可重复调用（已在 AutomationEngine 委托桥里懒调用）。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from ..models import UnifiedActionType
from ..services import ActionExecutor, ActionResult, action_registry

logger = logging.getLogger(__name__)

# 模块级注册标记，保证 register_automation_executors 幂等
_REGISTERED = False


class AutoAdvanceExecutor(ActionExecutor):
    action_type = UnifiedActionType.AUTO_ADVANCE

    def supports(self, action_type: str) -> bool:
        return action_type == self.action_type

    def execute(self, context, action, rule) -> ActionResult:
        from apps.application.models import Application
        from apps.application.services import advance_application_to_next_stage

        if not context.application_id:
            return ActionResult(success=False, action_type=self.action_type,
                                message='no_application_id')
        try:
            application = Application.objects.get(id=context.application_id)
        except Application.DoesNotExist:
            return ActionResult(success=False, action_type=self.action_type,
                                message='application_not_found')
        result = advance_application_to_next_stage(
            application,
            actor=context.actor,
            skip_entry_condition=bool(action.params_json.get('skip_check', False)),
            reason=f'AUTO_ADVANCE by unified rule {rule.name}',
        )
        return ActionResult(
            success=True, action_type=self.action_type,
            message=f"advanced to {result.get('next_stage_name', 'N/A')}",
            data=result,
        )


class SkipToExecutor(ActionExecutor):
    action_type = UnifiedActionType.SKIP_TO

    def supports(self, action_type: str) -> bool:
        return action_type == self.action_type

    def execute(self, context, action, rule) -> ActionResult:
        from apps.application.models import Application
        from apps.application.services import jump_application_to_stage

        next_stage_id = action.params_json.get('next_stage_id')
        if not next_stage_id:
            return ActionResult(success=False, action_type=self.action_type,
                                message='no_target_stage')
        if not context.application_id:
            return ActionResult(success=False, action_type=self.action_type,
                                message='no_application_id')
        try:
            application = Application.objects.get(id=context.application_id)
        except Application.DoesNotExist:
            return ActionResult(success=False, action_type=self.action_type,
                                message='application_not_found')
        result = jump_application_to_stage(
            application,
            target_stage_id=next_stage_id,
            actor=context.actor,
            skip_entry_condition=bool(action.params_json.get('skip_check', False)),
            reason=f'SKIP_TO by unified rule {rule.name}',
        )
        return ActionResult(
            success=True, action_type=self.action_type,
            message=f"skipped to {result.get('stage_name', 'N/A')}",
            data=result,
        )


class RemindExecutor(ActionExecutor):
    action_type = UnifiedActionType.REMIND

    def supports(self, action_type: str) -> bool:
        return action_type == self.action_type

    def execute(self, context, action, rule) -> ActionResult:
        from apps.notification.services import send_notification

        params = action.params_json or {}
        recipient_ids = self._resolve_recipients(context, params)
        message = params.get('remind_message',
                             f'请及时处理候选人 {context.candidate_id}')
        for rid in recipient_ids:
            send_notification(
                recipient_id=rid,
                title='自动化提醒',
                content=message,
                link=f'/candidates/{context.candidate_id}',
                source='AUTOMATION',
                source_id=rule.legacy_id or rule.id,
            )
        return ActionResult(
            success=True, action_type=self.action_type,
            message=f'reminded {len(recipient_ids)} recipients',
            data={'recipient_ids': recipient_ids},
        )

    @staticmethod
    def _resolve_recipients(context, params: Dict[str, Any]) -> list:
        recipient_type = params.get('remind_to', 'CURRENT_HANDLER')
        if recipient_type == 'CURRENT_HANDLER' and context.application_id:
            from apps.application.models import Application
            try:
                app = Application.objects.get(id=context.application_id)
                sr = app.current_stage_record
                if sr and sr.current_handlers:
                    ids = [str(uid) for uid in sr.current_handlers if uid]
                    if ids:
                        return [ids[0]]
            except (AttributeError, TypeError, ValueError):  # 提醒接收人解析失败不应阻断
                return []
        elif recipient_type == 'CUSTOM':
            return params.get('custom_user_ids', []) or []
        return []


class RejectToPoolExecutor(ActionExecutor):
    action_type = UnifiedActionType.REJECT_TO_POOL

    def supports(self, action_type: str) -> bool:
        return action_type == self.action_type

    def execute(self, context, action, rule) -> ActionResult:
        from apps.talent_pool.services import move_candidate_to_pool

        if not context.candidate_id:
            return ActionResult(success=False, action_type=self.action_type,
                                message='no_candidate_id')
        result = move_candidate_to_pool(
            candidate_id=context.candidate_id,
            entry_source='AUTOMATION',
            entry_reason=f'AUTO by unified rule {rule.name}',
            actor=context.actor,
        )
        return ActionResult(
            success=True, action_type=self.action_type,
            message=f"moved to pool ({result.get('talent_pool_id', 'N/A')})",
            data=result,
        )


def register_automation_executors(registry=action_registry) -> None:
    """把 4 个 automation 执行器注册到 action_registry（幂等）。"""
    global _REGISTERED
    if _REGISTERED:
        return
    registry.register(AutoAdvanceExecutor())
    registry.register(SkipToExecutor())
    registry.register(RemindExecutor())
    registry.register(RejectToPoolExecutor())
    _REGISTERED = True


# import 时即注册，确保统一引擎委托派发前执行器已就位
register_automation_executors()
