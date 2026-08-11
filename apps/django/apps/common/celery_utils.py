"""Celery 共享工具

提供:
- 调度任务的统一重试配置 (基于数据库抖动场景)
- 连续失败告警 (通过 NotificationService 通知超管)
- 任务执行上下文记录

设计原则 (P0-2 修复):
1. 任何调度任务必须配置 autoretry_for,避免单次 DB 抖动漏跑 30 分钟
2. 连续失败 N 次后,主动通知超管 (而非仅写日志)
3. 与 celery_app.py 的 task_acks_late=True 配合,保证任务不丢
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from celery import shared_task as _celery_shared_task
from django.core.cache import cache
from django.db import OperationalError, InterfaceError

logger = logging.getLogger(__name__)

# === 需要重试的异常 (网络/DB 抖动,不应让任务直接死) ===
DB_RETRY_EXCEPTIONS: tuple = (
    OperationalError,   # MySQL/Postgres 连接断开
    InterfaceError,     # pymysql/mysqlclient 底层连接错误
    ConnectionError,    # Redis/Celery broker 断
    TimeoutError,       # 网络超时
)

# === 需要立即告警的异常 (业务逻辑错误,重试也救不了) ===
BUSINESS_ERROR_EXCEPTIONS: tuple = (
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)

# === 告警阈值 ===
FATAL_FAILURE_THRESHOLD = 3      # 连续 3 次失败升级为告警
ALERT_COUNTER_TTL = 24 * 3600    # 计数保留 24 小时

F = TypeVar('F', bound=Callable[..., Any])


def _incr_failure_count(task_name: str) -> int:
    """原子增加失败计数,返回累计失败次数

    使用 Django cache API (而非直接 redis-py),确保与配置解耦:
    - 生产用 Redis: 真实原子
    - 开发用 locmem: 进程内仍然原子
    - 失败时返回 -1 表示计数失败,但不阻断主流程
    """
    key = f'celery:fail_count:{task_name}'
    try:
        # incr 第一次会 KeyError,需要 add 初始化
        try:
            count = cache.incr(key)
        except ValueError:
            cache.add(key, 1, timeout=ALERT_COUNTER_TTL)
            count = 1
        return int(count)
    except Exception as exc:  # noqa: BLE001
        logger.warning('celery_utils: 失败计数失败 (%s): %s', task_name, exc)
        return -1


def _clear_failure_count(task_name: str):
    """任务成功完成后,清除失败计数"""
    try:
        cache.delete(f'celery:fail_count:{task_name}')
        # 顺手清理历史告警 key (不同 retry_count 级别的)
        for retry_count in range(1, FATAL_FAILURE_THRESHOLD + 3):
            cache.delete(f'celery:alert_sent:{task_name}:{retry_count}')
    except Exception:  # noqa: BLE001
        pass


def _alert_on_fatal_failure(task_name: str, exc: BaseException, retry_count: int):
    """连续失败达到阈值时,通过 NotificationService 通知超管

    触发条件: 同一任务名连续失败 >= FATAL_FAILURE_THRESHOLD 次
    升级机制: 每次 retry_count 达新阈值才发一次告警,避免告警风暴
    """
    if retry_count < FATAL_FAILURE_THRESHOLD:
        return

    alert_key = f'celery:alert_sent:{task_name}:{retry_count}'
    if cache.get(alert_key):
        return  # 同级别已发过,跳过
    cache.set(alert_key, '1', timeout=ALERT_COUNTER_TTL)

    try:
        from apps.notification.services import NotificationService
        from apps.core.models import User

        admins = list(User.objects.filter(is_superuser=True, is_active=True)[:5])
        for admin in admins:
            try:
                NotificationService.send_notification(
                    recipient=admin,
                    event='celery.task_fatal_failure',
                    context={
                        'task_name': task_name,
                        'retry_count': retry_count,
                        'exception_type': type(exc).__name__,
                        'exception_message': str(exc)[:500],
                    },
                    channels=['IN_APP', 'EMAIL'],
                )
            except Exception as notify_exc:  # noqa: BLE001
                logger.exception(
                    'celery_utils: 告警通知失败给 %s: %s',
                    admin.username, notify_exc,
                )
        logger.error(
            'celery_utils: %s 连续失败 %d 次,已尝试通知 %d 位超管',
            task_name, retry_count, len(admins),
        )
    except Exception as outer_exc:  # noqa: BLE001
        # 告警发送失败不能影响原任务重试
        logger.exception('celery_utils: 告警发送整体失败: %s', outer_exc)


def retryable_scheduled_task(
    *,
    name: str,
    bind: bool = True,
    max_retries: int = 3,
    retry_backoff: int = 60,
    retry_backoff_max: int = 600,
    retry_jitter: bool = True,
):
    """调度任务装饰器 - 统一重试 + 告警 + 计数

    用法:
        @retryable_scheduled_task(name='apps.foo.tasks.bar')
        def bar():
            ...

    行为:
    - DB_RETRY_EXCEPTIONS 触发: 指数退避重试,最多 max_retries 次
    - 达到 max_retries 仍失败: 通知超管 + 抛出原异常
    - 业务异常 (ValueError 等): 不重试,直接抛出 (避免无效重试)
    - 任务成功: 清除失败计数
    """
    def decorator(func: F) -> F:
        @_celery_shared_task(
            bind=bind,
            name=name,
            autoretry_for=DB_RETRY_EXCEPTIONS,
            retry_backoff=retry_backoff,
            retry_backoff_max=retry_backoff_max,
            retry_jitter=retry_jitter,
            max_retries=max_retries,
            acks_late=True,  # 任务执行完才确认,与 celery_app.py 配合
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            # bind=True 时 Celery 把 Task 实例作为第一个位置参数传进来。
            # 它只用于取 retry 计数，**不得透传给业务函数** —— 本装饰器的契约
            # （见上方 docstring 的用法示例）就是业务函数不带 self。
            #
            # P0 修复（2026-08-10）：原实现为
            #     result = func(self, *args, **kwargs) if bind else func(*args, **kwargs)
            # 而 bind 默认 True，于是全仓 3 个使用者全部按 docstring 定义成 0 参数：
            #   automation.run_scheduled_rules
            #   time_limit.check_stage_time_limit
            #   time_limit.send_deadline_warnings
            # 一经调度即抛 TypeError('takes 0 positional arguments but 1 was given')，
            # 随后被下方 BUSINESS_ERROR_EXCEPTIONS 记一条日志后重抛。
            # 这三个任务此前零测试覆盖，所以从没人发现它们「从来没跑通过」——
            # 这也正是 tasks.py 里实参传反（P0-C/D）能长期潜伏的原因：函数根本进不去。
            task_self = args[0] if (bind and args) else None
            call_args = args[1:] if bind else args
            try:
                result = func(*call_args, **kwargs)
                _clear_failure_count(name)
                return result
            except DB_RETRY_EXCEPTIONS as exc:
                # celery autoretry 实际不抛到这里 (它会捕获并重试)
                # 但若达到 max_retries 仍失败,会作为原始异常重抛
                retry_count = task_self.request.retries if task_self is not None else 0
                _alert_on_fatal_failure(name, exc, retry_count)
                raise
            except BUSINESS_ERROR_EXCEPTIONS:
                # 业务错误 - 不重试,也不静默
                logger.exception('celery_utils: %s 业务错误,不重试:', name)
                raise

        return wrapper  # type: ignore[return-value]
    return decorator
