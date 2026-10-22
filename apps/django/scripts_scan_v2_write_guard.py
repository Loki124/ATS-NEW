"""扫描所有挂在 V2Permission 下的端点, 列出两类「写操作未被正确授权」的视图。

用法:
    python manage.py shell < scripts_scan_v2_write_guard.py
    或:  DJANGO_SETTINGS_MODULE=config.settings.test python scripts_scan_v2_write_guard.py

背景: V2Permission 修复后, 未声明 permission_required / permission_required_map 的
**写操作**会被拒绝。本脚本在开启严格守卫前把遗漏清单一次性列全, 避免逐个试错。

2026-10-21 (卡 A3) 修复的结构性盲区:
    原实现在「视图声明了单个 permission_required」时直接 `continue` ——
    理由是「create/update/destroy 由 V2Permission 自动派生, 视为已覆盖」。
    但**派生码本身可能没在 PermissionResource 里注册**。此时
    `V2Permission._derive()` 会走 fallback 分支, 把写操作回退到**读码**校验 ——
    结果是「只持 :list 权限的账号可以执行写操作」(权限提升), 而不是被拒绝。
    这个缺口正是这样进 CI 的。

    现补两类检查:
      ① 未声明: 写操作既无 permission_required 也无 map / self_service 覆盖
      ② 派生码未注册: 单码声明时, 按 action 派生出的写码不在已注册集合里
         (派生规则直接复用 permissions_v2.ACTION_SUFFIX / CUSTOM_ACTION_SUFFIX,
          与 V2Permission._derive 单一真相源一致)

    已注册集合 = PermissionResource 表(运行时真源) ∪ seed RESOURCES(声明真源)。
    取并集是为了避免本地库滞后(seed 有而库无)造成的假阳性;
    两侧都没有的才是真缺口。
"""
import importlib.util
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')

import django  # noqa: E402
django.setup()

from django.urls import get_resolver  # noqa: E402
from rest_framework.permissions import SAFE_METHODS  # noqa: E402

from apps.core.permissions_v2 import (  # noqa: E402
    ACTION_SUFFIX,
    CUSTOM_ACTION_SUFFIX,
    V2Permission,
    known_resource_codes,
)


def seed_resource_codes():
    """从 seed_v2_init.RESOURCES 取声明的资源码 (不触发 DB 访问)。"""
    seed_path = pathlib.Path(__file__).resolve().parent / (
        'apps/core/management/commands/seed_v2_init.py'
    )
    if not seed_path.exists():
        return set()
    spec = importlib.util.spec_from_file_location('seed_v2_init_probe', seed_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {code for code, *_rest in mod.RESOURCES}



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

    # 已注册资源码 = 运行时真源(DB) ∪ 声明真源(seed)
    known = set(known_resource_codes())
    seed_known = seed_resource_codes()
    known |= seed_known

    gaps = []          # ① 写操作完全没声明权限码
    derived_gaps = []  # ② 单码声明, 但派生出的写码未注册 (会静默回退到读码 → 权限提升)
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

        # ② 单码声明 → 逐 action 派生写码并校验是否已注册
        #    多码声明(list/tuple) 是调用方明确意图, 原样校验, 不派生。
        if isinstance(declared, str) and declared:
            base = declared.rsplit(':', 1)[0] if ':' in declared else declared
            is_viewset = hasattr(cls, 'get_extra_actions')
            for act in sorted(writes):
                # map 显式覆盖的 action 不走派生 (ViewSet 用 action 名, APIView 用 HTTP method)
                map_key = act if is_viewset else act
                if map_key in mapping:
                    continue
                if act in self_service:
                    continue
                # APIView 的 view.action 恒为 None → V2Permission._derive 收到 action=''
                action_name = act if is_viewset else ''
                suffix = ACTION_SUFFIX.get(action_name, CUSTOM_ACTION_SUFFIX)
                derived = f'{base}:{suffix}'
                if derived == declared:
                    continue
                if derived not in known:
                    derived_gaps.append((
                        key, sorted(info['patterns']), act, derived, declared,
                    ))
            continue

        # ① 完全未声明 → 写操作既无 required 也无 map / self_service 覆盖
        if declared:
            continue
        uncovered = writes - set(mapping) - set(self_service)
        if not uncovered:
            continue
        gaps.append((key, sorted(info['patterns']), sorted(uncovered)))

    print(f'V2Permission 端点视图总数: {len(seen)}')
    print(f'已注册资源码: DB {len(known_resource_codes())} 个 / seed {len(seed_known)} 个 '
          f'/ 并集 {len(known)} 个')
    print(f'写操作未声明权限码的视图: {len(gaps)}')
    print(f'派生写码未注册(会回退到读码 → 权限提升)的视图: {len(derived_gaps)}\n')
    for key, patterns, writes in gaps:
        print(f'  [未声明] {key}')
        print(f'      写方法: {writes}')
        for p in patterns[:3]:
            print(f'      路由  : {p}')
        print()
    for key, patterns, act, derived, declared in derived_gaps:
        print(f'  [派生码未注册] {key}')
        print(f'      写方法: {act}  → 实际应校验 {derived!r}, 但未注册')
        print(f'      回退到: {declared!r} (持该读码的账号可执行此写操作 ← 权限提升)')
        for p in patterns[:3]:
            print(f'      路由  : {p}')
        print()
    # 有缺口时 exit 1, 便于直接挂 CI 阻断新增的未授权写端点。
    return 1 if (gaps or derived_gaps) else 0



if __name__ == '__main__':
    raise SystemExit(main())
