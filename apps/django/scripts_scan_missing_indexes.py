"""D4 盘点：找出「被频繁按值过滤、却没有索引」的字段（status / stage / code 等）。

判定口径（静态可判）：
  1. 模型字段是 CharField（状态/阶段/编号类），且 **无** db_index 且 **无** unique
     （unique=True 在 MySQL 上自带唯一索引 → 视为已有索引）;
  2. 该字段名在全仓被 ``.filter(<field>=...)`` / ``.exclude(...)`` 按值过滤过
     （即"确实会被用到", 否则加索引纯属浪费写入性能）。

输出两类：
  - **建议加索引**：既没索引、又被按值过滤 → 加 db_index=True;
  - **无需处理**：已 unique（自带索引）或从未被按值过滤。

用法：python scripts_scan_missing_indexes.py
"""
from __future__ import annotations

import ast
import os
from pathlib import Path

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

from django.apps import apps as dj  # noqa: E402
from django.db import models  # noqa: E402

BASE = Path(__file__).resolve().parent / 'apps'

# 候选字段名（状态/阶段/编号类短名）
CANDIDATE_NAMES = {
    'status', 'state', 'stage', 'code', 'stage_code', 'process_code',
    'position_code', 'rule_code', 'role_code', 'resource_code', 'system_code',
    'current_stage', 'from_stage', 'to_stage', 'reason_code', 'tag_code',
}

# ── 1. 收集模型字段 ──
field_index: dict[tuple[str, str], object] = {}   # (app_label.Model, field) -> field
for m in dj.get_models():
    for f in m._meta.get_fields():
        if not getattr(f, 'concrete', False):
            continue
        if not isinstance(f, models.CharField):
            continue
        field_index[(f'{m._meta.app_label}.{m.__name__}', f.name)] = f

# ── 2. 扫全仓：哪些字段名被按值过滤 ──
filtered_names: set[str] = set()
for path in sorted(BASE.rglob('*.py')):
    if 'migrations' in path.parts:
        continue
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr not in ('filter', 'exclude', 'get'):
            continue
        for kw in node.keywords:
            if kw.arg:
                filtered_names.add(kw.arg)
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                filtered_names.add(arg.value)

# ── 3. 汇总 ──
need_index: list[tuple[str, str, str]] = []
already: list[tuple[str, str, str]] = []
unused: list[tuple[str, str, str]] = []

for (model_label, fname), field in sorted(field_index.items()):
    if fname not in CANDIDATE_NAMES:
        continue
    if field.db_index or field.unique:
        already.append((model_label, fname, 'unique' if field.unique else 'db_index'))
        continue
    # 字段名被按值过滤过？（kwarg 名或 filter 的第一个位置参数）
    if fname in filtered_names:
        need_index.append((model_label, fname, '被按值过滤'))
    else:
        unused.append((model_label, fname, '未见按值过滤'))

print('=' * 78)
print(f'建议加 db_index（无索引 + 确实按值过滤）：{len(need_index)} 处')
print('=' * 78)
for label, fname, why in need_index:
    print(f'  {label}.{fname}  ({why})')

print()
print('=' * 78)
print(f'已有索引（db_index / unique）：{len(already)} 处')
print('=' * 78)
for label, fname, why in already:
    print(f'  {label}.{fname}  ({why})')

print()
print('=' * 78)
print(f'未见按值过滤（加索引属浪费写入性能）：{len(unused)} 处')
print('=' * 78)
for label, fname, why in unused:
    print(f'  {label}.{fname}')
