"""Automation Celery tasks (PRD v4 §6.6)"""
import logging
from typing import Dict

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='apps.automation.tasks.run_scheduled_rules')
def run_scheduled_rules() -> Dict:
    """执行所有启用的自动化规则（每 15 分钟）"""
    from .models import AutomationRule
    from .services import AutomationEngine

    enabled_rules = AutomationRule.objects.filter(enabled=True)
    triggered = 0
    skipped = 0
    errors = 0

    for rule in enabled_rules:
        try:
            result = AutomationEngine.run(rule)
            if result.get('triggered'):
                triggered += 1
            else:
                skipped += 1
        except Exception as e:
            logger.exception(f'Rule {rule.id} failed: {e}')
            errors += 1

    return {
        'checked_at': timezone.now().isoformat(),
        'rules_total': enabled_rules.count(),
        'triggered': triggered,
        'skipped': skipped,
        'errors': errors,
    }


@shared_task(name='apps.automation.tasks.check_automation_failure_rate')
def check_automation_failure_rate() -> Dict:
    """检查自动化规则失败率，超过阈值则告警"""
    from .models import AutomationRule, AutomationLog
    from apps.notification.services import NotificationService
    from apps.core.models import User

    rules = AutomationRule.objects.filter(enabled=True)
    alerts = []

    for rule in rules:
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
        'rules_checked': rules.count(),
        'alerts': alerts,
    }
