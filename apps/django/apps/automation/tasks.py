"""Automation Celery tasks (PRD v4 §6.6)

P0-2 修复: 所有调度任务已从裸 @shared_task 改为
@retryable_scheduled_task,获得统一的:
- DB 抖动自动重试 (指数退避,最多 3 次)
- 连续失败 N 次后通知超管
- 任务成功自动清理失败计数
"""
import logging
from typing import Dict

from celery import shared_task
from django.utils import timezone

from apps.common.celery_utils import retryable_scheduled_task

logger = logging.getLogger(__name__)


@retryable_scheduled_task(
    name='apps.automation.tasks.run_scheduled_rules',
    max_retries=3,
    retry_backoff=60,
)
def run_scheduled_rules() -> Dict:
    """执行所有启用的 SCHEDULED 类型自动化规则（每 15 分钟）

    Fix 2: 原代码调用 ``AutomationEngine.run(rule)`` 把 rule 当 self 传入,
    触发 AttributeError. 正确做法: 构造一个 SCHEDULED trigger 的 engine,
    对每条规则调 evaluate_rule + execute_rule.
    """
    from .models import AutomationRule
    from .services import AutomationEngine, TriggerContext

    # 构造 SCHEDULED 触发上下文 (actor=None 表示系统触发)
    engine = AutomationEngine(
        context=TriggerContext(
            trigger_type='SCHEDULED',
            candidate_id=None,
            application_id=None,
            stage_id=None,
            extra={},
        ),
        actor=None,
    )

    # P1-3: .iterator() 流式查询,避免规则数量增长后 OOM
    enabled_rules = AutomationRule.objects.filter(
        enabled=True,
        trigger_type='SCHEDULED',
        deleted_at__isnull=True,
    ).iterator(chunk_size=200)
    triggered = 0
    skipped = 0
    errors = 0
    total = 0

    for rule in enabled_rules:
        total += 1
        try:
            # 熔断检查
            if engine._is_circuit_open(rule):
                skipped += 1
                continue
            match = engine.evaluate_rule(rule)
            if not match.matched:
                engine._save_log(rule, match, _skipped_result(rule, match.skip_reason))
                skipped += 1
                continue
            result = engine.execute_rule(rule, match)
            if result.get('triggered') if isinstance(result, dict) else True:
                triggered += 1
            else:
                skipped += 1
        except Exception as e:
            logger.exception(f'Rule {rule.id} failed: {e}')
            errors += 1

    return {
        'checked_at': timezone.now().isoformat(),
        'rules_total': total,
        'triggered': triggered,
        'skipped': skipped,
        'errors': errors,
    }


def _skipped_result(rule, reason: str):
    """构造 skipped ExecutionResult (避免循环 import ExecutionResult)"""
    from .services import ExecutionResult
    return ExecutionResult(
        rule_id=rule.id,
        rule_name=rule.name,
        matched=False,
        action_taken='',
        skip_reason=reason or '',
    )


@shared_task(name='apps.automation.tasks.check_automation_failure_rate')
def check_automation_failure_rate() -> Dict:
    """检查自动化规则失败率，超过阈值则告警"""
    from .models import AutomationRule, AutomationLog
    from apps.notification.services import NotificationService
    from apps.core.models import User

    # P1-3: .iterator() 流式查询
    rules = AutomationRule.objects.filter(enabled=True).iterator(chunk_size=200)
    alerts = []
    rules_checked = 0

    for rule in rules:
        rules_checked += 1
        threshold = rule.failure_rate_threshold or 0.5
        recent_logs = AutomationLog.objects.filter(rule=rule).order_by('-trigger_time')[:100]
        if not recent_logs.exists():
            continue

        total = recent_logs.count()
        failed = sum(1 for log in recent_logs if log.error_message or log.evaluate_result == 'ERROR')
        rate = failed / total if total else 0

        if rate > threshold:
            alerts.append({
                'rule_id': rule.id,
                'rule_name': rule.name,
                'failure_rate': rate,
                'threshold': threshold,
                'failed': failed,
                'total': total,
            })
            # 通知超管
            try:
                admins = User.objects.filter(is_superuser=True, is_active=True)
                for admin in admins:
                    NotificationService.send_notification(
                        recipient=admin,
                        event='automation.failure_rate_alert',
                        context={'rule': rule, 'failure_rate': rate},
                        channels=['IN_APP', 'EMAIL'],
                    )
            except Exception as e:
                logger.exception(f'Failure rate notification failed: {e}')

    return {
        'checked_at': timezone.now().isoformat(),
        'rules_checked': rules_checked,
        'alerts': alerts,
    }
