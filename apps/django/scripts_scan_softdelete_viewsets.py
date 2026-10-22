"""扫描器：找出「模型有 deleted_at、但 ViewSet 的 queryset 没过滤软删行」的漏网点。

与 ``scripts_scan_softdelete.py`` 方向相反：
  - ``scripts_scan_softdelete.py`` 查「对**没有** deleted_at 的模型做软删过滤」= 必炸（过滤无效）；
  - 本脚本查「对**有** deleted_at 的模型**没做**软删过滤」= 泄漏（软删行可见）。

为什么要它：
  2026-10-21 整改卡 D3 的第一步。此前全库约 73 个软删模型只有 7 个显式挂了
  ``SoftDeleteManager``，其余的默认 ``objects`` 不过滤 → 30 个 ViewSet 整类漏
  ``deleted_at__isnull=True`` → 软删行在列表接口可见（"删了还在列表里"）。

判定口径（静态可判）：
  1. ViewSet 的 queryset 指向的模型**有** ``deleted_at`` 字段；
  2. 且 queryset 表达式里**没有** ``deleted_at__isnull=True``；
  3. 且该模型的默认 manager **不是** ``SoftDeleteManager``（挂了就自动过滤，视为合规）。

用法：
    python scripts_scan_softdelete_viewsets.py            # 报告模式（不阻断）
    python scripts_scan_softdelete_viewsets.py --strict   # 发现即 exit 1（CI 硬门禁）

退出码：0 通过；1 有漏网点（仅 --strict）。
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

from django.apps import apps as dj  # noqa: E402

from apps.common.models import SoftDeleteManager  # noqa: E402

BASE = Path(__file__).resolve().parent / 'apps'

model_by_name: dict[str, list] = {}
for _m in dj.get_models():
    model_by_name.setdefault(_m.__name__, []).append(_m)


def has_sd(model) -> bool:
    return 'deleted_at' in {f.name for f in model._meta.get_fields()}


def default_manager_is_softdelete(model) -> bool:
    """模型默认 manager 是否就是 SoftDeleteManager（挂了就会自动过滤软删行）。"""
    manager = model._meta.default_manager
    return isinstance(manager, SoftDeleteManager)


def _model_names_from_expr(node: ast.AST) -> list[str]:
    """从 queryset 表达式里抠出模型名（`Foo.objects.all()` → ['Foo']）。"""
    names: list[str] = []
    cur = node
    while isinstance(cur, ast.Call):
        cur = cur.func
    while isinstance(cur, ast.Attribute):
        names.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        names.append(cur.id)
    names.reverse()
    # 形如 Foo.objects.xxx → chain[0] 是模型名
    if len(names) >= 2 and names[1] == 'objects':
        return [names[0]]
    return []


def _expr_filters_deleted(node: ast.AST) -> bool:
    """表达式里是否出现 deleted_at__isnull=True（大小写不敏感的 kwargs / 位置参数）。"""
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            for kw in n.keywords:
                if (kw.arg or '').startswith('deleted_at'):
                    return True
            for arg in n.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith('deleted_at'):
                        return True
    return False


findings: list[tuple[str, int, str, str, str]] = []   # (file, line, viewset, model, reason)
unresolved: list[tuple[str, int, str]] = []

for path in sorted(BASE.rglob('views.py')):
    rel = str(path.relative_to(BASE.parent))
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except SyntaxError:
        continue

    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        viewset_name = cls.name
        queryset_node = None
        queryset_line = 0
        has_get_queryset = False
        for item in cls.body:
            if isinstance(item, ast.Assign):
                for tgt in item.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == 'queryset':
                        queryset_node = item.value
                        queryset_line = item.lineno
            if isinstance(item, ast.FunctionDef) and item.name == 'get_queryset':
                has_get_queryset = True

        if queryset_node is None:
            if has_get_queryset:
                unresolved.append((rel, cls.lineno, f'{viewset_name}（覆盖 get_queryset，需人工确认）'))
            continue

        model_names = _model_names_from_expr(queryset_node)
        if not model_names:
            unresolved.append((rel, queryset_line, f'{viewset_name}.queryset 表达式无法静态解析'))
            continue

        for mname in model_names:
            candidates = model_by_name.get(mname, [])
            if not candidates:
                unresolved.append((rel, queryset_line, f'{viewset_name} → 未知模型 {mname}'))
                continue
            for model in candidates:
                if not has_sd(model):
                    continue                      # 非软删模型, 不归本脚本管
                if default_manager_is_softdelete(model):
                    continue                      # 默认 manager 已过滤 → 合规
                if _expr_filters_deleted(queryset_node):
                    continue                      # 表达式自己过滤了 → 合规
                findings.append((
                    rel, queryset_line, viewset_name,
                    f'{model._meta.app_label}.{model.__name__}',
                    '模型有 deleted_at，但 queryset 未过滤且默认 manager 不是 SoftDeleteManager',
                ))

print('=' * 78)
print(f'软删泄漏 ViewSet（模型有 deleted_at 却不过滤）：{len(findings)} 处')
print('=' * 78)
for rel, line, viewset, model, reason in findings:
    print(f'{rel}:{line}  {viewset} → {model}\n    {reason}')

print()
print('=' * 78)
print(f'需人工确认：{len(unresolved)} 处')
print('=' * 78)
for rel, line, text in unresolved:
    print(f'{rel}:{line}  {text}')

if '--strict' in sys.argv[1:] and findings:
    print('\n[strict] 存在软删泄漏 ViewSet, 退出 1')
    sys.exit(1)

sys.exit(0)
