"""Blind-except guard (P1-2)

阻止新增 `except Exception` / `except BaseException` (基类裸除外), 强制收敛到具体异常集合。
本文件不需要任何第三方 lint 依赖, 仅用 stdlib AST; CI / pre-commit / 后续 ruff BLE001 都能复用本逻辑。

约定:
  * `bare except:` (无类型) 计数为 "blind" —— BaseException 语义, 一律禁;
  * `except Exception` / `except BaseException` 及其别名变体 一律 "blind";
  * 仅当目标明确为 (ValueError, TypeError, ...) 这类窄集合时通过。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

APPS_DIR = Path('apps')

# 历史债务基线 (2026-10-01 第六批收敛后快照)。
# 每次新增 batch 收敛必须同步下调 CURRENT_BASELINE; 反向 (新增) 即失败。
#   2026-10-01 首批量 (notification): 196 → 189
#   2026-10-01 第二批 (integration services + suppliers): 189 → 171
#   2026-10-01 第三批 (entry_condition): 171 → 170
#   2026-10-01 第四批 (metrics): 170 → 170 (全 noqa 化, 盲不变)
#   2026-10-01 第五批 (application): 170 → 170 (全 noqa 化, 盲不变)
#   2026-10-01 第六批 (dynamic_field): 170 → 169 (1 处真窄化 signals.py)
CURRENT_BASELINE = 169
HISTORICAL_BASELINE = 196   # 报告 2026-09-27 AST 实测值, 不可上升
HARD_LIMIT = 100            # 第二阶段目标: ≤100 处


def _walk_blind(root: Path) -> list[tuple[str, int, str]]:
    """遍历 root 下的 *.py, 返回所有 (path, lineno, exception_type) 三元组"""
    out: list[tuple[str, int, str]] = []
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
            if n.type is None:
                # bare 'except:' - always catches BaseException, never acceptable
                out.append((str(py), n.lineno, '<bare except:>'))
                continue
            tname = ast.unparse(n.type).strip()
            if tname in {'Exception', 'BaseException'}:
                out.append((str(py), n.lineno, tname))
    return out


@pytest.fixture(scope='module')
def blind() -> list[tuple[str, int, str]]:
    return _walk_blind(APPS_DIR)


def test_bare_except_zero() -> None:
    """最严约束: 任何文件都禁止裸 except: (== BaseException)。
    真出现必须立刻报, 因为这会吞掉 KeyboardInterrupt/SystemExit 等真该外传的信号。"""
    bare = [(p, ln, t) for (p, ln, t) in _walk_blind(APPS_DIR) if t == '<bare except:>']
    assert not bare, (
        f'裸 except: 出现 {len(bare)} 处 (BaseException 语义, 必拦):\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln, _ in bare)
    )


def test_blind_except_at_or_below_current_baseline() -> None:
    """阶段目标: 当前实测必须 ≤ CURRENT_BASELINE (189)。
    收敛一批后请同步下调此数。"""
    current = len(_walk_blind(APPS_DIR))
    assert current <= CURRENT_BASELINE, (
        f'blind except 超当前基线: 实测 {current}, 当前基线 {CURRENT_BASELINE}\n'
        + '请确认是回归还是新代码引入; 回归须修正, 新代码引入须显式收敛。'
    )


def test_blind_except_never_above_historical_baseline() -> None:
    """硬护栏: 历史峰值 196, 任何时点实测不得高于此数 (防"成片回滚")。"""
    current = len(_walk_blind(APPS_DIR))
    assert current <= HISTORICAL_BASELINE, (
        f'blind except 突破历史基线: 当前 {current}, 历史峰值 {HISTORICAL_BASELINE} (2026-09-27)'
    )


@pytest.mark.skip(reason='阶段二启用, 当前 169 > 100 触红, 下一批收敛后摘 skip')
def test_blind_except_below_phase_two_limit() -> None:
    """阶段二目标: ≤100 处。下次批量收敛后摘掉 skip。"""
    current = len(_walk_blind(APPS_DIR))
    assert current <= HARD_LIMIT, (
        f'阶段二目标未达成: 当前 {current}, 上限 {HARD_LIMIT}'
    )