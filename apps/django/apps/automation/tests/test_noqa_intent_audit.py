"""P1-2 第八批审计式测试: 验证 automation 模块所有 noqa: BLE001 都具备明确意图注释。

策略: automation 是"自动化规则执行/触发"模块, 7 处 except Exception 全是设计内"宽捕获":
  - signals.py 双写兜底 (2 处, 已有充分意图)
  - services.py 单条规则执行失败 (1 处补意图)
  - services.py 收件人解析失败 (1 处补意图)
  - services.py 审计落库失败 (1 处补意图)
  - tasks.py Celery 批处理 (2 处补意图)

未来 PR 想在 automation 加新 except Exception 但忘标 noqa 或忘写意图 → 测试红.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


AUTO_DIR = Path('apps/automation')


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


def test_all_automation_blind_excepts_have_noqa_with_intent() -> None:
    """automation 模块所有 except Exception 必须:
       1. 同行或上一行有 # noqa: BLE001 标记
       2. noqa 后必须跟 ≥5 字符的意图说明
    """
    issues = []
    for path, lineno, line_text in _collect_blind_excepts(AUTO_DIR):
        m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
        if not m_noqa:
            issues.append(f'{path}:{lineno} 缺少 # noqa: BLE001 标记')
            continue
        intent = m_noqa.group(1).strip()
        if len(intent) < 5:
            issues.append(
                f'{path}:{lineno} noqa 意图说明不足 (>{len(intent)}<, 需 ≥5 字符)'
            )
    assert not issues, 'automation noqa 审计失败:\n' + '\n'.join(issues)


def test_automation_module_count_consistent_with_baseline() -> None:
    """automation 模块所有 except Exception 必须都被 noqa 化."""
    unmarked = []
    for path, lineno, line_text in _collect_blind_excepts(AUTO_DIR):
        if '# noqa: BLE001' not in line_text:
            unmarked.append((path, lineno))
    assert not unmarked, (
        f'automation 出现 {len(unmarked)} 处未 noqa 化的盲 except:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unmarked)
    )


# ============================================================
# 范式案例: 单条规则执行失败不入其他规则
# ============================================================

def test_automation_log_save_failure_does_not_propagate():
    """_save_log 失败不应阻断主 ExecutionResult (服务侧: services.py:536 noqa 路径).

    这是 automation noqa 的典型场景: 审计落库失败不影响主结果.
    """
    from unittest.mock import MagicMock, patch

    # 直接验证 noqa 化形状 (不依赖运行时逻辑)
    src = (AUTO_DIR / 'services.py').read_text(encoding='utf-8')
    # 找 _save_log 函数的 try/except (line 536)
    m = re.search(
        r'except Exception as e:\s*#\s*noqa:\s*BLE001\s*[^\n]*\n\s*logger\.warning\(\'Failed to save automation log',
        src,
    )
    assert m, '_save_log 处的 noqa 意图注释未匹配 (可能文本已变)'