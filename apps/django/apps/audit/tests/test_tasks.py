"""apps/audit 任务回归测试.

覆盖 celery beat 调度的绑定任务签名契约, 防止历史 bug
`audit_cleanup_healthcheck() takes 0 positional arguments but 1 was given`
(装饰器 @shared_task(bind=True) 期望首参 self, 函数却无参) 复发.
"""
import pytest

pytestmark = pytest.mark.v2_permission


@pytest.mark.django_db
def test_audit_cleanup_healthcheck_runs_bound_with_self():
    """绑定任务契约: bind=True 的任务, celery 在调度时会把 self 作为第 1 个位置参数注入.

    若底层函数首参不是 self, beat 每小时调度即抛
    TypeError(takes 0 positional arguments but 1 was given) -> SchedulingError.

    用 .apply() 同步本地执行(与 beat 同一调用路径, 不依赖 broker) 证明 self 已正确注入:
    修复前会复现 TypeError(任务 FAILURE), 修复后返回 dict 且 successful().
    """
    from apps.audit.tasks import audit_cleanup_healthcheck

    real = audit_cleanup_healthcheck._get_current_object()
    result = real.apply()

    assert result.successful(), (
        f'audit_cleanup_healthcheck 执行失败, 可能 self 注入仍异常: {result.result!r}'
    )
    assert isinstance(result.result, dict), f'返回应为 dict, 实际: {result.result!r}'
    assert 'total' in result.result, f'返回缺少 total 字段: {result.result!r}'
