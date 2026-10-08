"""P1-2 第五批审计式测试: 验证 application 模块所有 noqa: BLE001 都具备明确意图注释。

策略: application 是"状态机/批量任务" 重型模块, 19 处 except Exception 全是设计内"宽捕获":
  - 状态机转换异常统一 re-raise 为 StateTransitionError
  - Celery 批量任务单条失败不影响整体
  - view 层 evaluate 兜底返 500
全部 noqa 化 + 配套意图注释.

未来 PR 想在 application 加新 except Exception 但忘标 noqa 或忘写意图 → 测试红.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

APP_DIR = Path('apps/application')


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


def test_all_application_blind_excepts_have_noqa_with_intent() -> None:
    """application 模块所有 except Exception 必须:
       1. 同行或上一行有 # noqa: BLE001 标记
       2. noqa 后必须跟 ≥5 字符的意图说明

    状态机/批量任务故意宽捕获, 但 noqa 是许可不是默许.
    """
    issues = []
    for path, lineno, line_text in _collect_blind_excepts(APP_DIR):
        m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
        if not m_noqa:
            issues.append(f'{path}:{lineno} 缺少 # noqa: BLE001 标记')
            continue
        intent = m_noqa.group(1).strip()
        if len(intent) < 5:
            issues.append(
                f'{path}:{lineno} noqa 意图说明不足 (>{len(intent)}<, 需 ≥5 字符)'
            )
    assert not issues, 'application noqa 审计失败:\n' + '\n'.join(issues)


def test_application_module_count_consistent_with_baseline() -> None:
    """application 模块所有 except Exception 必须都被 noqa 化."""
    unmarked = []
    for path, lineno, line_text in _collect_blind_excepts(APP_DIR):
        if '# noqa: BLE001' not in line_text:
            unmarked.append((path, lineno))
    assert not unmarked, (
        f'application 出现 {len(unmarked)} 处未 noqa 化的盲 except:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unmarked)
    )


# ============================================================
# 范式案例: ApplicationService.start() 状态机异常 re-raise
# ============================================================

@pytest.mark.django_db
def test_start_application_state_transition_error_on_invalid_state():
    """ApplicationService.start_application 在 PENDING 状态下应走完前置校验; 模拟 fsm-2 抛 Exception 时, except 块将其转为 StateTransitionError.

    这是 application noqa 化的典型场景: 内部 try/except 把 fsm-2 抛的 Exception 子类
    (通常是 TransitionNotAllowed, 但 django-fsm-2 内部包成 Exception) 统一转为
    项目自定义 StateTransitionError.

    测试策略: 用 MagicMock 模拟 Application, 让其 state==PENDING 走完前置校验,
    然后 application.start() 抛 Exception — 验证 except 块将其包成 StateTransitionError.
    """
    from unittest.mock import MagicMock

    from apps.application.models import ApplicationState
    from apps.application.services import ApplicationService
    from apps.application.services.__init__ import StateTransitionError

    mock_app = MagicMock()
    mock_app.state = ApplicationState.PENDING  # 走完前置校验
    mock_app.start.side_effect = Exception('mocked TransitionNotAllowed')

    with pytest.raises(StateTransitionError, match='mocked TransitionNotAllowed'):
        ApplicationService().start_application(mock_app, actor=None)


@pytest.mark.django_db
def test_pause_rejects_resume_state():
    """pause_application 是 free function (services/__init__.py:1070). 模拟 application.pause() 抛 Exception → noqa 块应包成 StateTransitionError."""
    from unittest.mock import MagicMock

    from apps.application.models import ApplicationState
    from apps.application.services import pause_application
    from apps.application.services.__init__ import StateTransitionError

    mock_app = MagicMock()
    mock_app.state = ApplicationState.ACTIVE  # 通过前置 state != ACTIVE 校验, 走到 try 块
    mock_app.pause.side_effect = Exception('mocked TransitionNotAllowed')

    with pytest.raises(StateTransitionError, match='mocked TransitionNotAllowed'):
        pause_application(mock_app, reason='test')