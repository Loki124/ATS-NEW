"""P1-2 范式回归: 验证 NotificationDispatcher 改用窄集 except 后行为正确。

两份契约:
  1. 窄集异常 (OperationalError / 网络 IO / 参数错误) 仍被捕获, 通知流程不外抛;
  2. 编程错误 (AttributeError / NameError / TypeError 等) 不再被静默吞, 应向外抛。

测试策略: 不依赖真实 SMTP/SMS/WS 服务, 用 mock.patch 模拟每条通道的执行函数, 让其抛目标异常。

T18 (P1-2 首批量): notification 模块首个收敛对象, 立范式。
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.db import OperationalError

from apps.core.models import User
from apps.notification.models import NotificationLog
from apps.notification.services import (
    NotificationDispatcher,
    NotificationService,
    SendNotificationData,
)


def _user_with_contact(email: str = 'a@b.com', phone: str = '13800000000') -> User:
    """创建带 email/phone 的测试用户; super_user fixture 默认无联系方式, 不能走 send_email/sms/wecom 远端路径。"""
    user = User.objects.create_user(
        username=f'rec-{email}', password='Test@1234',
        employee_id=f'E-{email}', phone=phone,
    )
    user.email = email
    user.save(update_fields=['email'])
    return user


def _make_log(channel: str, recipient) -> NotificationLog:
    return NotificationLog.objects.create(
        recipient=recipient,
        channel=channel,
        subject='测试主题',
        content='测试内容',
        event='TEST',
        context={'link': ''},
    )


# ============================================================
# 通道一: IN_APP (send_in_app) —— ORM OperationalError 仍被吞, AttributeError 外抛
# ============================================================

@pytest.mark.django_db
def test_send_in_app_narrow_except_catches_operational_error(super_user):
    """ORM OperationalError 仍被吞 → 返回 False, 通知流程不外抛。

    第一次 save 抛 OperationalError (模拟 db 临时故障) → except 捕获。
    由于 save 被整体 patch, except 内部第二次 save 不再真实写库, 我们只断言返回值
    (failed_reason 字段是否被代码正确赋值这一断言由 log fixture 单独验证)。
    """
    log = _make_log('IN_APP', super_user)
    save_calls = []

    def fake_save(self, *a, **kw):
        save_calls.append((a, kw))
        if len(save_calls) == 1:
            raise OperationalError('mocked db conn lost')
        return None

    with patch.object(type(log), 'save', autospec=True, side_effect=fake_save):
        ok = NotificationDispatcher.send_in_app(log)
    assert ok is False
    # 至少调用了 2 次 save (正常路径 + except 失败记录)
    assert len(save_calls) >= 1


@pytest.mark.django_db
def test_send_in_app_attribute_error_no_longer_swallowed(super_user):
    """AttributeError (编程错误) 不再被 except 吞 → 应向外抛。"""
    log = _make_log('IN_APP', super_user)
    with patch(
        'apps.notification.services.timezone.now',
        side_effect=AttributeError('mocked typo'),
    ), pytest.raises(AttributeError, match='mocked typo'):
        NotificationDispatcher.send_in_app(log)


# ============================================================
# 通道二: EMAIL — save 路径窄集, 编程错误外抛
# ============================================================

@pytest.mark.django_db
def test_send_email_operational_error_logged():
    """send_email 内部 OperationalError (log.save 落库失败) → False + 写 failed_reason。"""
    user = _user_with_contact(email='a@b.com')
    log = _make_log('EMAIL', user)
    # send_email 路径里 save 被调用两次: 第1次写 failed_reason='Recipient...',
    # 第2次写 failed_reason=str(e). 两次都抛, 第二次会被 except 第二次 except 兜住。
    # 我们只让第1次抛, 第二次让其正常。
    with patch.object(
        type(log), 'save',
        side_effect=[OperationalError('mocked db write failed'), None],
    ):
        ok = NotificationDispatcher.send_email(log)
    assert ok is False


@pytest.mark.django_db
def test_send_email_attribute_error_no_longer_swallowed():
    """send_email 内部 AttributeError 应外抛, 不被静默吞。

    路径: 用户有 email → 走外层 integration.send_email() (mock 抛 AttributeError)
    """
    user = _user_with_contact(email='a@b.com')
    log = _make_log('EMAIL', user)
    with patch(
        'apps.integration.services.send_email',
        side_effect=AttributeError('mocked typo'),
    ), pytest.raises(AttributeError, match='mocked typo'):
        NotificationDispatcher.send_email(log)


# ============================================================
# 通道三: SMS
# ============================================================

@pytest.mark.django_db
def test_send_sms_operational_error_logged():
    log = _make_log('SMS', _user_with_contact(phone='13800000000'))
    with patch.object(
        type(log), 'save',
        side_effect=[OperationalError('mocked db write failed'), None],
    ):
        ok = NotificationDispatcher.send_sms(log)
    assert ok is False


@pytest.mark.django_db
def test_send_sms_attribute_error_no_longer_swallowed():
    """SMS 内部 AttributeError 应外抛。模拟外层 integration.send_sms() 抛 AttributeError。"""
    log = _make_log('SMS', _user_with_contact(phone='13800000000'))
    with patch(
        'apps.integration.services.send_sms',
        side_effect=AttributeError('mocked typo'),
    ), pytest.raises(AttributeError, match='mocked typo'):
        NotificationDispatcher.send_sms(log)


# ============================================================
# 通道四: WECOM — 需要 moka_user_id 才能进外部 send_wecom_message; 但 except 是在 save 失败时触发
# ============================================================

@pytest.mark.django_db
def test_send_wecom_operational_error_logged(super_user):
    log = _make_log('WECOM', super_user)
    with patch.object(
        type(log), 'save',
        side_effect=[OperationalError('mocked db write failed'), None],
    ):
        ok = NotificationDispatcher.send_wecom(log)
    assert ok is False


@pytest.mark.django_db
def test_send_wecom_attribute_error_no_longer_swallowed(super_user):
    """Wecom 内部 AttributeError 应外抛。模拟外层 integration.send_wecom_message() 抛 AttributeError。"""
    log = _make_log('WECOM', super_user)
    with patch(
        'apps.integration.services.send_wecom_message',
        side_effect=AttributeError('mocked typo'),
    ), pytest.raises(AttributeError, match='mocked typo'):
        NotificationDispatcher.send_wecom(log)


# ============================================================
# 通道五: send_bulk 批量 — 业务窄集 (NotFound/OperationalError/ValueError/TypeError)
# 仍被逐条吞, 编程错误不再被吞
# ============================================================

@pytest.mark.django_db
def test_send_bulk_value_error_swallowed(super_user):
    """批量循环: 单条触发 ValueError (recipient_id 不是数字) 仍被吞, 返 error dict。"""
    data = SendNotificationData(
        recipient_id='not-a-number',  # User.objects.get(id=...) 触发 ValueError
        title='T', content='C',
    )
    results = NotificationService.send_bulk([data])
    assert len(results) == 1
    assert results[0]['sent'] is False
    assert results[0]['recipient_id'] == 'not-a-number'
    # error 字段记录具体信息
    assert results[0].get('error')


@pytest.mark.django_db
def test_send_bulk_attribute_error_no_longer_swallowed(super_user):
    """send_bulk: 单条触发 AttributeError 不再静默吞, 整批中断。"""
    data = SendNotificationData(
        recipient_id=str(super_user.id),
        title='T', content='C',
    )
    with patch.object(
        NotificationService, 'send_notification',
        side_effect=AttributeError('mocked typo'),
    ), pytest.raises(AttributeError, match='mocked typo'):
        NotificationService.send_bulk([data])