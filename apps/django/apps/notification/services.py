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
from datetime import timedelta
from typing import Any, Dict, List

from django.db import OperationalError, transaction
from django.db.models import Q
from django.utils import timezone
from kombu.exceptions import OperationalError as BrokerOperationalError
from redis.exceptions import RedisError

from apps.common.exceptions import NotFound
from apps.core.models import User

from .models import NotificationLog, NotificationTemplate

logger = logging.getLogger(__name__)

#: 通知抢占超时（分钟）—— 超过即视为上一轮进程崩溃, 允许重新抢占
DELIVER_CLAIM_TTL_MINUTES = 5


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
    source_id: str | None = None
    channel: str = 'IN_APP'
    template_code: str | None = None
    variables: Dict[str, Any] | None = None
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
            except (ConnectionError, OSError, TimeoutError) as e:
                # Channels 推送是网络 IO, 窄集异常可观察。编程错误(AttributeError 等)不再吞。
                logger.debug('WebSocket push failed: %s', e)
            log.sent_at = timezone.now()
            log.save(update_fields=['sent_at'])
            return True
        except OperationalError as e:
            # ORM 落库失败：连接/事务问题。IntegrityError 等业务异常留给上层事务回滚。
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
        except OperationalError as e:
            # integration.send_email() 已自行 swallow 第三方 IO 异常并返回 False,
            # 这里只兜 ORM 落库失败; 其他编程错误不再静默吞, 让其崩出以便排查。
            logger.exception('Email log persist failed: %s', e)
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
        except OperationalError as e:
            logger.exception('SMS log persist failed: %s', e)
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
        except OperationalError as e:
            logger.exception('Wecom log persist failed: %s', e)
            log.failed_reason = str(e)
            log.save(update_fields=['failed_reason'])
            return False

    @staticmethod
    def dispatch(log: NotificationLog) -> bool:
        """根据 channel 分发（同步投递，不做抢占）"""
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

    @staticmethod
    def deliver_log(log: NotificationLog) -> str:
        """投递单条通知 —— **抢占 → 发送 → 落状态**（2026-10-21 卡 F1/F3 共用）。

        与 `dispatch` 的区别：这里先抢占（条件 UPDATE 把 `sending_at` 由 NULL 置 now），
        抢到才发。这样两条投递路径（请求路径入队的即时任务、每小时的重试任务）
        不会对同一条通知重复发送。

        Returns:
            'sent'    发送成功
            'failed'  发送失败（已落 failed_reason, 下一轮可重试）
            'skipped' 未抢到（别人正在发 / 已发过 / 上一轮抢占未超时）
        """
        claimed = NotificationLog.objects.filter(
            pk=log.pk,
            sent_at__isnull=True,
            failed_reason='',
        ).filter(
            Q(sending_at__isnull=True)
            | Q(sending_at__lt=timezone.now() - timedelta(minutes=DELIVER_CLAIM_TTL_MINUTES))
        ).update(sending_at=timezone.now())
        if not claimed:
            return 'skipped'

        try:
            handler = {
                'IN_APP': NotificationDispatcher.send_in_app,
                'EMAIL': NotificationDispatcher.send_email,
                'SMS': NotificationDispatcher.send_sms,
                'WECOM': NotificationDispatcher.send_wecom,
            }.get(log.channel)
            if handler is None:
                success = False
            else:
                success = handler(log)
        except (OperationalError, ValueError, TypeError) as e:
            # Celery 批量重试: ORM 落库失败 + 参数错误窄集。
            # 第三方 IO 异常由 integration 层 swallow 返 False, 不再此层重复捕获。
            logger.exception(f'Notification {log.id} retry failed: {e}')
            log.failed_reason = str(e)
            log.sending_at = None
            log.save(update_fields=['failed_reason', 'sending_at'])
            return 'failed'

        if success:
            log.sent_at = timezone.now()
            log.sending_at = None
            log.save(update_fields=['sent_at', 'sending_at'])
            return 'sent'
        log.failed_reason = '发送失败'
        log.sending_at = None
        log.save(update_fields=['failed_reason', 'sending_at'])
        return 'failed'


# ============================================================
# 通知服务
# ============================================================
def _enqueue_notification(log_id: str) -> None:
    """把通知投递任务入队；broker 不可用时回退同步投递（不丢通知）。

    2026-10-21 卡 F3。异常集刻意收窄（kombu / redis / socket），不新增宽捕获。
    """
    from .tasks import send_notification_log_task

    try:
        send_notification_log_task.delay(log_id)
        return
    except (BrokerOperationalError, RedisError, OSError) as e:
        logger.warning('通知入队失败, 回退同步投递 log=%s err=%s', log_id, e)

    log = NotificationLog.objects.filter(id=log_id, deleted_at__isnull=True).first()
    if log is None:
        return
    NotificationDispatcher.deliver_log(log)


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

        # 2026-10-21 卡 F3: **外部通道调用移出请求路径**。
        #   此前是同步 dispatch —— 邮件/短信/企微各 timeout=10, 外部慢就把 API 请求拖住
        #   (Offer 审批 / 面试安排 / 公告推送 / 自动化规则执行都在请求路径上)。
        #   现改为: 落库后**入队**由 Celery 任务投递, 请求立即返回。
        #   · on_commit: 必须等事务提交后再入队, 否则 worker 抢在提交前读不到本行;
        #   · 兜底 1: broker 不可用(开发机没起 worker) → 同步投递, 不丢通知;
        #   · 兜底 2: 每小时 `send_pending_reminders` 会捡走仍未送达的日志。
        transaction.on_commit(lambda: _enqueue_notification(log.id))
        return {
            'log_id': log.id,
            'channel': log.channel,
            # 语义: True = 已受理(已入队待投递), 不代表第三方已收到
            'sent': True,
            'queued': True,
            'sent_at': None,
        }

    @staticmethod
    def send_bulk(data_list: List[SendNotificationData]) -> List[Dict[str, Any]]:
        """批量发送"""
        results = []
        for data in data_list:
            try:
                result = NotificationService.send_notification(data)
                results.append({'recipient_id': data.recipient_id, **result})
            except (NotFound, OperationalError, ValueError, TypeError) as e:
                # 批量循环: 业务级/参数级/DB IO 异常窄集。编程错误不再吞, 便于发现真实 bug。
                logger.warning('单条通知发送失败 recipient=%s err=%s', data.recipient_id, e, exc_info=True)
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
        event: str | None = None,
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
    link: str = '', source: str = 'SYSTEM', source_id: str | None = None,
    channel: str = 'IN_APP', template_code: str | None = None,
    variables: Dict[str, Any] | None = None,
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
