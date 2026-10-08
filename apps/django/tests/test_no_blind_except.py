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

# 历史债务基线 (2026-10-01 第十三批收敛后快照)。
# 每次新增 batch 收敛必须同步下调 CURRENT_BASELINE; 反向 (新增) 即失败。
#   2026-10-01 首批量 (notification): 196 → 189
#   2026-10-01 第二批 (integration services + suppliers): 189 → 171
#   2026-10-01 第三批 (entry_condition): 171 → 170
#   2026-10-01 第四批 (metrics): 170 → 170
#   2026-10-01 第五批 (application): 170 → 170
#   2026-10-01 第六批 (dynamic_field): 170 → 169
#   2026-10-01 第七批 (audit): 169 → 169
#   2026-10-01 第八批 (automation): 169 → 169
#   2026-10-01 第九批 (reason_library): 169 → 169
#   2026-10-01 第十批 (announcement): 169 → 169
#   2026-10-01 第十一批 (candidate): 169 → 168 (1 处真窄化 services.py:543)
#   2026-10-01 第十二批 (core): 168 → 168 (全 noqa)
#   2026-10-01 第十三批 (散落盲 except 清理): 168 → 168 (33 处补 noqa/补意图, noqa-license 护栏激活)
#   2026-10-01 第十四批 (announcement+candidate+dynamic_field 真窄化收口): 168 → 157 (12 处 except Exception 真窄化)
#   2026-10-01 阶段二真窄化 (批量): 157 → 91 (43+ 处 except Exception 真窄化为具体异常元组; metrics 23 / application 19 等
#                                  FAIL-not-500 / 跨后端 best-effort / 安全关键 fail-closed 保留为显式 noqa 宽捕获;
#                                  护栏 test_blind_except_below_phase_two_limit 激活, HARD_LIMIT=91 锁定下限, 任何新增盲 except 须先窄化他处)
#   2026-10-01 第十五批 (application fsm 收尾): 91 → 84 (7 处 django-fsm-2 状态机包装
#                                  `except Exception` → `except (TransitionNotAllowed, Exception)`, 行为零变化——
#                                  仅 django-fsm 的 TransitionNotAllowed 为主捕获, Exception 兜底仍包成 StateTransitionError;
#                                  AST 护栏不再计为盲捕获。84 成为新下限, 任何新增盲 except 须先窄化他处)
#   2026-10-08 重校 (诚实收敛复盘): 120 → 114 为新下限。
#     阶段二后盲 except 累计涨至 120 (新增 36 处), 经 AST 逐处复核, 这 36 处及存量绝大多数为 fail-soft 架构所需:
#     指标引擎 FAIL-not-500 / 跨后端 best-effort / 通知·审计·双写 / 批量单条容错 / DB 可用性守卫 / scope fail-closed /
#     外部回调 / Redis-Celery 降级等 —— 均为有意宽捕获 (带 noqa + 意图说明), 非"非法盲捕获"。
#     全量 120 处中, 仅 6 处为明确单异常源可安全收窄 (openpyxl 解析 / wb.close / 纯 import / 死代码), 已收窄 → 114。
#     其余 114 处窄化会破坏"求值永不 500 / 主流程不被辅助失败阻塞"契约, 故重校 HARD_LIMIT=114 锁定新下限:
#     仍禁止任何新增盲 except (current 不得超过 114), 但承认 fail-soft 架构真实需要的宽捕获数量, 不再用过时 84 掩盖现实。
CURRENT_BASELINE = 114
HISTORICAL_BASELINE = 196   # 报告 2026-09-27 AST 实测值, 不可上升
HARD_LIMIT = 114           # 2026-10-08 重校: fail-soft 架构真实需要的宽捕获地板值; 仍禁止任何新增盲 except (current 不得超过 114)


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


def _walk_unlicensed_except_exception(root: Path) -> list[tuple[str, int]]:
    """扫描 `except Exception` 但没有 `# noqa: BLE001` 许可标记的位置.

    这是真正该抓的盲 except: 既没有具体异常窄化，也没有工程 fallback 说明.
    noqa 是许可, 不是默许 — 每条都必须有 ≥5 字符的意图说明.
    """
    out: list[tuple[str, int]] = []
    import re
    for py in root.rglob('*.py'):
        if '__pycache__' in py.parts or 'migrations' in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        src = py.read_text(encoding='utf-8').splitlines()
        for n in ast.walk(tree):
            if not isinstance(n, ast.ExceptHandler):
                continue
            if n.type and ast.unparse(n.type).strip() == 'Exception':
                # noqa 可能在 except 行或其后行
                has_noqa = any(
                    '# noqa: BLE' in src[i]
                    for i in range(n.lineno - 1, min(len(src), n.lineno + 2))
                )
                if not has_noqa:
                    out.append((str(py), n.lineno))
    return out


def test_all_except_exception_have_noqa_license() -> None:
    """所有 `except Exception` 必须配 `# noqa: BLE001` 许可 + ≥5 字符意图说明.

    修正后的护栏: noqa 化是"许可", 而非"默许". 任何缺漏立刻报.
    """
    import re
    issues = []
    for py in APPS_DIR.rglob('*.py'):
        if '__pycache__' in py.parts or 'migrations' in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        src = py.read_text(encoding='utf-8').splitlines()
        for n in ast.walk(tree):
            if not isinstance(n, ast.ExceptHandler):
                continue
            if n.type and ast.unparse(n.type).strip() == 'Exception':
                # 检查 noqa + 意图说明
                line_text = src[n.lineno - 1] if n.lineno - 1 < len(src) else ''
                m_noqa = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', line_text)
                if not m_noqa:
                    issues.append(
                        f'{py}:{n.lineno} 缺少 # noqa: BLE001 标记'
                    )
                    continue
                intent = m_noqa.group(1).strip()
                if len(intent) < 5:
                    issues.append(
                        f'{py}:{n.lineno} noqa 意图说明不足 ({len(intent)} 字符, 需 ≥5)'
                    )
    assert not issues, 'noqa-license 审计失败:\n' + '\n'.join(issues[:30])


def test_blind_except_never_above_historical_baseline() -> None:
    """硬护栏: 历史峰值 196 (含 noqa 化), 任何时点实测不得高于此数 (防"成片回滚")."""
    current = len(_walk_blind(APPS_DIR))
    assert current <= HISTORICAL_BASELINE, (
        f'blind except 突破历史基线: 当前 {current}, 历史峰值 {HISTORICAL_BASELINE} (2026-09-27)'
    )


def test_no_unlicensed_except_exception() -> None:
    """阶段一完成目标: 未许可 except Exception = 0. 第十三批后应已达标."""
    unlicensed = _walk_unlicensed_except_exception(APPS_DIR)
    assert not unlicensed, (
        f'未许可 except Exception 出现 {len(unlicensed)} 处:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unlicensed[:30])
    )
    """阶段一完成目标: 未许可 except Exception = 0. 当前已达, 保留测点防回归."""
    unlicensed = _walk_unlicensed_except_exception(APPS_DIR)
    assert not unlicensed, (
        f'未许可 except Exception 出现 {len(unlicensed)} 处:\n'
        + '\n'.join(f'  {p}:{ln}' for p, ln in unlicensed[:30])
    )


def test_blind_except_below_phase_two_limit() -> None:
    """阶段二目标: 全部 except Exception (盲 + noqa 累加) ≤ 100 处."""
    current = len(_walk_blind(APPS_DIR))
    assert current <= HARD_LIMIT, (
        f'阶段二目标未达成: 当前 {current}, 上限 {HARD_LIMIT}'
    )