"""P1-2 第十二批审计式测试: 验证 core 模块所有 noqa: BLE001 都具备明确意图注释。

策略: core 是"V2 权限迁移 + 健康检查 + WebSocket 路由 + JWT 认证"模块, 16 处 except Exception 全是设计内"宽捕获":
  - scope_resolver.py fail-closed + V2 字段缺失兜底 (3 处)
  - views_health.py DB/Redis 健康检查 (2 处)
  - views_auth.py JWT 登出失败 (1 处)
  - routing.py Channels WebSocket 推送 (2 处)
  - views_permission_v2.py V2 pk 解包 (1 处)
  - permissions.py deny by default (1 处)
  - serializers_permission_v2.py Person 名字兜底 (1 处)
  - tests/* 测试代码 (2 处)
  - management/commands/* 迁移与 demo 命令 (3 处)

未来 PR 想在 core 加新 except Exception 但忘标 noqa 或忘写意图 → 测试红.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

CORE_DIR = Path('apps/core')


def _collect_blind_excepts(root: Path) -> list[tuple[str, int, str]]:
    out = []
    for py in root.rglob('*.py'):
        if '__pycache__' in py.parts or 'migrations' in py.parts or 'tests' in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.ExceptHandler):
                continue
            if n.type and ast.unparse(n.type) == 'Exception':
                src = py.read_text(encoding='utf-8').splitlines()
                line_text = src[n.lineno - 1] if n.lineno - 1 < len(src) else ''
                out.append((str(py), n.lineno, line_text))
    return out


def test_all_core_blind_excepts_have_noqa_with_intent() -> None:
    """core 模块所有 except Exception 必须:
       1. 同行或上一行有 # noqa: BLE001 标记
       2. noqa 后必须跟 ≥5 字符的意图说明
    """
    issues = []
    for path, lineno, line_text in _collect_blind_excepts(CORE_DIR):
        m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
        if not m_noqa:
            issues.append(f'{path}:{lineno} 缺少 # noqa: BLE001 标记')
            continue
        intent = m_noqa.group(1).strip()
        if len(intent) < 5:
            issues.append(
                f'{path}:{lineno} noqa 意图说明不足 (>{len(intent)}<, 需 ≥5 字符)'
            )
    assert not issues, 'core noqa 审计失败:\n' + '\n'.join(issues)


def test_core_module_count_consistent_with_baseline() -> None:
    """core 模块所有 except Exception 必须都被 noqa 化."""
    unmarked = []
    for path, lineno, line_text in _collect_blind_excepts(CORE_DIR):
        if '# noqa: BLE001' not in line_text:
            unmarked.append((path, lineno))
    assert not unmarked, (
        f'core 出现 {len(unmarked)} 处未 noqa 化的盲 except:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unmarked)
    )


# ============================================================
# 范式案例: health check fail-soft + 权限 deny by default
# ============================================================

@pytest.mark.django_db
def test_health_check_db_failure_returns_degraded_not_500():
    """health_check DB 异常返 degraded (status=503), 不应 500.

    这是 core noqa 的核心契约: 健康检查自身失败是矛盾状态, 必须给降级信号而非崩溃.
    """
    from unittest.mock import patch

    from django.db import connection

    from apps.core.views_health import health_check

    def buggy_cursor():
        from django.db import OperationalError
        raise OperationalError('mocked DB unavailable')

    # mock connection.cursor 让 health check 第一个 try 抛异常
    with patch.object(connection, 'cursor', side_effect=buggy_cursor):
        response = health_check(request=None)
        assert response.status_code == 503
        assert 'error' in response.content.decode() or 'degraded' in response.content.decode()


def test_permissions_deny_by_default():
    """permissions.py 权限检查异常 deny by default (security).

    这是 core noqa 的安全契约: 权限检查失败必须 deny, 不应因异常放行.
    """
    from unittest.mock import MagicMock, patch

    from apps.core.permissions import ResourceScoped

    perm = ResourceScoped()

    # mock user: 不是超管, 没有 SUPER_ADMIN 角色
    mock_user = MagicMock()
    mock_user.is_authenticated = True
    mock_user.is_superuser = False
    mock_user.pk = 'u-1'

    # mock view 注入 resource_code
    mock_view = MagicMock()
    mock_view.resource_code = 'recruit:candidate'

    mock_request = MagicMock()
    mock_request.user = mock_user

    # mock is_super_admin 返 False (确保不会因超管绕过)
    # mock resolve_scope 抛 RuntimeError
    with patch('apps.core.permissions.is_super_admin', return_value=False), \
         patch('apps.core.scope_resolver.resolve_scope', side_effect=RuntimeError('mocked scope crash')):
        result = perm.has_permission(mock_request, mock_view)
        assert result is False, '权限检查异常必须 deny by default'


def test_scope_resolver_fail_closed_on_unexpected_exception():
    """scope_resolver.py 非 DB 异常 fail-closed 到 SELF (空 list), 不应放行.

    这是 core noqa 的关键安全契约: scope 计算异常时收紧而非放宽权限.
    """
    from unittest.mock import MagicMock, patch

    from apps.core import scope_resolver

    # mock UserRoleV2.objects.filter 返回一个会让 management_unit_ids 抛 ValueError 的对象
    mock_ur = MagicMock()
    type(mock_ur).management_unit_ids = MagicMock(side_effect=ValueError('mocked logic error'))
    type(mock_ur).id = 'ur-1'
    type(mock_ur).role_code = 'rc-1'  # 不要抛

    with patch.object(scope_resolver, 'UserRoleV2') as MockUserRoleV2:
        MockUserRoleV2.objects.filter.return_value = [mock_ur]
        user = MagicMock()
        user.pk = 'u-1'
        user.is_authenticated = True
        result = scope_resolver.resolve_scope(user, resource_code='recruit:candidate')
        # fail-closed: 异常时返空 management_unit_ids (收紧而非放宽)
        assert result == {'management_unit_ids': []}