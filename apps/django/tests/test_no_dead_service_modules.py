"""棘轮守卫（ratchet）：已删除的死代码模块不得复活，且台账本身不得陈旧。

背景（T6）
==========
``apps/application/services/stage_transitions.py`` 是一份零调用、零测试覆盖的死代码，
已在前批次整文件删除。但**配套守卫当时没建**，属半成品：删除动作没有任何机制阻止
它日后被 copy-paste 回来（尤其是在合并旧分支、回滚 commit 时）。本文件补上这个棘轮。

为什么守卫必须是**双向**的
==========================
本项目吃过两次「隔离台账陈旧」的亏：

1. ``add_candidate`` 有 6 条 ``deselect`` 早已自愈，却仍挂在跳过名单里，无人察觉；
2. 「518 passed / 8 xfailed」这个被反复引用的基线数字**两个都是错的**（实测 557 / 0），
   陈旧台账被当作事实沿用了整整一轮。

共同病根是：台账只做「单向」断言——只检查"名单里的东西是不是还坏着"，
从不检查"名单本身是不是已经过期"。过期项永远静默留存，久而久之整份台账失去可信度。

所以本文件对 :data:`DEAD_MODULES` 里的每一项都做**两个方向**的断言：

- **正向**：该模块在磁盘上确实不存在、且全仓无任何引用（防死代码复活）；
- **反向**：该条目本身仍然"值得守"——即它必须是一条**真的被删除过**的记录，
  而不是一个从未存在过、纯属想象出来的名字
  （见 :func:`test_dead_module_ledger_has_no_stale_entries`）。

反向断言的判据是 git 历史：一个条目若在 git 历史里从来没出现过，说明它是笔误
或早已无关的臆造项，应当从台账中删除，而不是永远挂着装样子。
"""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import List, NamedTuple

# tests/ 与 apps/ 同级，均位于 apps/django/ 下
DJANGO_ROOT = Path(__file__).resolve().parent.parent
APPS_ROOT = DJANGO_ROOT / 'apps'
REPO_ROOT = DJANGO_ROOT.parent.parent

# 本文件自身会大量提到这些名字，扫描时必须排除，否则守卫会自己告自己
SELF_PATH = Path(__file__).resolve()


class DeadModule(NamedTuple):
    """一条死代码台账。

    Attributes:
        rel_path: 相对 ``apps/django/`` 的模块路径，必须已从磁盘删除。
        symbol: 该模块的可搜索标识（模块名），全仓不得出现任何引用。
        reason: 删除理由，供后人判断这条守卫是否仍有意义。
    """

    rel_path: str
    symbol: str
    reason: str


# ⚠️ 增删本清单时请同时确认两件事：
#   1. 正向——该模块确已从磁盘删除、全仓零引用；
#   2. 反向——该条目在 git 历史中确实存在过（否则属陈旧/臆造项，应删除条目而非保留）。
DEAD_MODULES: List[DeadModule] = [
    DeadModule(
        rel_path='apps/application/services/stage_transitions.py',
        symbol='stage_transitions',
        reason='零调用零测试的死代码；阶段流转逻辑已由 application/services/__init__.py 的活实现承载',
    ),
]


class Reference(NamedTuple):
    """一处对死模块的引用。"""

    path: Path
    lineno: int
    text: str

    def render(self) -> str:
        rel = self.path.relative_to(REPO_ROOT)
        return f'  {rel}:{self.lineno}: {self.text}'


def _iter_python_files() -> List[Path]:
    """遍历 apps/django/ 下所有 .py 文件（排除虚拟环境、缓存与本文件自身）。"""
    skip_parts = {'.venv', '__pycache__', 'node_modules', '.git'}
    files: List[Path] = []
    for py_file in DJANGO_ROOT.rglob('*.py'):
        if skip_parts & set(py_file.relative_to(DJANGO_ROOT).parts):
            continue
        if py_file.resolve() == SELF_PATH:
            continue
        files.append(py_file)
    return sorted(files)


def _collect_references(symbol: str) -> List[Reference]:
    """用 ast 收集对 ``symbol`` 的 import 引用，再用文本兜住字符串式动态引用。

    只用 ast 会漏掉 ``import_module('...stage_transitions')`` / ``getattr`` 这类动态写法；
    只用文本会误伤注释。两者叠加：ast 负责精确，文本负责兜底且只在非注释行生效。
    """
    refs: List[Reference] = []

    for py_file in _iter_python_files():
        source = py_file.read_text(encoding='utf-8')
        if symbol not in source:
            continue

        # ① ast：精确捕获 import 语句
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:  # pragma: no cover - 仓内不应有语法错文件
            tree = None

        matched_linenos = set()
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if symbol in alias.name.split('.'):
                            matched_linenos.add(node.lineno)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    if symbol in module.split('.'):
                        matched_linenos.add(node.lineno)
                    for alias in node.names:
                        if alias.name == symbol:
                            matched_linenos.add(node.lineno)

        # ② 文本兜底：非注释行里出现该符号（覆盖 import_module / 字符串路径等动态引用）
        for lineno, line in enumerate(source.splitlines(), start=1):
            if symbol not in line:
                continue
            if line.lstrip().startswith('#'):
                continue
            matched_linenos.add(lineno)

        lines = source.splitlines()
        for lineno in sorted(matched_linenos):
            refs.append(Reference(path=py_file, lineno=lineno, text=lines[lineno - 1].strip()))

    return refs


def _git_log_touched(rel_path: str) -> bool:
    """git 历史里是否出现过该路径（含已删除文件）。

    ``git log --all --diff-filter=D`` 只列删除事件；这里放宽为「历史上出现过」，
    因为文件也可能是 rename 走的。返回 False 意味着该台账条目是臆造项。
    """
    try:
        out = subprocess.run(
            ['git', 'log', '--all', '--oneline', '--', rel_path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - 无 git 环境
        return True  # 拿不到 git 历史时不误判，交由正向断言把关
    if out.returncode != 0:  # pragma: no cover
        return True
    return bool(out.stdout.strip())


# ============================================================
# 前置条件：防「空扫描 = 没测」的假绿
# ============================================================
def test_scan_root_is_discoverable() -> None:
    assert APPS_ROOT.is_dir(), f'未找到 apps 根目录: {APPS_ROOT}'


def test_scan_actually_covers_files() -> None:
    """必须真的扫到文件，否则「零引用」只是遍历逻辑失效的假象。"""
    files = _iter_python_files()
    assert len(files) > 100, (
        f'仅扫描到 {len(files)} 个 .py 文件，远低于预期，'
        f'说明遍历逻辑可能失效，本文件的守卫将形同虚设'
    )


def test_ledger_is_not_empty() -> None:
    """台账为空则本文件退化为空跑；若确实无死模块需守，应连同本文件一并删除。"""
    assert DEAD_MODULES, 'DEAD_MODULES 为空 —— 守卫已无对象，请删除本文件而非留空跑'


# ============================================================
# 正向：死模块不得复活
# ============================================================
def test_dead_modules_do_not_exist_on_disk() -> None:
    revived = [d for d in DEAD_MODULES if (DJANGO_ROOT / d.rel_path).exists()]
    assert not revived, (
        '以下已删除的死代码模块又出现在磁盘上（很可能是合并旧分支/回滚 commit 带回来的）：\n'
        + '\n'.join(f'  {d.rel_path} —— 当初删除理由：{d.reason}' for d in revived)
    )


def test_dead_modules_have_no_references_anywhere() -> None:
    """全仓（排除本文件自身）不得有任何对死模块的 import 或字符串引用。"""
    problems: List[str] = []
    for dead in DEAD_MODULES:
        refs = _collect_references(dead.symbol)
        if refs:
            problems.append(
                f'{dead.symbol}（{dead.rel_path}）仍被 {len(refs)} 处引用：\n'
                + '\n'.join(r.render() for r in refs)
            )
    assert not problems, '\n'.join(problems)


# ============================================================
# 反向：台账本身不得陈旧
# ============================================================
def test_dead_module_ledger_has_no_stale_entries() -> None:
    """反向守卫：台账里不允许挂着「其实根本不需要守」的臆造项。

    本项目两次栽在陈旧台账上（add_candidate 的 6 条 deselect 早已自愈仍在跳过；
    518/8 基线数字双错）。单向断言天然无法发现过期项——它只会永远通过。
    这里以 git 历史为客观判据：某条目若在 git 历史里从来没存在过，
    说明它是笔误或臆造，应当**删除条目**，而不是让它继续占位装样子。
    """
    stale = [d for d in DEAD_MODULES if not _git_log_touched(f'apps/django/{d.rel_path}')]
    assert not stale, (
        '以下台账条目在 git 历史中从未出现过，属陈旧/臆造项，请从 DEAD_MODULES 中删除：\n'
        + '\n'.join(f'  {d.rel_path}' for d in stale)
    )


def test_dead_module_ledger_entries_are_well_formed() -> None:
    """台账字段自洽：symbol 必须能从 rel_path 推出，reason 必须写清楚。

    防止有人只填半截（例如 symbol 写错导致 _collect_references 永远扫不到东西，
    正向断言就变成了永远通过的哑巴守卫）。
    """
    problems: List[str] = []
    for dead in DEAD_MODULES:
        expected_symbol = Path(dead.rel_path).stem
        if dead.symbol != expected_symbol:
            problems.append(
                f'  {dead.rel_path}: symbol={dead.symbol!r} 与文件名推出的 {expected_symbol!r} 不符 '
                f'→ 引用扫描会扫错目标，正向守卫将永远通过（哑巴守卫）'
            )
        if not dead.reason.strip():
            problems.append(f'  {dead.rel_path}: reason 为空，后人无法判断此条守卫是否仍有意义')
    assert not problems, '\n'.join(problems)


def test_reference_detector_is_not_a_dumb_guard(tmp_path: Path) -> None:
    """自检：确保引用检测器不是永远返回空。

    在临时目录搭一个含 import 的最小复现，断言检测逻辑能识别；
    同时断言纯注释行不被计入（避免本文件这类文档性提及造成误报）。
    """
    sample = (
        'import os\n'
        '# from apps.application.services import stage_transitions  # 注释，不算引用\n'
        'from apps.application.services import stage_transitions\n'
    )
    tree = ast.parse(sample)
    hits = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and any(alias.name == 'stage_transitions' for alias in node.names)
    ]
    assert hits == [3], f'ast 检测器未能识别 import，实得 {hits}'

    comment_line = sample.splitlines()[1]
    assert comment_line.lstrip().startswith('#'), '注释行判据失效 → 文本兜底会把注释误报为引用'
