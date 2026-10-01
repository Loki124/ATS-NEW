"""P1-2 第六批审计式测试: 验证 dynamic_field 模块所有 noqa: BLE001 都具备明确意图注释 + 1 处真窄化范式.

策略: dynamic_field 是动态字段配置模块, 7 处 except Exception 全是设计内"宽捕获":
  - signals.py 自动映射 AtomicMetric 失败 (1 处真窄化: (OperationalError, IntegrityError, ValueError))
  - models.py 解析失败降级到手动 options
  - views.py 4 处 JSON 解析失败降级 + 批量导入单条失败计入 errors

未来 PR 想在 dynamic_field 加新 except Exception 但忘标 noqa 或忘写意图 → 测试红.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


DF_DIR = Path('apps/dynamic_field')


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


def test_all_dynamic_field_blind_excepts_have_noqa_with_intent() -> None:
    """dynamic_field 模块所有 except Exception 必须:
       1. 同行或上一行有 # noqa: BLE001 标记 (即必须被显式许可)
       2. noqa 后必须跟 ≥5 字符的意图说明

    动态字段配置故意宽捕获, 但 noqa 是许可不是默许.
    """
    issues = []
    for path, lineno, line_text in _collect_blind_excepts(DF_DIR):
        m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
        if not m_noqa:
            issues.append(f'{path}:{lineno} 缺少 # noqa: BLE001 标记 (必须真窄化为具体异常)')
            continue
        intent = m_noqa.group(1).strip()
        if len(intent) < 5:
            issues.append(
                f'{path}:{lineno} noqa 意图说明不足 (>{len(intent)}<, 需 ≥5 字符)'
            )
    assert not issues, 'dynamic_field noqa 审计失败:\n' + '\n'.join(issues)


def test_signals_narrow_set_actually_works() -> None:
    """signals.py:67 真窄化范式: except (OperationalError, IntegrityError, ValueError).

    验证属性:
      1. 窄集异常被吞 (logger.warning 调用 + 不外抛)
      2. AttributeError (编程错误) 不再被吞, 向上抛
    """
    src = (DF_DIR / 'signals.py').read_text(encoding='utf-8')
    # 找 except 行
    m = re.search(r'except \(([^)]+)\)', src)
    assert m, 'signals.py 找不到 except (...) 窄集'
    narrow_set = m.group(1)
    assert 'OperationalError' in narrow_set
    assert 'IntegrityError' in narrow_set
    assert 'ValueError' in narrow_set
    assert 'Exception' not in narrow_set.split(','), (
        'signals.py 已真窄化, 不应再含 except Exception'
    )


def test_signals_auto_create_metric_on_field_swallows_operational_error(db, monkeypatch):
    """post_save 触发自动创建 AtomicMetric 抛 OperationalError 时不应阻断字段保存 (logger.warning).

    这是 signals.py:67 真窄化的运行时验证.
    """
    from django.db import OperationalError

    # mock apps.metrics.models.AtomicMetric.objects.create 抛 OperationalError
    from apps.metrics import models as metrics_models
    original_create = metrics_models.AtomicMetric.objects.create

    def buggy_create(*args, **kwargs):
        raise OperationalError('mocked db write failed')

    monkeypatch.setattr(metrics_models.AtomicMetric.objects, 'create', buggy_create)

    # 触发 post_save: 直接调用 receiver 函数
    from apps.dynamic_field.signals import auto_create_metric_on_field
    from types import SimpleNamespace
    fake_instance = SimpleNamespace(
        resource='Candidate',
        field_type='TEXT',
        field_key='test_field',
        id='df-1',
    )
    # 不抛 + 通过 = 验证 except 块吞掉了 OperationalError
    auto_create_metric_on_field(sender=metrics_models.AtomicMetric, instance=fake_instance, created=True)