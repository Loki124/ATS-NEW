"""F1 / F2 —— Celery 幂等化与重试配置（2026-10-21）

**F1 幂等化**
- 每日看板快照：同一天重跑**只更新同一条**（原先每次 create → 看板出现重复快照）；
- 提醒发送：改「**先标记后发**」—— 发送前用条件 UPDATE 抢占本行 (sending_at)，
  抢到才发；抢不到（别人正在发 / 上一轮刚抢过）跳过；抢占超 5 分钟视为上一轮崩溃 → 重新抢占。
  修的是「外部通道已收到、但落 sent_at 前进程崩溃 → 下一轮重发」的重复通知窗口。

**F2 重试配置**
- 只加 `max_retries` **不会自动重试**，必须配 `autoretry_for(瞬时异常)`；
- 选 `django.db.OperationalError`（DB 抖动/死锁/连接断开）：它是 DatabaseError 子类但
  **不含** IntegrityError / ProgrammingError（非瞬时，重试无意义）。
- 本文件末尾有一条**静态守卫**，防止重试配置被后续改动回退。
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.analytics.models import ReportSnapshot
from apps.analytics.tasks import generate_daily_report_snapshot
from apps.notification.models import NotificationLog
from apps.notification.tasks import send_pending_reminders

pytestmark = pytest.mark.django_db


# ══════════════════════════════════════════════════════════════════
# F1-a 每日快照幂等
# ══════════════════════════════════════════════════════════════════

class TestDailySnapshotIdempotent:
    def test_run_twice_keeps_one_snapshot(self):
        """同一天跑两次 → 仍然只有一条快照 (且 id 相同)。"""
        first = generate_daily_report_snapshot()
        second = generate_daily_report_snapshot()

        assert first['snapshot_id'] == second['snapshot_id']
        assert ReportSnapshot.objects.count() == 1
        assert second['created'] is False

    def test_snapshot_key_is_unique_constraint(self):
        """幂等键有 DB 级唯一约束兜底 (并发跑也不会插出两条)。"""
        from django.db import IntegrityError, transaction

        with transaction.atomic():
            ReportSnapshot.objects.create(
                name='重复键', report_type='DASHBOARD', snapshot_key='DASHBOARD:2026-01-01',
            )
            with pytest.raises(IntegrityError):
                ReportSnapshot.objects.create(
                    name='重复键2', report_type='DASHBOARD', snapshot_key='DASHBOARD:2026-01-01',
                )

    def test_snapshot_without_key_unaffected(self):
        """幂等键为 NULL 的快照不受唯一约束影响 (MySQL 唯一索引允许多个 NULL)。"""
        ReportSnapshot.objects.create(name='手工快照A', report_type='DASHBOARD')
        ReportSnapshot.objects.create(name='手工快照B', report_type='DASHBOARD')
        assert ReportSnapshot.objects.count() == 2


# ══════════════════════════════════════════════════════════════════
# F1-b 提醒「先标记后发」
# ══════════════════════════════════════════════════════════════════

def _make_log(user, **kwargs):
    defaults = {
        'channel': 'IN_APP', 'subject': '提醒', 'content': '内容', 'event': 'TEST_EVENT',
    }
    defaults.update(kwargs)
    return NotificationLog.objects.create(recipient=user, **defaults)


@pytest.fixture
def mail_user(db, hr_user):
    """收件人（带邮箱）—— 投递走 NotificationDispatcher, 无邮箱会被直接判失败并记原因。"""
    hr_user.email = 'hr_zhang_f1@example.com'
    hr_user.save(update_fields=['email'])
    return hr_user


class TestReminderClaimBeforeSend:
    def test_sent_once_then_not_resent(self, mail_user, monkeypatch):
        """发过一次 → 再跑一轮不会再发 (sent_at 已置位)。"""
        sent_calls = []

        def _fake_send(**kwargs):
            sent_calls.append(kwargs)
            return True

        monkeypatch.setattr('apps.integration.services.send_email', _fake_send)
        log = _make_log(mail_user, channel='EMAIL')

        r1 = send_pending_reminders()
        assert r1['sent'] == 1
        assert len(sent_calls) == 1

        r2 = send_pending_reminders()
        assert r2['sent'] == 0
        assert len(sent_calls) == 1, '已发送的通知不得重复发送'
        log.refresh_from_db()
        assert log.sent_at is not None
        assert log.sending_at is None

    def test_fresh_claim_is_skipped(self, mail_user, monkeypatch):
        """别的 worker 刚抢占 (sending_at 是新的) → 跳过, 不重复发。"""
        sent_calls = []
        monkeypatch.setattr(
            'apps.integration.services.send_email',
            lambda **kw: sent_calls.append(kw) or True,
        )
        log = _make_log(mail_user, channel='EMAIL', sending_at=timezone.now())

        r = send_pending_reminders()
        assert r['sent'] == 0
        assert r['skipped_locked'] == 1
        assert sent_calls == []
        log.refresh_from_db()
        assert log.sending_at is not None, '未完成的抢占应保留 (等超时后再抢)'

    def test_stale_claim_is_reclaimed(self, mail_user, monkeypatch):
        """抢占超 5 分钟 (上一轮崩溃) → 允许重新抢占并发送 (既不重复也不漏发)。"""
        sent_calls = []
        monkeypatch.setattr(
            'apps.integration.services.send_email',
            lambda **kw: sent_calls.append(kw) or True,
        )
        log = _make_log(
            mail_user, channel='EMAIL',
            sending_at=timezone.now() - timedelta(minutes=6),
        )

        r = send_pending_reminders()
        assert r['sent'] == 1
        assert len(sent_calls) == 1
        log.refresh_from_db()
        assert log.sent_at is not None
        assert log.sending_at is None

    def test_failed_send_releases_claim(self, mail_user, monkeypatch):
        """发送失败 → 释放抢占 (sending_at 置回 NULL), 下一轮可再试。"""
        monkeypatch.setattr(
            'apps.integration.services.send_email',
            lambda **kw: False,
        )
        log = _make_log(mail_user, channel='EMAIL')

        r = send_pending_reminders()
        assert r['failed'] == 1
        log.refresh_from_db()
        assert log.sending_at is None
        assert log.failed_reason


# ══════════════════════════════════════════════════════════════════
# F2 重试配置（静态守卫）
# ══════════════════════════════════════════════════════════════════

RETRY_TASKS = [
    'apps.analytics.tasks.run_export_task',
    'apps.analytics.tasks.generate_daily_report_snapshot',
    'apps.gdpr.tasks.run_retention_cleanup',
    'apps.invitation.tasks.cleanup_expired',
    'apps.invitation.tasks.send_invitation_reminders',
    'apps.notification.tasks.send_pending_reminders',
    'apps.talent_pool.tasks.recommend_candidates',
    'apps.talent_pool.tasks.cleanup_inactive_entries',
    'apps.metrics.tasks.filter_by_scene_task',
    'apps.add_candidate.tasks.send_async_notification_task',
]


@pytest.mark.parametrize('task_path', RETRY_TASKS)
def test_task_has_retry_config(task_path):
    """每个易失败任务都要有 max_retries + autoretry_for（否则重试配置形同虚设）。"""
    from importlib import import_module

    module_path, attr = task_path.rsplit('.', 1)
    task = getattr(import_module(module_path), attr)

    assert task.max_retries and task.max_retries >= 3, f'{task_path} 缺 max_retries'
    assert task.default_retry_delay, f'{task_path} 缺 default_retry_delay'
    assert task.autoretry_for, (
        f'{task_path} 只配了 max_retries 而没有 autoretry_for —— '
        'Celery 不会自动重试, 异常必须真正逃出任务体才会被重跑'
    )
    assert any(exc.__name__ == 'OperationalError' for exc in task.autoretry_for), (
        f'{task_path} 的 autoretry_for 应含 OperationalError (DB 抖动等瞬时异常)'
    )
