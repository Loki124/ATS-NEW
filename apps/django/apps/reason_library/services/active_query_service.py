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


def _cache_key(scene_name: str, recruit_type: Optional[str] = None) -> str:
    if recruit_type:
        return f'rl:scene:{scene_name}:{recruit_type}'
    return CACHE_KEY_TEMPLATE.format(scene_name=scene_name)


def get_active_rule(scene_name: str, recruit_type: Optional[str] = None) -> Optional[SceneRule]:
    """返回当前 (scene, [recruit_type]) 的活跃 SceneRule (Q3 优先级) — 带 Redis 缓存。

    recruit_type 可选: 业务流当前未真正传类型 (见前端 system.ts 注释), 传 None 时退化为纯
    按场景兜底 (与历史行为一致); 一旦前端接入类型维度, 传入即可精确按 (场景,类型) 取规则。
    """
    key = _cache_key(scene_name, recruit_type)
    cached = cache.get(key)
    if cached and isinstance(cached, dict) and cached.get('rule_id'):
        try:
            rule = SceneRule.objects.get(pk=cached['rule_id'])
            # 二次校验 enabled + scene 绑定仍存在 (防 cache 与 DB 不一致)
            if not rule.enabled:
                cache.delete(key)
                return _query_active_rule_no_cache(scene_name, recruit_type)
            # 预置默认规则: 无 RuleSceneAssignment 行 (覆盖全部场景×类型), 跳过 scene 绑定校验
            if not rule.is_preset_default:
                q = RuleSceneAssignment.objects.filter(rule=rule, scene=scene_name)
                if recruit_type:
                    q = q.filter(recruit_type=recruit_type)
                if not q.exists():
                    cache.delete(key)
                    return _query_active_rule_no_cache(scene_name, recruit_type)
            return rule
        except SceneRule.DoesNotExist:
            cache.delete(key)
            return _query_active_rule_no_cache(scene_name, recruit_type)

    return _query_active_rule_no_cache(scene_name, recruit_type)


def _query_active_rule_no_cache(scene_name: str, recruit_type: Optional[str] = None) -> Optional[SceneRule]:
    """实际查 DB 写缓存。优先级: 显式引用(排除预置默认) > 预置默认规则兜底。"""
    # 1) 显式引用 (不含预置默认规则, 后者仅作全局兜底)
    explicit = (
        RuleSceneAssignment.objects
        .filter(scene=scene_name)
        .exclude(rule__is_system=True, rule__name='预置默认规则')
        .select_related('rule')
        .order_by('-rule__updated_at')
    )
    if recruit_type:
        explicit = explicit.filter(recruit_type=recruit_type)
    explicit_list = list(explicit)
    if explicit_list:
        chosen = explicit_list[0].rule
        _write_cache(scene_name, chosen, recruit_type)
        return chosen

    # 2) 预置默认规则兜底: 覆盖全部场景×类型, 任意 (场景,类型) 未命中显式规则时回退到它
    fallback = SceneRule.objects.preset_default()
    if fallback and fallback.enabled:
        _write_cache(scene_name, fallback, recruit_type)
        return fallback

    # 3) 真没有, 写空缓存 (短 TTL)
    cache.set(_cache_key(scene_name, recruit_type), {'rule_id': None, 'cached_at': datetime.utcnow().isoformat()}, CACHE_TTL)
    return None


def _write_cache(scene_name: str, rule: SceneRule, recruit_type: Optional[str] = None) -> None:
    cache.set(_cache_key(scene_name, recruit_type), {
        'rule_id': rule.id,
        'name': rule.name,
        'is_system': rule.is_system,
        'updated_at': rule.updated_at.isoformat(),
        'cached_at': datetime.utcnow().isoformat(),
    }, CACHE_TTL)


def invalidate_active_cache() -> None:
    """清掉所有 rl:scene:* 缓存 (含招聘类型后缀 social/campus)。"""
    recruit_types = ['social', 'campus']
    scenes = [
        '筛选不通过', '取消面试', '放入人才库', '淘汰', '标记失败', '邀约标注',
    ]
    try:
        # LocMemCache 不支持 delete_pattern, 直接 enumerate 场景 × (无后缀 + 各类型后缀)
        for s in scenes:
            cache.delete(_cache_key(s))
            for rt in recruit_types:
                cache.delete(_cache_key(s, rt))
    except Exception as e:  # noqa: BLE001 — cache 失效失败不影响主流程 (下次读时 cache miss 会重算, 仅日志)
        logger.warning('invalidate_active_cache failed: %s', e)


def invalidate_scene_cache(scene_name: str) -> None:
    cache.delete(_cache_key(scene_name))
    for rt in ['social', 'campus']:
        cache.delete(_cache_key(scene_name, rt))
