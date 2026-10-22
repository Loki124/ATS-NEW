"""一次性审计脚本：找出所有对「没有 deleted_at 字段的模型」做软删过滤的调用点。

方法：AST 扫描出所有形如 ``<recv>.filter/exclude/get(... deleted_at ...)`` 的调用，
再用 Django 运行时元数据解析 <recv> 指向的模型：
  - ``Foo.objects``            → 模型 Foo
  - ``<任意>.<accessor>``      → 所有把 <accessor> 作为反向访问名/related_name 的模型
只要解析出的候选模型里存在「无 deleted_at」的，就报出来。

用法：
    python scripts_scan_softdelete.py            # 报告模式（不阻断，CI 当前用法）
    python scripts_scan_softdelete.py --strict   # 发现即 exit 1（存量清零后翻硬门禁）

2026-10-21 卡 B6：修掉一处**死循环**（`base.func` 不是 Attribute 时 `base = base`
自赋值 → while 永真 → 脚本挂死不退出，实测挂 18 分钟无输出）；并在 CI 接入本脚本。
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

BASE = Path(__file__).resolve().parent / 'apps'

# 模型名 → 是否有 deleted_at
model_by_name: dict[str, list] = {}
accessor_owner: dict[str, list] = {}

for m in dj.get_models():
    model_by_name.setdefault(m.__name__, []).append(m)
    # m.<accessor> 返回的是 rel.related_model 的 queryset，不是 m 自己
    for rel in m._meta.related_objects:
        accessor_owner.setdefault(rel.get_accessor_name(), []).append(rel.related_model)
    # 只看**正向**关系字段的 related_name（get_fields() 会把反向关系也混进来，
    # 反向关系对象同样带 related_name 属性，误纳入会把归属判反）
    for f in m._meta.get_fields():
        if not getattr(f, 'is_relation', False) or getattr(f, 'auto_created', False):
            continue
        rn = getattr(f, 'related_name', None)
        if rn and not rn.endswith('+'):
            # 对方模型上通过 rn 访问回来的是 m 的 queryset
            accessor_owner.setdefault(rn, []).append(m)


def has_sd(model) -> bool:
    return 'deleted_at' in {f.name for f in model._meta.get_fields()}


def recv_text(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return '<?>'


findings: list[tuple[str, int, str, str]] = []
unresolved: list[tuple[str, int, str]] = []

for path in sorted(BASE.rglob('*.py')):
    parts = set(path.parts)
    if 'migrations' in parts or 'tests' in parts:
        continue
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except SyntaxError:
        continue

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr not in ('filter', 'exclude', 'get'):
            continue
        kwnames = [kw.arg or '' for kw in node.keywords]
        if not any(k.startswith('deleted_at') for k in kwnames):
            continue

        recv = func.value
        text = recv_text(recv)
        rel = str(path.relative_to(BASE.parent))
        line = node.lineno

        candidates = []
        # Foo.objects / Foo.objects.select_related(...) 形态
        base = recv
        while isinstance(base, ast.Call):
            # 🔴 2026-10-21 卡 B6：这里原先写成
            #     `base = base.func.value if isinstance(base.func, ast.Attribute) else base`
            #    —— 当 base.func **不是** Attribute（如 `get_foo(...).filter(...)`，
            #    func 是 Name）时 base 被赋成它自己 → while 永远为真 → **死循环**，
            #    脚本永远跑不完（实测挂 18 分钟无输出，CI 里等于挂死）。
            #    修正：func 不是 Attribute 时无法再往里剥，置 None 并退出循环，
            #    该调用点归入「未能静态解析」列表（人工确认），不再挂死。
            if isinstance(base.func, ast.Attribute):
                base = base.func.value
            else:
                base = None
                break
        chain = []
        cur = base
        while isinstance(cur, ast.Attribute):
            chain.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            chain.append(cur.id)
        chain.reverse()

        if len(chain) >= 2 and chain[1] == 'objects' and chain[0] in model_by_name:
            candidates = model_by_name[chain[0]]
        elif chain and chain[-1] in accessor_owner:
            candidates = accessor_owner[chain[-1]]

        if not candidates:
            unresolved.append((rel, line, text))
            continue

        bad = [c for c in candidates if not has_sd(c)]
        if bad:
            findings.append((
                rel, line, text,
                ','.join(f'{b._meta.app_label}.{b.__name__}' for b in bad),
            ))

print('=' * 78)
print(f'必炸调用点（模型无 deleted_at 字段）：{len(findings)} 处')
print('=' * 78)
for rel, line, text, models in findings:
    print(f'{rel}:{line}\n    recv = {text}\n    模型 = {models}')

print()
print('=' * 78)
print(f'未能静态解析的调用点（需人工确认）：{len(unresolved)} 处')
print('=' * 78)
for rel, line, text in unresolved:
    print(f'{rel}:{line}  recv = {text}')

# 默认报告模式不阻断；--strict 才把不合规变成失败（与 scripts_scan_todo.py 同款口径：
# 存量清零后在 CI 加 --strict 即翻硬门禁）
if '--strict' in sys.argv[1:] and findings:
    print('\n[strict] 存在对无 deleted_at 模型的软删过滤调用点, 退出 1')
    sys.exit(1)

sys.exit(0)
