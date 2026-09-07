"""ATS-NEW API 运行时内省脚本（只读，不修改任何业务代码）

用途：遍历 django.urls.get_resolver() 拿到**真实注册**的所有端点，
提取 view 类的 permission_classes / throttle_classes / pagination /
filter_backends / queryset 优化，输出 CSV + 汇总统计。

运行：
    cd apps/django && DJANGO_SETTINGS_MODULE=config.settings.test \
        ../../docs/audit/introspect_api.py        # 需要 venv python
    .venv/bin/python ../../docs/audit/introspect_api.py

产出：docs/audit/api_endpoints.csv
"""
import csv
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../../apps/django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/../../apps/django')
django.setup()

from django.urls import get_resolver  # noqa: E402
from rest_framework.views import APIView  # noqa: E402

OUT = os.path.abspath(
    os.path.dirname(os.path.abspath(__file__)) + '/api_endpoints.csv')


def collect(patterns, prefix=''):
    """递归展开 url patterns，产出 (path, view_class_or_func)"""
    out = []
    for p in patterns:
        if hasattr(p, 'url_patterns'):
            out.extend(collect(p.url_patterns, prefix + str(p.pattern)))
        elif hasattr(p, 'callback'):
            out.append((prefix + str(p.pattern), p.callback, str(p.pattern)))
    return out


def view_class_of(callback):
    cls = getattr(callback, 'cls', None)
    if cls is not None:
        return cls
    if hasattr(callback, 'view_class'):
        return callback.view_class
    return None


def name_of(cls, callback):
    if cls is not None:
        mod = getattr(cls, '__module__', '?')
        return f'{mod}.{cls.__name__}'
    return f'{getattr(callback, "__module__", "?")}.{getattr(callback, "__name__", "?")}'


def join_classes(seq):
    if seq is None:
        return ''
    return ','.join(
        c.__name__ if isinstance(c, type) else str(c) for c in seq)


def loc_of(obj):
    try:
        import inspect
        f = obj
        if isinstance(obj, type):
            f = getattr(obj, '__init__', None)
        if f is None:
            return ''
        src, lineno = inspect.getsourcelines(f)
        return f'{inspect.getsourcefile(f)}:{lineno}'
    except Exception:
        return ''


rows = []
resolver = get_resolver()
all_patterns = collect(resolver.url_patterns)

for full, cb, pat in all_patterns:
    cls = view_class_of(cb)
    vname = name_of(cls, cb)
    # 只看 API 相关（排除 admin / static / spectacular docs）
    if vname.startswith('django.contrib.admin') or vname.startswith(
            'django.views.static'):
        continue
    row = {
        'path': full,
        'view': vname,
        'kind': 'DRF' if (cls is not None and issubclass(cls, APIView)) else
                ('DRF-fn' if (cls is None and hasattr(cb, 'cls')) else 'Django'),
        'permission_classes': '',
        'authentication_classes': '',
        'throttle_classes': '',
        'pagination_class': '',
        'filter_backends': '',
        'queryset_opt': '',
        'serializer': '',
        'http_methods': '',
        'loc': '',
    }
    if cls is not None:
        row['loc'] = loc_of(cls)
        if issubclass(cls, APIView):
            row['permission_classes'] = join_classes(
                getattr(cls, 'permission_classes', None))
            row['authentication_classes'] = join_classes(
                getattr(cls, 'authentication_classes', None))
            row['throttle_classes'] = join_classes(
                getattr(cls, 'throttle_classes', None))
            row['pagination_class'] = join_classes(
                [getattr(cls, 'pagination_class', None)]
            ) if getattr(cls, 'pagination_class', None) else ''
            row['filter_backends'] = join_classes(
                getattr(cls, 'filter_backends', None))
            row['serializer'] = getattr(
                getattr(cls, 'serializer_class', None), '__name__', '')
            row['http_methods'] = ','.join(sorted(
                m for m in getattr(cls, 'http_method_names', [])
                if hasattr(cls, m)
            ))
            # queryset 优化探测（源码级）
            try:
                import inspect
                loc = loc_of(cls)
                if loc and ':' in loc:
                    fp = loc.rsplit(':', 1)[0]
                    with open(fp, encoding='utf-8', errors='ignore') as fh:
                        src = fh.read()
                    opts = []
                    for token in ('select_related', 'prefetch_related',
                                  'only(', 'defer('):
                        if token in src:
                            opts.append(token.rstrip('('))
                    row['queryset_opt'] = ','.join(opts)
            except Exception:
                pass
    else:
        row['loc'] = loc_of(cb)
    rows.append(row)

with open(OUT, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# ---------- 汇总 ----------
total = len(rows)
drf = [r for r in rows if r['kind'] == 'DRF']
noop = [r for r in drf if not r['permission_classes']]
only_auth = [r for r in drf
             if r['permission_classes'] == 'IsAuthenticated']
allow_any = [r for r in drf if 'AllowAny' in r['permission_classes']]
no_throttle = [r for r in drf if not r['throttle_classes']]
listable = [r for r in drf
            if r['http_methods'] and 'get' in r['http_methods']]
no_pagination = [r for r in listable if not r['pagination_class']]

print(f'OUT={OUT}')
print(f'总 URL 模式（不含 admin/static）: {total}')
print(f'DRF 类视图端点: {len(drf)}')
print(f'  ├─ permission_classes 空(走 DEFAULT 全局默认): {len(noop)}')
print(f'  ├─ 仅 IsAuthenticated (裸认证、无对象级权限): {len(only_auth)}')
print(f'  ├─ 含 AllowAny: {len(allow_any)}')
print(f'  ├─ 无 throttle_classes: {len(no_throttle)}')
print(f'  └─ 支持 GET(list) 且未声明 pagination_class: {len(no_pagination)}')
print()
print('--- 仅 IsAuthenticated 的端点（前 60 条）---')
for r in only_auth[:60]:
    print(f"  {r['path']:70s} {r['view']}")
print()
print('--- 含 AllowAny 的端点 ---')
for r in allow_any:
    print(f"  {r['path']:70s} {r['view']}  perms={r['permission_classes']}")
