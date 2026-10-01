"""P1-2 第四批审计式测试: 验证 metrics 模块所有 noqa: BLE001 都具备明确意图注释。

策略: metrics 是"派生计算层", 23 处 except Exception 全是设计内"宽捕获"
(快照失败 / 缓存失败 / DB 异常等), 全部 noqa 化 + 配套意图注释.

未来 PR 想在 metrics 加新 except Exception 但忘标 noqa 或忘写意图 → 测试红.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


METRICS_DIR = Path('apps/metrics')


def _collect_blind_excepts(root: Path) -> list[tuple[str, int, str]]:
    """扫描 *.py, 返回 (path, lineno, line_text) 三元组."""
    import ast
    out = []
    for py in root.rglob('*.py'):
        if '__pycache__' in py.parts or 'migrations' in py.parts:
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


def test_all_metrics_blind_excepts_have_noqa_with_intent() -> None:
    """metrics 模块所有 except Exception 必须:
       1. 同行或上一行有 # noqa: BLE001 标记
       2. noqa 后必须跟 ≥5 字符的意图说明 (不是空白)

    派生计算层故意宽捕获, 但 noqa 是许可不是默许.
    """
    issues = []
    for path, lineno, line_text in _collect_blind_excepts(METRICS_DIR):
        # 检查 noqa 标记
        m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
        if not m_noqa:
            issues.append(f'{path}:{lineno} 缺少 # noqa: BLE001 标记')
            continue
        # 检查意图说明 (≥5 字符)
        intent = m_noqa.group(1).strip()
        if len(intent) < 5:
            issues.append(
                f'{path}:{lineno} noqa 意图说明不足 (>{len(intent)}<, 需 ≥5 字符)'
            )

    assert not issues, 'metrics noqa 审计失败:\n' + '\n'.join(issues)


def test_metrics_module_count_consistent_with_baseline() -> None:
    """metrics 模块所有 except Exception 必须都被 noqa 化.

    派生计算层故意宽捕获, 但 # noqa: BLE001 是显式许可,
    没有 noqa 标记的 except Exception 视为"忘记标注", 应当被全局基线 (test_no_blind_except.py) 抓红.
    本测试同时校验: 即使 noqa 化让全局基线放过它们, metrics 自己内部审计也确认 0 处未标注.
    """
    unmarked = []
    for path, lineno, line_text in _collect_blind_excepts(METRICS_DIR):
        if '# noqa: BLE001' not in line_text:
            unmarked.append((path, lineno))
    assert not unmarked, (
        f'metrics 出现 {len(unmarked)} 处未 noqa 化的盲 except; 必须配 noqa 注释或真窄化为具体异常:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unmarked)
    )


# ============================================================
# 范式案例: MetricEngine._op_label 故意保留 noqa (容错优先)
# ============================================================

def test_op_label_returns_original_string_for_unknown_operator():
    """_op_label 对未知运算符返原值 (容错, 不阻断比较逻辑).

    这是 metrics noqa 的典型场景: 展示原文比抛异常更有价值.
    """
    from apps.metrics.services.metric_engine import MetricEngine
    # 已知运算符 → 返 label
    assert MetricEngine._op_label('GT') == '大于'
    # 未知运算符 → 返原值字符串 (容错)
    assert MetricEngine._op_label('UNKNOWN_OP_XYZ') == 'UNKNOWN_OP_XYZ'
    assert MetricEngine._op_label(None) == ''
    assert MetricEngine._op_label('') == ''


def test_op_label_intent_comment_exists():
    """_op_label 的 except Exception 必须有 noqa + 意图说明.

    测试具体到文件 + 函数, 防止未来 PR 偷偷删掉意图注释.
    """
    src = (METRICS_DIR / 'services/metric_engine.py').read_text(encoding='utf-8')
    # 找 _op_label 函数 + 它内部 except Exception
    fn_match = re.search(
        r'def _op_label\([^)]*\)[^:]*:\s*\n\s*try:.*?\n\s*except Exception[^\n]*',
        src, re.DOTALL,
    )
    assert fn_match, '_op_label 函数或 except Exception 未找到'
    assert '# noqa: BLE001' in fn_match.group(0), \
        '_op_label 的 except Exception 缺少 noqa 标记'
    assert '容错' in fn_match.group(0) or '容错' in fn_match.group(0), \
        '_op_label 的 noqa 缺少意图说明 (容错)'