"""可配置动作字典的读取层（权限 v2）。

DB（DataPermissionAction / DataPermissionActionPreset）是运行时真相源；
本模块负责：
- TTL 缓存读取（5 分钟，测试可经 settings 置 0 —— 与 V2_PERM_CODES_CACHE_TTL 同款）；
- DB 不可用时的**兜底降级**：回退 action_map 种子，语义 = 全部动作可用
  （fail-open，与「不锁死写入口」的守卫哲学一致 —— 字典是收紧手段，字典不可读
  不应反向扩大拒绝面）；
- 保存规则时的 actions 合法性校验；
- 字典变更后的缓存失效。

测试注意：用例间必须 invalidate_cache()，否则跨用例缓存污染会造成顺序依赖
（test.py 已把 TTL 置 0 的项目同样建议显式失效，双保险）。
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import OperationalError, ProgrammingError

from . import action_map
from .models import DataPermissionAction, DataPermissionActionPreset

logger = logging.getLogger(__name__)

_ACTION_DICT_CACHE_KEY = 'dp:action-dict:v1'
_PRESET_DICT_CACHE_KEY = 'dp:preset-dict:v1'
_DEFAULT_TTL = 300


def _cache_ttl() -> int:
    return int(getattr(settings, 'DP_ACTION_DICT_CACHE_TTL', _DEFAULT_TTL))


def invalidate_cache() -> None:
    """动作/预设字典变更后调用（管理接口 save/delete 处）。"""
    cache.delete(_ACTION_DICT_CACHE_KEY)
    cache.delete(_PRESET_DICT_CACHE_KEY)


def action_dict() -> list[dict]:
    """全量动作清单（含停用，供管理页与 options 下发）。

    DB 读失败 -> 回退种子（enabled 全 True）。每项含 key/label/category/destructive/
    enabled/is_system/sort_order。
    """
    cached = cache.get(_ACTION_DICT_CACHE_KEY)
    if cached is not None:
        return cached
    try:
        items = [
            {
                'key': a.key,
                'label': a.label,
                'category': a.category,
                'destructive': a.destructive,
                'enabled': a.enabled,
                'is_system': a.is_system,
                'sort_order': a.sort_order,
            }
            for a in DataPermissionAction.objects.all().order_by('sort_order', 'key')
        ]
    except (OperationalError, ProgrammingError):
        logger.warning('动作字典表不可用, 回退 action_map 种子（全部可用）')
        items = [
            {
                'key': key,
                'label': meta['label'],
                'category': meta.get('category', 'write'),
                'destructive': meta.get('destructive', False),
                'enabled': True,
                'is_system': True,
                'sort_order': meta.get('sort_order', 0),
            }
            for key, meta in action_map.ACTION_REGISTRY.items()
        ]
    cache.set(_ACTION_DICT_CACHE_KEY, items, _cache_ttl())
    return items


def enabled_action_keys() -> set[str]:
    """当前启用的动作 key 集合（write_scope_q 运行时过滤用）。"""
    return {a['key'] for a in action_dict() if a['enabled']}


def is_action_enabled(action: str) -> bool:
    """动作是否启用；未注册的动作一律 False（fail-closed）。"""
    return action in enabled_action_keys()


def preset_dict() -> dict[str, list[str]]:
    """预设包清单（key -> action_keys）。DB 读失败 -> 回退种子。"""
    cached = cache.get(_PRESET_DICT_CACHE_KEY)
    if cached is not None:
        return cached
    try:
        items = {
            p.key: list(p.action_keys or [])
            for p in DataPermissionActionPreset.objects.all().order_by('sort_order', 'key')
        }
    except (OperationalError, ProgrammingError):
        logger.warning('预设包表不可用, 回退 action_map 种子')
        items = {k: list(v) for k, v in action_map.PRESET_PACKAGES.items()}
    cache.set(_PRESET_DICT_CACHE_KEY, items, _cache_ttl())
    return items


def validate_write_actions(actions: list | None) -> str | None:
    """保存 WRITE 规则时校验 actions 合法性。返回首个错误原因或 None。

    规则：
    - 必须是非空字符串数组（[] = 拒绝一切写动作，合法但前端需二次确认，这里放行）；
    - 每个 key 必须存在于字典且处于启用状态（停用动作不允许再配进新规则 ——
      否则会出现「配置时可用、字典停用后行为悄变」的窗口；停用语义由运行时 deny 承担）；
    - 重复 key 去重不算错，但保持调用方原样提交由后端归一。
    """
    if actions is None:
        return None  # NULL = 全动作放行（双读兼容）
    if not isinstance(actions, list):
        return 'actions 必须是数组'
    seen: set[str] = set()
    enabled = enabled_action_keys()
    known = {a['key'] for a in action_dict()}
    for a in actions:
        if not isinstance(a, str) or not a:
            return 'actions 元素必须是非空字符串'
        if a in seen:
            continue
        seen.add(a)
        if a not in known:
            return f'未知动作 key: {a}'
        if a not in enabled:
            return f'动作已停用，不允许配置: {a}'
    return None
