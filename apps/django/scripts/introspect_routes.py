"""路由内省脚本 — 打印每个 api/v1 URL 实际由哪个 ViewSet/View 服务.

用途: 验证 DRF DefaultRouter 上多个 ViewSet 同时 register(r'') 造成的
"路由掩盖" (后注册的 list/detail 路由被先注册的吃掉) 是否已修复.

用法:
    python scripts/introspect_routes.py                # 打印全部 api/v1 路由
    python scripts/introspect_routes.py channels       # 只打印含 'channels' 的路由
    python scripts/introspect_routes.py --resolve      # 额外做 resolve() 实测

输出格式:
    <HTTP 方法映射>  <完整 URL 正则路径>  ->  <ViewSet 类名>
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Iterator, Tuple

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.urls import get_resolver, resolve  # noqa: E402
from django.urls.resolvers import URLPattern, URLResolver  # noqa: E402


def _pattern_str(pattern: Any) -> str:
    """把 URLPattern/URLResolver 的 pattern 还原成可读字符串."""
    raw = str(pattern.pattern)
    # RegexPattern 的 str() 已经是正则; RoutePattern 是 '<int:pk>/' 这种
    return raw


def _view_name(callback: Any) -> str:
    """从 callback 反查真实的 View / ViewSet 类名."""
    cls = getattr(callback, 'cls', None)
    if cls is not None:
        return cls.__name__
    view_class = getattr(callback, 'view_class', None)
    if view_class is not None:
        return view_class.__name__
    return getattr(callback, '__name__', repr(callback))


def _actions(callback: Any) -> str:
    """ViewSet 的 method -> action 映射 (initkwargs['actions'])."""
    initkwargs = getattr(callback, 'initkwargs', None) or {}
    actions = getattr(callback, 'actions', None) or initkwargs.get('actions')
    if not actions:
        return ''
    return ','.join(f'{m.upper()}={a}' for m, a in sorted(actions.items()))


def walk(patterns: Any, prefix: str = '') -> Iterator[Tuple[str, str, str, str]]:
    """深度优先遍历 URLconf, yield (完整路径, ViewSet 名, actions, url_name)."""
    for entry in patterns:
        current = prefix + _pattern_str(entry)
        if isinstance(entry, URLResolver):
            yield from walk(entry.url_patterns, current)
        elif isinstance(entry, URLPattern):
            yield (current, _view_name(entry.callback), _actions(entry.callback),
                   entry.name or '')


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    do_resolve = '--resolve' in sys.argv
    keyword = args[0] if args else ''

    resolver = get_resolver()
    rows = list(walk(resolver.url_patterns))

    printed = 0
    for path, view, actions, name in rows:
        if not path.startswith('^api/v1/') and 'api/v1/' not in path:
            continue
        if keyword and keyword not in path:
            continue
        # 跳过 format-suffix 变体, 减少噪音
        if r'\.(?P<format>' in path:
            continue
        print(f'{path:<78} -> {view:<32} [{actions}] name={name}')
        printed += 1

    print(f'\n共 {printed} 条 (关键字={keyword!r})')

    if do_resolve:
        print('\n=== resolve() 实测 ===')
        probes = [
            '/api/v1/channels/', '/api/v1/channels/1/',
            '/api/v1/channels/costs/', '/api/v1/channels/costs/1/',
            '/api/v1/notifications/', '/api/v1/notifications/1/',
            '/api/v1/notifications/logs/', '/api/v1/notifications/logs/1/',
            '/api/v1/notifications/logs/unread/',
            '/api/v1/automation-rules/', '/api/v1/automation-rules/1/',
            '/api/v1/automation-rules/1/logs/',
            '/api/v1/automation-rules/logs/', '/api/v1/automation-rules/logs/1/',
            '/api/v1/analytics/', '/api/v1/analytics/1/',
            '/api/v1/analytics/exports/', '/api/v1/analytics/exports/1/',
            '/api/v1/analytics/exports/dashboard-summary/',
            '/api/v1/integrations/', '/api/v1/integrations/1/',
            '/api/v1/integrations/1/test/',
            '/api/v1/integrations/sync-logs/', '/api/v1/integrations/sync-logs/1/',
            '/api/v1/talent-pool/', '/api/v1/talent-pool/1/',
            '/api/v1/talent-pool/1/activate/',
            '/api/v1/talent-pool/tags/', '/api/v1/talent-pool/tags/1/',
            '/api/v1/interviews/', '/api/v1/interviews/1/',
            '/api/v1/interviews/evaluations/', '/api/v1/interviews/evaluations/1/',
            '/api/v1/applications/', '/api/v1/applications/1/',
            '/api/v1/applications/1/grab/', '/api/v1/applications/reapply-suggest/',
            '/api/v1/grab-pool/', '/api/v1/grab-pool/summary/',
            '/api/v1/grab-pool/reassign/',
            '/api/v1/invitations/', '/api/v1/invitations/1/',
            '/api/v1/invitations/claimable/',
        ]
        for probe in probes:
            try:
                match = resolve(probe)
                print(f'{probe:<52} -> {_view_name(match.func):<30} '
                      f'[{_actions(match.func)}]')
            except Exception as exc:  # noqa: BLE001
                # Resolver404 的 tried 列表极长, 只保留异常类型
                print(f'{probe:<52} -> !! {type(exc).__name__} (无路由匹配)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
