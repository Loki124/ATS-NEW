"""静态守卫：禁止指向不存在模块的单点相对导入。

背景（2026-08-06 寇豆码）
========================
``apps/application/services/grab.py`` 在函数体内写了 ``from .models import
ApplicationHistory``。该文件位于 ``apps/application/services/`` 这个**二级子包**内，
而 ``services/`` 目录下并没有 ``models.py`` —— 单点 ``.models`` 会解析成
``apps.application.services.models``，即 ``ModuleNotFoundError``。正确写法是双点
``..models``（父包 ``apps/application/models.py``）。

这类错误极其隐蔽，原因有二：

1. **写在函数体内的延迟 import，模块加载期不会执行。** Django 启动、``manage.py
   check``、乃至整个 import 图遍历都不会碰到它，只有那个函数被真正调用的瞬间才炸。
2. 一旦对应端点因为别的原因不可达（本例中 ``GrabPoolViewSet`` 的路由被
   ``ApplicationViewSet`` 吃掉），这行代码可以从上线起一次都没执行过，
   覆盖率报告里就是一片 0%，无人察觉。

所以「服务能启动」「没有 import error」都无法证明这类 bug 不存在，必须做静态扫描。

实现要点
========
- 用 ``ast`` 解析而非正则：正则无法可靠区分 ``.``/``..`` 的层级，也拿不到准确行号，
  更会误伤字符串和注释里的同形文本。``ast.ImportFrom.level`` 是权威的点数来源。
- **不硬编码任何白名单。** 判据是"目标模块在磁盘上是否真的存在于该文件同级目录"，
  因此将来任何人新增子包都自动纳入检查，也绝不会误伤合法的单点导入
  （例如 ``apps/candidate/views.py`` 里的 ``from .models import Candidate`` —
  ``apps/candidate/models.py`` 确实存在，合法放行）。
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import List, NamedTuple

# tests/ 与 apps/ 同级，均位于 apps/django/ 下
DJANGO_ROOT = Path(__file__).resolve().parent.parent
APPS_ROOT = DJANGO_ROOT / 'apps'

# 这些目录不属于业务代码，或有自己的导入约定，跳过
SKIP_DIR_NAMES = {'migrations', 'tests', '__pycache__', 'management'}


class Violation(NamedTuple):
    """一处非法的单点相对导入。"""

    path: Path
    lineno: int
    module: str
    names: str

    def render(self) -> str:
        rel = self.path.relative_to(DJANGO_ROOT)
        return (
            f'  {rel}:{self.lineno}: from .{self.module} import {self.names}\n'
            f'      → 同级目录 {self.path.parent.relative_to(DJANGO_ROOT)}/ '
            f'下不存在 {self.module}.py 或 {self.module}/__init__.py；'
            f'若目标在父包，应写 from ..{self.module} import ...'
        )


def _iter_package_files() -> List[Path]:
    """遍历 apps/ 下所有**包目录**（含 __init__.py）里的 .py 文件。"""
    files: List[Path] = []
    for init_file in APPS_ROOT.rglob('__init__.py'):
        pkg_dir = init_file.parent
        # 路径中任一段命中跳过名单，则整个包跳过
        if SKIP_DIR_NAMES & set(pkg_dir.relative_to(APPS_ROOT).parts):
            continue
        for py_file in sorted(pkg_dir.glob('*.py')):
            files.append(py_file)
    return sorted(set(files))


def _module_exists_beside(pkg_dir: Path, module_head: str) -> bool:
    """判断 module_head 是否作为模块或子包真实存在于 pkg_dir 下。"""
    if (pkg_dir / f'{module_head}.py').is_file():
        return True
    if (pkg_dir / module_head / '__init__.py').is_file():
        return True
    return False


def _collect_violations() -> List[Violation]:
    """扫描全部包文件，收集指向不存在模块的单点相对导入。"""
    violations: List[Violation] = []

    for py_file in _iter_package_files():
        source = py_file.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(py_file))

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            # 只查单点相对导入；level==0 是绝对导入，level>=2 本就指向父包
            if node.level != 1:
                continue
            # `from . import x` 形式，node.module 为 None，不在本检查范围
            if node.module is None:
                continue

            # `from .sub.mod import x` 只需校验第一段能否落地
            module_head = node.module.split('.')[0]
            if _module_exists_beside(py_file.parent, module_head):
                continue

            violations.append(Violation(
                path=py_file,
                lineno=node.lineno,
                module=node.module,
                names=', '.join(alias.name for alias in node.names),
            ))

    return violations


def test_apps_root_is_discoverable() -> None:
    """前置条件：扫描根必须存在，否则下面的用例会静默通过（空扫描=没测）。"""
    assert APPS_ROOT.is_dir(), f'未找到 apps 根目录: {APPS_ROOT}'


def test_scan_actually_covers_files() -> None:
    """前置条件：必须真的扫到文件，防止 glob 写错导致"零违规"的假绿。"""
    files = _iter_package_files()
    assert len(files) > 50, (
        f'仅扫描到 {len(files)} 个文件，远低于预期，'
        f'说明遍历逻辑可能失效，本文件的守卫将形同虚设'
    )


def test_no_single_dot_relative_import_to_missing_module() -> None:
    """核心守卫：任何单点相对导入都必须能在同级目录落地。

    典型触发场景：在 ``apps/<app>/services/`` 等二级子包内，把本应写作
    ``..models`` 的父包导入误写成 ``.models``。
    """
    violations = _collect_violations()

    assert not violations, (
        f'\n发现 {len(violations)} 处指向不存在模块的单点相对导入'
        f'（延迟 import 时只有函数被调用才会炸，静态扫描是唯一防线）：\n'
        + '\n'.join(v.render() for v in violations)
    )


def test_detector_flags_a_known_bad_pattern(tmp_path: Path) -> None:
    """反向自检：确保检测器不是永远返回空的"哑巴守卫"。

    在临时目录里搭一个「子包内单点导入父包 models」的最小复现，
    断言检测逻辑能识别出来；同时断言同级真实存在的模块不被误报。
    """
    pkg = tmp_path / 'fakeapp'
    sub = pkg / 'services'
    sub.mkdir(parents=True)
    (pkg / '__init__.py').write_text('', encoding='utf-8')
    (pkg / 'models.py').write_text('X = 1\n', encoding='utf-8')
    (sub / '__init__.py').write_text('', encoding='utf-8')
    (sub / 'helper.py').write_text('', encoding='utf-8')

    # 坏例：services/ 下没有 models.py → 应判为不存在
    assert not _module_exists_beside(sub, 'models')
    # 好例：services/ 下确有 helper.py → 应判为存在，不得误报
    assert _module_exists_beside(sub, 'helper')
    # 好例：父包下确有 models.py（对应正确写法 ..models）
    assert _module_exists_beside(pkg, 'models')
