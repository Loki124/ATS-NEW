"""扫描器：找出**模块级** ``pytest.mark.django_db(transaction=True)`` 的测试文件。

为什么禁它（2026-10-21 整跑 flaky 根因治理）：

``django_db(transaction=True)`` 的用例在 teardown 会 ``flush`` **整库**，
连同**已提交**的种子（``permission_resources`` / ``role_permission`` /
``recruitment_stages`` / ``dynamic_fields`` / 核心指标）一起清掉。
配 ``--reuse-db`` 时下次运行不再重跑已应用的迁移 → 种子永久缺失
→ **字典序在它之后**的用例批量拿到 403 / ``DoesNotExist``。

把它写在**模块级**（``pytestmark = pytest.mark.django_db(transaction=True)``）
会让该文件里的**每一个**用例都触发一次全库 flush —— 污染面是「整个文件」，
而不是「确有用例的那几个」。

判定口径（AST 静态可判，**不执行**测试）：
  1. 顶层赋值语句 ``pytestmark = ...``；
  2. 其值（直接、或在 list/tuple 里）包含 ``pytest.mark.django_db(transaction=True)``。

方法级装饰器（``@pytest.mark.django_db(transaction=True)``）**不算违规** ——
它只影响那一个用例，flush 面可控。

用法：
    python scripts_scan_module_level_transaction.py            # 报告模式（不阻断）
    python scripts_scan_module_level_transaction.py --strict   # 发现即 exit 1（CI 硬门禁）

退出码：0 通过；1 有违规（仅 --strict）。

已登记的历史例外（``KNOWN_EXCEPTIONS``）—— 改动前必须先读那里的理由：
这些文件**确实**需要模块级事务（用例依赖真实提交 / ``select_for_update`` 语义），
已逐一评估过代价，保留并登记；**新增**模块级用法一律拦下。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

# 测试文件搜索根（与 pytest.ini 的 testpaths = tests apps 对齐）
SEARCH_ROOTS = ('tests', 'apps')

# 已登记的历史例外：relpath → 理由
KNOWN_EXCEPTIONS: dict[str, str] = {
    'apps/campus_control/tests/test_rule_config.py': (
        '该文件大量依赖 save() 内的 select_for_update 自动补号，'
        '在 savepoint 模式下会逃逸回滚 → 编号断言不确定；已确认保留，'
        '其 flush 造成的种子缺失由 tests/fixtures_common.py 的补种兜底。'
    ),
}


def _iter_test_files():
    for root in SEARCH_ROOTS:
        base = BASE / root
        if not base.exists():
            continue
        for path in base.rglob('test_*.py'):
            if path.is_file():
                yield path


def _relative(path: Path) -> str:
    """相对 BASE 的路径；不在 BASE 下时（如自测用的临时目录）退回绝对路径。"""
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def _is_transactional_db_marker(node: ast.AST) -> bool:
    """判断一个表达式是否包含 ``pytest.mark.django_db(transaction=True)``。

    兼容三种写法：
      pytest.mark.django_db(transaction=True)
      pytest.mark.django_db(transaction=True, reset_sequences=False)
      [pytest.mark.django_db(transaction=True), pytest.mark.slow]
    """
    if isinstance(node, ast.Call):
        # pytest.mark.django_db(...)
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == 'django_db'
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == 'mark'
        ):
            for kw in node.keywords:
                if kw.arg == 'transaction' and _is_true(kw.value):
                    return True
            # 位置参数形式: django_db(True)
            if node.args and _is_true(node.args[0]):
                return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return any(_is_transactional_db_marker(elt) for elt in node.elts)
    return False


def _is_true(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def find_module_level_transactional_markers() -> list[tuple[str, int, str]]:
    """返回 [(相对路径, 行号, 原因)]，只含**不在**已登记例外里的违规。"""
    findings: list[tuple[str, int, str]] = []
    for path in _iter_test_files():
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in tree.body:  # 只看顶层
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            if 'pytestmark' not in names:
                continue
            value = node.value
            if value is None or not _is_transactional_db_marker(value):
                continue
            rel = _relative(path)
            if rel in KNOWN_EXCEPTIONS:
                continue
            findings.append((
                rel,
                node.lineno,
                '模块级 pytestmark 含 django_db(transaction=True)'
                ' → 该文件每个用例 teardown 都会 flush 整库，'
                '抹掉已提交种子 → 后续用例批量 403。'
                '请改成方法级装饰器；确需模块级时先在 KNOWN_EXCEPTIONS 登记理由。',
            ))
    return findings


def main() -> int:
    findings = find_module_level_transactional_markers()

    print('=' * 78)
    print(f'模块级 django_db(transaction=True) 违规：{len(findings)} 处')
    print('=' * 78)
    for rel, line, reason in findings:
        print(f'{rel}:{line}\n    {reason}\n')

    if KNOWN_EXCEPTIONS:
        print('-' * 78)
        print(f'已登记的历史例外（{len(KNOWN_EXCEPTIONS)} 处，均已评估过代价）：')
        for rel, reason in KNOWN_EXCEPTIONS.items():
            print(f'  · {rel}\n      {reason}')
        print('-' * 78)

    if '--strict' in sys.argv[1:] and findings:
        print('\n[strict] 存在模块级 django_db(transaction=True), 退出 1')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
