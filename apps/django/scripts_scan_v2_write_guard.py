"""扫描所有挂在 V2Permission 下的端点, 列出「写操作未被任何权限码覆盖」的视图.

用法:
    python manage.py shell < scripts_scan_v2_write_guard.py
    或:  DJANGO_SETTINGS_MODULE=config.settings.test python scripts_scan_v2_write_guard.py

背景: V2Permission 修复后, 未声明 permission_required / permission_required_map 的
**写操作**会被拒绝。本脚本在开启严格守卫前把遗漏清单一次性列全, 避免逐个试错。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')

import django  # noqa: E402
django.setup()

from django.urls import get_resolver  # noqa: E402
from rest_framework.permissions import SAFE_METHODS  # noqa: E402

from apps.core.permissions_v2 import V2Permission  # noqa: E402


def iter_views(resolver, prefix=''):
    for p in resolver.url_patterns:
        if hasattr(p, 'url_patterns'):
            yield from iter_views(p, prefix + str(p.pattern))
        else:
            yield prefix + str(p.pattern), p.callback


def view_class(callback):
    cls = getattr(callback, 'cls', None)
    if cls is None:
        cls = getattr(callback, 'view_class', None)
    return cls


def write_actions(cls):
    """返回该视图真正会执行的**写操作 action 名**集合。

    ViewSet: 自定义 @action (按 mapping 的 key 取 HTTP 方法, value 是 url_path)
             + router 绑定的标准 action (类上必须真的实现了)。
    APIView: 只有类上实现了对应 handler 的方法才算 (APIView.http_method_names 默认
             全开, 但没实现 post() 的请求根本走不到权限校验, 不算缺口)。
    """
    actions = set()
    if hasattr(cls, 'get_extra_actions'):          # ViewSet
        for action in cls.get_extra_actions():
            methods = {m.upper() for m in action.mapping.keys()}
            if methods - set(SAFE_METHODS):
                actions.add(action.__name__)
        for attr in ('create', 'update', 'partial_update', 'destroy'):
            if hasattr(cls, attr):
                actions.add(attr)
    else:                                          # APIView
        for m in getattr(cls, 'http_method_names', []):
            if m.upper() in SAFE_METHODS:
                continue
            if hasattr(cls, m.lower()):
                actions.add(m.lower())
    return actions


def action_level_v2(cls):
    """返回在 @action 上单独声明了 V2Permission 的 action 名。

    这类端点最容易漏: 类上没挂 V2Permission, 只扫类属性会完全看不见它们
    (例: RecruitmentProcessViewSet.batch-screen)。
    """
    getter = getattr(cls, 'get_extra_actions', None)
    if getter is None:
        return set()
    out = set()
    for action in getter():
        pc = (getattr(action, 'permission_classes', None)
              or getattr(action, 'kwargs', {}).get('permission_classes')
              or [])
        if V2Permission in pc:
            out.add(action.__name__)
    return out


def main():
    seen = {}
    for pattern, cb in iter_views(get_resolver()):
        cls = view_class(cb)
        if cls is None:
            continue
        class_perms = getattr(cls, 'permission_classes', []) or []
        act_perms = action_level_v2(cls)
        if V2Permission not in class_perms and not act_perms:
            continue
        key = f'{cls.__module__}.{cls.__name__}'
        entry = seen.setdefault(key, {'cls': cls, 'patterns': set()})
        entry['patterns'].add(pattern)
        entry['action_level'] = entry.get('action_level', set()) | act_perms

    gaps = []
    for key, info in sorted(seen.items()):
        cls = info['cls']
        declared = getattr(cls, 'permission_required', None)
        mapping = getattr(cls, 'permission_required_map', None) or {}
        self_service = getattr(cls, 'v2_self_service_actions', None) or ()
        writes = write_actions(cls)
        # 类上没挂 V2Permission 时, 只有 action 级声明过的 action 才受守卫约束
        if V2Permission not in (getattr(cls, 'permission_classes', []) or []):
            writes = writes & info.get('action_level', set())
        if not writes:
            continue
        # 已声明单码 / 多码 → create/update/destroy 由 V2Permission 自动派生, 视为已覆盖
        if declared:
            continue
        uncovered = writes - set(mapping) - set(self_service)
        if not uncovered:
            continue
        gaps.append((key, sorted(info['patterns']), sorted(uncovered)))

    print(f'V2Permission 端点视图总数: {len(seen)}')
    print(f'写操作未声明权限码的视图: {len(gaps)}\n')
    for key, patterns, writes in gaps:
        print(f'  {key}')
        print(f'      写方法: {writes}')
        for p in patterns[:3]:
            print(f'      路由  : {p}')
        print()
    # 有缺口时 exit 1, 便于直接挂 CI 阻断新增的未授权写端点。
    return 1 if gaps else 0


if __name__ == '__main__':
    raise SystemExit(main())
