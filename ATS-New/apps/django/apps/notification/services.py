"""Notification Services (PRD v4 §14.10)

通知服务：
- 多通道发送：IN_APP / EMAIL / SMS / WECOM
- 模板渲染（变量替换）
- 批量发送
- 通知日志
- 失败重试
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import NotFound
from apps.core.models import User

from .models import NotificationLog, NotificationTemplate

logger = logging.getLogger(__name__)


# ============================================================
# 数据类
# ============================================================
@dataclass
class SendNotificationData:
    """发送通知入参"""
    recipient_id: str
    title: str
    content: str
    link: str = ''
    source: str = 'SYSTEM'
    source_id: Optional[str] = None
    channel: str = 'IN_APP'
    template_code: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    priority: str = 'NORMAL'


# ============================================================
# 变量渲染
# ============================================================
VARIABLE_PATTERN = re.compile(r'\{\{\s*(\w+)\s*\}\}')


def render_template(text: str, variables: Dict[str, Any]) -> str:
    """渲染模板：{{name}} → 张三"""
    if not text:
        return text
    def replace(match):
        key = match.group(1)
        return str(variables.get(key, match.group(0)))
    return VARIABLE_PATTERN.sub(replace, text)


# ============================================================
# 通道分发
# ============================================================
class NotificationDispatcher:
    """通知分发器"""

    @staticmethod
    def send_in_app(log: NotificationLog) -> bool:
        """站内信 - 直接落库 + WebSocket 推送"""
        try:
            # WebSocket 推送（异步）
            from apps.core.routing import push_to_user
            try:
                push_to_user(
                    user_id=log.recipient_id,
                    payload={
                        'type': 'notification',
                        'id': log.id,
                        'title': log.subject,
                        'content': log.content,
                        'link': (log.context or {}).get('link', ''),
                        'event': log.event,
                    },
                )
            except Exception as e:
                logger.debug('WebSocket push failed: %s', e)
            log.sent_at = timezone.now()
            log.save(update_fields=['sent_at'])
            return True
        except Exception as e:
            logger.exception('In-app send failed: %s', e)
            log.failed_reason = str(e)
            log.save(update_fields=['failed_reason'])
            return False

    @staticmethod
    def send_email(log: NotificationLog) -> bool:
        """邮件发送 - 集成 email service"""
        try:
            from apps.integration.services import send_email
            recipient = log.recipient
            if not recipient or not recipient.email:
                log.failed_reason = 'Recipient has no email'
                log.save(update_fields=['failed_reason'])
                return False
            return send_email(
                to=recipient.email,
                subject=log.subject,
                body=log.content,
            )
        except Exception as e:
            logger.exception('Email send failed: %s', e)
            log.failed_reason = str(e)
            log.save(update_fields=['failed_reason'])
            return False

    @staticmethod
    def send_sms(log: NotificationLog) -> bool:
        """短信发送"""
        try:
            from apps.integration.services import send_sms
            recipient = log.recipient
            if not recipient or not recipient.phone:
                log.failed_reason = 'Recipient has no phone'
                log.save(update_fields=['failed_reason'])
                return False
            return send_sms(
                phone=recipient.phone,
                content=log.content,
            )
        except Exception as e:
            logger.exception('SMS send failed: %s', e)
            log.failed_reason = str(e)
            log.save(update_fields=['failed_reason'])
            return False

    @staticmethod
    def send_wecom(log: NotificationLog) -> bool:
        """企微发送"""
        try:
            from apps.integration.services import send_wecom_message
            recipient = log.recipient
            if not recipient:
                log.failed_reason = 'Recipient not found'
                log.save(update_fields=['failed_reason'])
                return False
            return send_wecom_message(
                user_id=log.recipient_id,
                content=log.content,
                title=log.subject,
            )
        except Exception as e:
            logger.exception('Wecom send failed: %s', e)
            log.failed_reason = str(e)
            log.save(update_fields=['failed_reason'])
            return False

    @staticmethod
    def dispatch(log: NotificationLog) -> bool:
        """根据 channel 分发"""
        handler = {
            'IN_APP': NotificationDispatcher.send_in_app,
            'EMAIL': NotificationDispatcher.send_email,
            'SMS': NotificationDispatcher.send_sms,
            'WECOM': NotificationDispatcher.send_wecom,
        }.get(log.channel)
        if not handler:
            log.failed_reason = f'Unknown channel: {log.channel}'
            log.save(update_fields=['failed_reason'])
            return False
        return handler(log)


# ============================================================
# 通知服务
# ============================================================
class NotificationService:
    """通知服务"""

    @staticmethod
    @transaction.atomic
    def send_notification(data: SendNotificationData) -> Dict[str, Any]:
        """发送单条通知"""
        try:
            recipient = User.objects.get(id=data.recipient_id, is_active=True)
        except User.DoesNotExist as e:
            raise NotFound(f'Recipient {data.recipient_id} not found') from e

        # 解析模板（如果提供）
        subject = data.title
        content = data.content
        template = None
        if data.template_code:
            try:
                template = NotificationTemplate.objects.get(
                    code=data.template_code, is_active=True,
                )
                templates = template.templates or {}
                channel_tpl = templates.get(data.channel, {})
                if isinstance(channel_tpl, dict):
                    subject = channel_tpl.get('subject', data.title)
                    body_tpl = channel_tpl.get('body', data.content)
                else:
                    body_tpl = channel_tpl
                content = render_template(body_tpl, data.variables or {})
            except NotificationTemplate.DoesNotExist:
                logger.debug('Template %s not found, use raw content', data.template_code)

        # 写入日志
        log = NotificationLog.objects.create(
            template=template,
            recipient=recipient,
            channel=data.channel,
            subject=subject[:200],
            content=content,
            event=data.source,
            context={
                'source': data.source,
                'source_id': data.source_id,
                'link': data.link,
                'priority': data.priority,
                **(data.variables or {}),
            },
        )

        # 分发
        success = NotificationDispatcher.dispatch(log)
        return {
            'log_id': log.id,
            'channel': log.channel,
            'sent': success,
            'sent_at': log.sent_at.isoformat() if log.sent_at else None,
        }

    @staticmethod
    def send_bulk(data_list: List[SendNotificationData]) -> List[Dict[str, Any]]:
        """批量发送"""
        results = []
        for data in data_list:
            try:
                result = NotificationService.send_notification(data)
                results.append({'recipient_id': data.recipient_id, **result})
            except Exception as e:
                results.append({
                    'recipient_id': data.recipient_id, 'sent': False, 'error': str(e),
                })
        return results

    @staticmethod
    def mark_as_read(log_id: str, user: User) -> bool:
        """标记已读"""
        try:
            log = NotificationLog.objects.get(id=log_id, recipient=user, deleted_at__isnull=True)
        except NotificationLog.DoesNotExist:
            return False
        if not log.read_at:
            log.read_at = timezone.now()
            log.save(update_fields=['read_at'])
        return True

    @staticmethod
    def get_unread_count(user: User) -> int:
        """未读数"""
        return NotificationLog.objects.filter(
            recipient=user, read_at__isnull=True, deleted_at__isnull=True,
            channel='IN_APP',
        ).count()

    @staticmethod
    def list_notifications(
        user: User,
        unread_only: bool = False,
        event: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[NotificationLog]:
        """列表"""
        qs = NotificationLog.objects.filter(
            recipient=user, deleted_at__isnull=True,
        )
        if unread_only:
            qs = qs.filter(read_at__isnull=True)
        if event:
            qs = qs.filter(event=event)
        return list(qs.order_by('-created_at')[offset:offset + limit])

    @staticmethod
    def render_and_preview(template_code: str, variables: Dict[str, Any],
                            channel: str = 'IN_APP') -> Dict[str, str]:
        """预览模板渲染结果"""
        try:
            template = NotificationTemplate.objects.get(code=template_code)
        except NotificationTemplate.DoesNotExist as e:
            raise NotFound(f'Template {template_code} not found') from e
        tpl = (template.templates or {}).get(channel, {})
        if isinstance(tpl, dict):
            subject = render_template(tpl.get('subject', ''), variables)
            body = render_template(tpl.get('body', ''), variables)
        else:
            subject = template.name
            body = render_template(tpl, variables)
        return {'subject': subject, 'body': body}


# ============================================================
# 便捷函数
# ============================================================
def send_notification(
    recipient_id: str, title: str, content: str,
    link: str = '', source: str = 'SYSTEM', source_id: Optional[str] = None,
    channel: str = 'IN_APP', template_code: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """便捷函数"""
    data = SendNotificationData(
        recipient_id=recipient_id, title=title, content=content, link=link,
        source=source, source_id=source_id, channel=channel,
        template_code=template_code, variables=variables,
    )
    return NotificationService.send_notification(data)


def render_and_preview(template_code: str, variables: Dict[str, Any],
                        channel: str = 'IN_APP') -> Dict[str, str]:
    return NotificationService.render_and_preview(template_code, variables, channel)
