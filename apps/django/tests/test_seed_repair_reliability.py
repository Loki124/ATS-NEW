"""补种可靠性守卫（2026-10-21 整跑 flaky 根因治理）。

背景：`_repair_committed_seeds` 原来用 `except Exception: pass` 吞掉一切异常，
其中包括 MySQL 1213 死锁 / 1205 锁等待超时这类**瞬时**错误
→ 补种静默失效 → 已提交种子没补回来 → 后续用例批量 403 / DoesNotExist。

实测症状：同一份代码整跑，结果在 0 failed 与 8~18 failed 之间乱跳，
且**失败集合逐轮不同**（403 权限失败 ↔ MySQL 1213 死锁之间游走）。

本文件锁死三件事：
  1. 瞬时数据库错误 → **会重试**，且重试成功后**不算失败**；
  2. 非瞬时错误 → **不重试**（重试无意义），但**必须被记录**（不再静默）；
  3. 真实场景：种子被「flush 掉」后，补种能把它补回来（端到端）。
"""
import pytest
from django.db.utils import IntegrityError, OperationalError

from tests.fixtures_common import (
    _SEED_REPAIR_FAILURES,
    _is_no_db_context,
    _is_transient_db_error,
    _run_with_retry,
    in_test_database,
    seed_repair_failures,
)


class TestNoDbContext:
    """「本来就不该查库」的语境**不是失败** —— 不能刷假告警。"""

    def test_database_operation_forbidden_is_no_db_context(self):
        from django.test.testcases import DatabaseOperationForbidden

        # 注意：它继承的是 AssertionError，不是 RuntimeError
        assert issubclass(DatabaseOperationForbidden, AssertionError)
        assert _is_no_db_context(DatabaseOperationForbidden('no db')) is True

    def test_pytest_django_blocking_is_no_db_context(self):
        assert _is_no_db_context(RuntimeError('Database access not allowed')) is True

    def test_real_db_error_is_not_no_db_context(self):
        assert _is_no_db_context(OperationalError('(1213, deadlock)')) is False

    def test_no_db_context_does_not_record_failure(self):
        before = len(_SEED_REPAIR_FAILURES)

        def blocked():
            raise RuntimeError('Database access not allowed')

        assert _run_with_retry(blocked, 'unit:no_db') is None
        assert len(_SEED_REPAIR_FAILURES) == before, '无 DB 语境不应记为补种失败'


class TestTestDatabaseGate:
    """补种**只允许**作用于测试库。

    🔴 实测过的坑：``pytest_runtest_setup``(tryfirst) 跑在 ``item.setup()`` 之前，
    此时 pytest-django 还没把库名切成测试库 → 补种打到**开发库**：
    ① 污染开发库（实测写入 552 行 role_permission）；
    ② 开发库迁移较旧 → INSERT 报缺列 → 异常被吞 → **测试库的种子一次都没补回来**。
    """

    @pytest.mark.django_db
    def test_inside_test_orm_is_on_test_database(self):
        from django.db import connection

        assert in_test_database() is True, '用例体内必须已在测试库上'
        assert connection.settings_dict['NAME'].startswith('test_')


class TestTransientClassification:
    """异常集必须**收窄**：只对瞬时错误重试。"""

    def test_operational_error_is_transient(self):
        # MySQL 1213 死锁 / 1205 锁等待超时 都走 OperationalError
        exc = OperationalError('(1213, "Deadlock found when trying to get lock")')
        assert _is_transient_db_error(exc) is True

    def test_integrity_error_is_not_transient(self):
        # 唯一约束冲突：重试没有意义（幂等 upsert 已处理）
        assert _is_transient_db_error(IntegrityError('duplicate')) is False

    def test_plain_exception_is_not_transient(self):
        assert _is_transient_db_error(ValueError('boom')) is False


class TestRetryBehaviour:
    """重试语义：瞬时错误重试、非瞬时不重试、失败必须可见。"""

    def test_transient_error_is_retried_then_succeeds(self, monkeypatch):
        monkeypatch.setattr('tests.fixtures_common.time.sleep', lambda _s: None)
        calls = {'n': 0}

        def flaky():
            calls['n'] += 1
            if calls['n'] < 3:
                raise OperationalError('(1213, "Deadlock found when trying to get lock")')
            return 'ok'

        before = len(_SEED_REPAIR_FAILURES)
        assert _run_with_retry(flaky, 'unit:transient') == 'ok'
        assert calls['n'] == 3, '瞬时错误应重试到第 3 次'
        assert len(_SEED_REPAIR_FAILURES) == before, '重试后成功不应记为失败'

    def test_non_transient_error_is_not_retried_but_is_recorded(self, monkeypatch):
        monkeypatch.setattr('tests.fixtures_common.time.sleep', lambda _s: None)
        calls = {'n': 0}

        def broken():
            calls['n'] += 1
            raise IntegrityError('duplicate key')

        before = len(_SEED_REPAIR_FAILURES)
        assert _run_with_retry(broken, 'unit:non_transient') is None
        assert calls['n'] == 1, '非瞬时错误不应重试'
        assert len(_SEED_REPAIR_FAILURES) == before + 1, '失败必须被记录（不能静默）'
        assert _SEED_REPAIR_FAILURES[-1]['label'] == 'unit:non_transient'

    def test_transient_error_exhausted_attempts_is_recorded(self, monkeypatch):
        monkeypatch.setattr('tests.fixtures_common.time.sleep', lambda _s: None)
        calls = {'n': 0}

        def always_deadlock():
            calls['n'] += 1
            raise OperationalError('(1213, "Deadlock found when trying to get lock")')

        before = len(_SEED_REPAIR_FAILURES)
        assert _run_with_retry(always_deadlock, 'unit:exhausted') is None
        assert calls['n'] == 3, '应按 max_attempts 退避重试'
        assert len(_SEED_REPAIR_FAILURES) == before + 1, '重试用尽必须被记录'
        assert '1213' in _SEED_REPAIR_FAILURES[-1]['error']

    def test_seed_repair_failures_returns_copy(self):
        # 暴露的是**副本** → 外部改动不影响内部状态
        snapshot = seed_repair_failures()
        assert isinstance(snapshot, list)
        snapshot.append({'label': 'x', 'error': 'y'})
        assert all(f.get('label') != 'x' for f in seed_repair_failures())


@pytest.mark.django_db
class TestRealRepair:
    """端到端：种子被清掉（模拟 flush）后，补种能补回来。"""

    def test_repair_restores_permission_resources(self):
        from apps.core.models_permission_v2 import PermissionResource
        from tests.fixtures_common import _repair_committed_seeds

        code = 'recruit:candidate:list'
        PermissionResource.objects.filter(resource_code=code).delete()
        assert not PermissionResource.objects.filter(resource_code=code).exists(), '前置条件：种子已被清掉'

        _repair_committed_seeds()

        assert PermissionResource.objects.filter(resource_code=code).exists(), '补种应把资源码补回来'

    def test_repair_restores_role_permission(self):
        from apps.core.models_permission_v2 import RolePermissionV2
        from tests.fixtures_common import _repair_committed_seeds

        RolePermissionV2.objects.filter(
            role_code='HR', resource_code='recruit:candidate:list'
        ).delete()
        assert not RolePermissionV2.objects.filter(
            role_code='HR', resource_code='recruit:candidate:list'
        ).exists(), '前置条件：授权已被清掉'

        _repair_committed_seeds()

        assert RolePermissionV2.objects.filter(
            role_code='HR', resource_code='recruit:candidate:list'
        ).exists(), '补种应把 HR 的授权补回来'

    def test_repair_is_idempotent(self):
        from apps.core.models_permission_v2 import PermissionResource
        from tests.fixtures_common import _repair_committed_seeds

        code = 'recruit:candidate:list'
        _repair_committed_seeds()
        first = PermissionResource.objects.filter(resource_code=code).count()
        _repair_committed_seeds()
        second = PermissionResource.objects.filter(resource_code=code).count()
        assert first == second, '补种必须幂等（重复执行不产生重复行）'
