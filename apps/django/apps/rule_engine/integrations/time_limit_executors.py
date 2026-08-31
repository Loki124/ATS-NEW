"""time_limit 家族的动作执行器（Phase 3，2026-08-31）。

time_limit 的语义是「进入阶段时计算停留限时 / 锁定截止时间」；统一引擎侧每条镜像规则
携带一条 LOCK 动作。LOCK 执行器复用 time_limit 业务侧已有的计算口径
（calc_time_limit 的 锁定时长 + 加时 × 人数 公式 + compute_locked_until），把 deadline
写入 Application.stage_deadline（现网实际承载字段，见 time_limit/tasks.py 对
app.stage_deadline 的使用；原注释里的 ApplicationStageRecord.locked_until 字段并不存在）。

所有业务 import 均为函数体内懒加载，确保 rule_engine 模块被 import 时不会触发对
time_limit / application 的循环依赖。

注册：模块底部在 import 时自动注册到全局 action_registry；register_time_limit_executors()
幂等，可重复调用。
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.utils import timezone

from ..services import ActionExecutor, ActionResult, action_registry
from ..models import UnifiedActionType

logger = logging.getLogger(__name__)

# 模块级注册标记，保证 register_time_limit_executors 幂等
_REGISTERED = False


class LockExecutor(ActionExecutor):
    """LOCK：写入阶段停留截止时间（Application.stage_deadline）。"""

    action_type = UnifiedActionType.LOCK

    def supports(self, action_type: str) -> bool:
        return action_type == self.action_type

    def execute(self, context, action, rule) -> ActionResult:
        params = action.params_json or {}
        lock_duration = int(params.get('lock_duration', 0) or 0)
        extension_per_person = int(params.get('extension_per_person', 0) or 0)
        effective_scope = params.get('effective_scope', 'NEW_ONLY')

        # 加时公式：基础锁定时长 + 加时 × (面试官人数 - 1)
        interviewer_count = int(context.extra.get('interviewer_count', 1) or 1)
        extra_interviewer_days = extension_per_person * max(0, interviewer_count - 1)
        total_lock_days = lock_duration + extra_interviewer_days

        if total_lock_days <= 0:
            return ActionResult(
                success=True,
                action_type=self.action_type,
                message='no_lock(no positive duration)',
                data={'total_lock_days': 0, 'effective_scope': effective_scope},
            )

        # 复用 time_limit 业务侧的计算口径，避免重复实现
        from apps.time_limit.services import compute_locked_until

        now = timezone.now()
        locked_until = compute_locked_until(now, total_lock_days)

        # 写入 Application.stage_deadline（现网承载字段）
        if context.application_id:
            from apps.application.models import Application
            try:
                application = Application.objects.get(id=context.application_id)
                application.stage_deadline = locked_until
                application.save(update_fields=['stage_deadline', 'updated_at'])
            except Application.DoesNotExist:
                return ActionResult(
                    success=False, action_type=self.action_type,
                    message='application_not_found',
                    data={'total_lock_days': total_lock_days},
                )
            except Exception as exc:  # noqa: BLE001 — LOCK 写入失败不应阻断派发主链路
                logger.exception('LOCK executor failed to persist stage_deadline: %s', exc)
                return ActionResult(
                    success=False, action_type=self.action_type,
                    message=f'persist_failed: {exc}',
                    data={'total_lock_days': total_lock_days},
                )

        return ActionResult(
            success=True,
            action_type=self.action_type,
            message=f'locked for {total_lock_days}d',
            data={
                'total_lock_days': total_lock_days,
                'effective_scope': effective_scope,
                'locked_until': locked_until.isoformat() if locked_until else None,
            },
        )


def register_time_limit_executors(registry=action_registry) -> None:
    """把 time_limit 执行器注册到 action_registry（幂等）。"""
    global _REGISTERED
    if _REGISTERED:
        return
    registry.register(LockExecutor())
    _REGISTERED = True


# import 时即注册，确保统一引擎委托派发前执行器已就位
register_time_limit_executors()
