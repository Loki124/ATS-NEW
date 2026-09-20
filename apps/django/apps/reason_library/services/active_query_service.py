"""Active 业务态查询服务 (T08).

缓存策略:
- key:  rl:scene:{scene_name}
- TTL:  300s
- 值:   {'rule_id': ..., 'name': ..., 'updated_at': ..., 'cached_at': ...}
       (此处只缓存 rule 元信息, 完整树用 SceneRuleDetailSerializer 在 view 端实时拼)

失效:
- rule save / delete / wizard save / scene PUT / CSV import / JSON import
  都调用 ``invalidate_active_cache()`` 清理全部 rl:scene:* 缓存。
- 简单粗暴全清; 实际生产可按 rule_id 关联 scenes 精确失效, 但 V2 阶段
  active endpoint 缓存量本身很小, 6 个 key 直接全清。

Q3 优先级:
- 显式引用 (scene → rule) > 系统预置 (rule.is_system=True)
- 多条显式引用时: 取最新 updated_at
- 但实际场景里 UNIQUE(scene) 保证每个 scene 仅 1 条 RuleSceneAssignment,
  所以业务态只看"该 scene 是否有显式引用":
  - 有 → 用该 rule
  - 无 → 找 is_system=True 的 rule 且场景匹配 (兜底, 通过 rule_scenes 命中)
    即保留 r-resume 这种 system 规则自带默认 scenes 的设计。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.core.cache import cache
from django.db.models import Max

from ..models import RuleSceneAssignment, SceneRule

logger = logging.getLogger(__name__)

CACHE_KEY_TEMPLATE = 'rl:scene:{scene_name}'
CACHE_TTL = 300  # seconds


def _cache_key(scene_name: str) -> str:
    return CACHE_KEY_TEMPLATE.format(scene_name=scene_name)


def get_active_rule(scene_name: str) -> Optional[SceneRule]:
    """返回当前 scene 的活跃 SceneRule (Q3 优先级) — 带 Redis 缓存。"""
    cached = cache.get(_cache_key(scene_name))
    if cached and isinstance(cached, dict) and cached.get('rule_id'):
        try:
            rule = SceneRule.objects.get(pk=cached['rule_id'])
            # 二次校验 enabled + scene 绑定仍存在 (防 cache 与 DB 不一致)
            if not rule.enabled:
                cache.delete(_cache_key(scene_name))
                return _query_active_rule_no_cache(scene_name)
            # 校验 scene 当前是否还绑定该 rule
            if not RuleSceneAssignment.objects.filter(rule=rule, scene=scene_name).exists():
                cache.delete(_cache_key(scene_name))
                return _query_active_rule_no_cache(scene_name)
            return rule
        except SceneRule.DoesNotExist:
            cache.delete(_cache_key(scene_name))
            return _query_active_rule_no_cache(scene_name)

    return _query_active_rule_no_cache(scene_name)


def _query_active_rule_no_cache(scene_name: str) -> Optional[SceneRule]:
    """实际查 DB 写缓存。Q3: 显式 > 系统预置, 多条显式取最新 updated_at。"""
    # 1) 显式引用
    explicit = (
        RuleSceneAssignment.objects
        .filter(scene=scene_name)
        .select_related('rule')
        .order_by('-rule__updated_at')
    )
    explicit_list = list(explicit)
    if explicit_list:
        chosen = explicit_list[0].rule
        _write_cache(scene_name, chosen)
        return chosen

    # 2) 系统预置兜底: 找 is_system=True 且其 scene_assignments 含此 scene 的 rule
    fallback = (
        SceneRule.objects
        .filter(is_system=True, enabled=True, scene_assignments__scene=scene_name)
        .order_by('-updated_at')
        .first()
    )
    if fallback:
        _write_cache(scene_name, fallback)
        return fallback

    # 3) 真没有, 写空缓存 (短 TTL)
    cache.set(_cache_key(scene_name), {'rule_id': None, 'cached_at': datetime.utcnow().isoformat()}, CACHE_TTL)
    return None


def _write_cache(scene_name: str, rule: SceneRule) -> None:
    cache.set(_cache_key(scene_name), {
        'rule_id': rule.id,
        'name': rule.name,
        'is_system': rule.is_system,
        'updated_at': rule.updated_at.isoformat(),
        'cached_at': datetime.utcnow().isoformat(),
    }, CACHE_TTL)


def invalidate_active_cache() -> None:
    """清掉所有 rl:scene:* 缓存。"""
    try:
        # LocMemCache 不支持 delete_pattern, 直接 enumerate 6 个 scene
        for s in [
            '筛选不通过', '取消面试', '放入人才库', '淘汰', '标记失败', '邀约标注',
        ]:
            cache.delete(_cache_key(s))
    except Exception as e:  # noqa: BLE001
        logger.warning('invalidate_active_cache failed: %s', e)


def invalidate_scene_cache(scene_name: str) -> None:
    cache.delete(_cache_key(scene_name))
