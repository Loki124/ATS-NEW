"""F3 —— 通知外部通道调用移出请求路径（2026-10-21）

**缺陷**：`NotificationService.send_notification` 此前**同步**调用
`NotificationDispatcher.dispatch(log)` → 邮件/短信/企微各 `timeout=10`。
而它在请求路径上被调用（Offer 审批 / 面试安排 / 公告推送 / 自动化规则执行）——
外部通道慢，**API 请求就跟着卡住**（最坏 10s × 通道数）。

**改法**：
1. 落库后 `transaction.on_commit(...)` **入队**由 Celery 任务投递，请求立即返回；
   - 用 `on_commit` 是必须的：不等事务提交就入队，worker 会抢在提交前读不到这一行；
2. 兜底 1：broker 不可用（开发机没起 worker）→ 同步投递，**不丢通知**；
3. 兜底 2：每小时 `send_pending_reminders` 会捡走仍未送达的日志。

**关于 worker 依赖**：本改动让「通知投递」也依赖 Celery worker。这**不是新假设** ——
系统本就有依赖 worker 的定时任务（每小时提醒重试 / 每日看板快照 / GDPR 保留期清理），
worker 不起时那些同样不跑。

**本文件锁死**：请求路径**不得**同步调外部通道；任务路径才真正发送。

注：测试里**直接调用任务函数**而不是 `.delay()` —— 本仓测试环境的 `current_app` 是 Celery
默认 app，未继承 Django 的 `CELERY_TASK_ALWAYS_EAGER`（实测 `current_app.conf.task_always_eager=False`），
`.delay()` 会真投到 broker 而不是本地执行。任务函数体本身与投递方式无关。
"""
import pytest

from apps.notification.models import NotificationLog
from apps.notification.services import NotificationService, SendNotificationData
from apps.notification.tasks import send_notification_log_task, send_pending_reminders

pytestmark = pytest.mark.django_db


@pytest.fixture
def mail_user(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(
        username='f3_mail_user', password='Test@1234', email='f3@example.com',
    )


def _patch_email(monkeypatch):
    calls = []
    monkeypatch.setattr(
        'apps.integration.services.send_email',
        lambda **kw: calls.append(kw) or True,
    )
    return calls


def test_request_path_does_not_call_external_channel(mail_user, monkeypatch):
    """请求路径只落库 + 入队, 不碰外部通道。"""
    calls = _patch_email(monkeypatch)

    result = NotificationService.send_notification(SendNotificationData(
        recipient_id=str(mail_user.id), title='标题', content='内容', channel='EMAIL',
    ))

    assert result['queued'] is True
    assert result['sent'] is True          # 语义: 已受理(已入队待投递)
    assert calls == [], '请求路径不得同步调用外部通道'

    log = NotificationLog.objects.get(id=result['log_id'])
    assert log.sent_at is None             # 还没真发
    assert log.failed_reason == ''


def test_queued_task_actually_delivers(mail_user, monkeypatch):
    """入队任务执行后才真正发送（并落 sent_at）。"""
    calls = _patch_email(monkeypatch)
    result = NotificationService.send_notification(SendNotificationData(
        recipient_id=str(mail_user.id), title='标题', content='内容', channel='EMAIL',
    ))
    log = NotificationLog.objects.get(id=result['log_id'])

    send_notification_log_task(log.id)

    log.refresh_from_db()
    assert len(calls) == 1
    assert log.sent_at is not None
    assert log.sending_at is None


def test_hourly_task_is_the_safety_net(mail_user, monkeypatch):
    """兜底: 即时任务没跑成时, 每小时重试任务会捡走未送达的日志。"""
    calls = _patch_email(monkeypatch)
    result = NotificationService.send_notification(SendNotificationData(
        recipient_id=str(mail_user.id), title='标题', content='内容', channel='EMAIL',
    ))
    assert calls == []

    r = send_pending_reminders()

    assert r['sent'] == 1, r
    assert len(calls) == 1
    log = NotificationLog.objects.get(id=result['log_id'])
    assert log.sent_at is not None


def test_hourly_task_does_not_double_send(mail_user, monkeypatch):
    """已送达的不会被每小时任务重发。"""
    calls = _patch_email(monkeypatch)
    result = NotificationService.send_notification(SendNotificationData(
        recipient_id=str(mail_user.id), title='标题', content='内容', channel='EMAIL',
    ))
    send_notification_log_task(result['log_id'])
    assert len(calls) == 1

    r = send_pending_reminders()

    assert r['sent'] == 0
    assert len(calls) == 1, '已送达的通知不得被每小时任务重复发送'
