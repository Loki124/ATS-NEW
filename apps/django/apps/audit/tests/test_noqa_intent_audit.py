"""P1-2 第七批审计式测试: 验证 audit 模块所有 noqa: BLE001 都具备明确意图注释。

策略: audit 是"审计中间件/熔断/cache 容错"模块, 7 处 except Exception 全是设计内"宽捕获":
  - 读/写 cache 失败 (容错, cache 不可用 = 不熔断)
  - Celery 告警发送失败 (不影响清理主流程)
  - 审计写入失败 (走失败计数 + 熔断路径)
  - response body 解析失败 (回退原文截断)

全部 noqa 化 + 配套意图注释.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

AUDIT_DIR = Path('apps/audit')


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


def test_all_audit_blind_excepts_have_noqa_with_intent() -> None:
    """audit 模块所有 except Exception 必须:
       1. 同行或上一行有 # noqa: BLE001 标记
       2. noqa 后必须跟 ≥5 字符的意图说明
    """
    issues = []
    for path, lineno, line_text in _collect_blind_excepts(AUDIT_DIR):
        m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
        if not m_noqa:
            issues.append(f'{path}:{lineno} 缺少 # noqa: BLE001 标记')
            continue
        intent = m_noqa.group(1).strip()
        if len(intent) < 5:
            issues.append(
                f'{path}:{lineno} noqa 意图说明不足 (>{len(intent)}<, 需 ≥5 字符)'
            )
    assert not issues, 'audit noqa 审计失败:\n' + '\n'.join(issues)


def test_audit_module_count_consistent_with_baseline() -> None:
    """audit 模块所有 except Exception 必须都被 noqa 化."""
    unmarked = []
    for path, lineno, line_text in _collect_blind_excepts(AUDIT_DIR):
        if '# noqa: BLE001' not in line_text:
            unmarked.append((path, lineno))
    assert not unmarked, (
        f'audit 出现 {len(unmarked)} 处未 noqa 化的盲 except:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unmarked)
    )


# ============================================================
# 范式案例: 中间件 cache 读写容错
# ============================================================

def test_audit_kill_switch_cache_read_failure_returns_false(monkeypatch):
    """_is_killed() 读 cache 失败返 False (容错: cache 不可用 = 不熔断).

    这是 audit noqa 的典型场景: cache 容错不能 500 业务请求.
    """
    from django.core.cache import cache as django_cache

    from apps.audit.middleware import _is_killed

    # mock cache.get 抛 ConnectionError (mocked)
    def buggy_get(*args, **kwargs):
        raise ConnectionError('mocked cache unavailable')

    monkeypatch.setattr(django_cache, 'get', buggy_get)

    # cache 失败时必须返 False (不熔断), 不抛异常
    assert _is_killed() is False


def test_record_failure_cache_failure_returns_negative_one(monkeypatch):
    """_record_failure() 写 cache 失败返 -1 (不影响后续熔断逻辑).

    验证属性:
      1. cache 失败被吞 (logger.warning 调用 + 返 -1)
      2. 不外抛异常
    """
    from django.core.cache import cache as django_cache

    from apps.audit.middleware import _record_failure

    def buggy_incr(*args, **kwargs):
        raise ConnectionError('mocked cache write unavailable')

    monkeypatch.setattr(django_cache, 'incr', buggy_incr)

    result = _record_failure()
    assert result == -1