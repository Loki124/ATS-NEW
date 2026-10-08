"""CSV / JSON 导入导出服务 (T04 / T05 / T09).

- parse_csv_import(): 解析上传 CSV (由 view 调)
- parse_json_import(payload): 解析 JSON 完整 rule draft
- create_rule_from_import(payload): 落库为 custom rule
- export_rule_json(rule): 导出完整 draft JSON

T09 主要用 JSON 导入; CSV 导入在 tag_view 里直接实现 (轻量)。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from django.db import IntegrityError, transaction

from ..models import (
    MAX_CATEGORY_LEVEL,
    SCENE_OPTIONS,
    CategoryAssignment,
    ReasonTag,
    RuleCategory,
    RuleSceneAssignment,
    SceneRule,
)

logger = logging.getLogger(__name__)


def export_rule_json(rule: SceneRule) -> Dict[str, Any]:
    """导出 rule 完整 draft JSON。

    Schema:
      {
        'name': str,
        'description': str,
        'enabled': bool,
        'categories': [
          {'client_id': 'cat-1', 'parent_client_id': None, 'name': ..., 'order': int,
           'allow_custom': bool, 'tag_ids': [...]},
          ...
        ],
        'scenes': [scene_name, ...]
      }
    """
    cats = list(rule.categories.order_by('level', 'order'))
    # 按 parent 引用重写为 client_id 形式 (UUID → 临时 client_id)
    cid_for = {c.id: f'cat-{i}' for i, c in enumerate(cats, 1)}
    categories_out = []
    for c in cats:
        categories_out.append({
            'client_id': cid_for[c.id],
            'parent_client_id': cid_for.get(c.parent_id) if c.parent_id else None,
            'name': c.name,
            'order': c.order,
            'allow_custom': c.allow_custom,
            'level': c.level,
            'tag_ids': list(c.assignments.order_by('order').values_list('tag_id', flat=True)),
        })
    return {
        'name': rule.name,
        'description': rule.description,
        'enabled': rule.enabled,
        'is_system': rule.is_system,
        'categories': categories_out,
        'scenes': list(rule.scene_assignments.values_list('scene', flat=True)),
    }


def parse_json_import(payload: Dict[str, Any]) -> Dict[str, Any]:
    """校验 + 标准化 JSON payload (不写库), 返回处理后的 dict。

    Raises: ValueError (view 层转 BizException(JSON_FORMAT_INVALID, ...))
    """
    if not isinstance(payload, dict):
        raise ValueError('payload 必须为 JSON 对象')
    name = (payload.get('name') or '').strip()
    if not name:
        raise ValueError('name 不能为空')
    if len(name) > 64:
        raise ValueError('name 不能超过 64 字符')
    categories = payload.get('categories') or []
    if not isinstance(categories, list):
        raise ValueError('categories 必须为数组')
    scenes = payload.get('scenes') or []
    if not isinstance(scenes, list):
        raise ValueError('scenes 必须为数组')
    for s in scenes:
        if s not in SCENE_OPTIONS:
            raise ValueError(f'非法 scene: {s}')
    # 校验 tag_ids 都存在
    all_tag_ids = set()
    for c in categories:
        if not isinstance(c, dict):
            raise ValueError('categories 元素必须为对象')
        tag_ids = c.get('tag_ids') or []
        for tid in tag_ids:
            if not isinstance(tid, str):
                raise ValueError('tag_ids 必须为字符串数组')
            all_tag_ids.add(tid)
    existing_tags = set(
        ReasonTag.objects.filter(pk__in=all_tag_ids, deleted_at__isnull=True)
        .values_list('pk', flat=True)
    )
    missing = all_tag_ids - existing_tags
    if missing:
        raise ValueError(f'tag_ids 不存在或已软删: {sorted(missing)}')
    return {
        'name': name,
        'description': (payload.get('description') or '').strip()[:200],
        'enabled': bool(payload.get('enabled', True)),
        'categories': categories,
        'scenes': scenes,
    }


@transaction.atomic
def create_rule_from_import(payload: Dict[str, Any]) -> SceneRule:
    """从 JSON payload 创建 custom rule (T09).

    行为:
      - 始终创建 is_system=False 的规则
      - 同名自动追加 "(导入)" 后缀避免冲突
      - scenes 由 DB UNIQUE(scene) 兜底, 冲突抛 IntegrityError
    """
    normalized = parse_json_import(payload)

    # name 去重
    base_name = normalized['name']
    name = f'{base_name}(导入)'
    counter = 2
    while SceneRule.objects.filter(name=name).exists():
        name = f'{base_name}(导入{counter})'
        counter += 1

    rule = SceneRule.objects.create(
        name=name,
        is_system=False,
        enabled=normalized['enabled'],
        description=normalized['description'] or 'JSON 导入创建',
    )

    # 重建 categories (兼容 camelCase clientId/parentClientId/tagIds)
    client_id_to_pk: Dict[str, str] = {}
    parent_map = {}  # client_id -> parent_client_id
    for c in normalized['categories']:
        cid = c.get('client_id') or c.get('clientId') or ''
        if cid:
            parent_map[cid] = c.get('parent_client_id') or c.get('parentClientId') or None
    # 按 parent 在前创建 (BFS)
    processed = set()
    safety = 0
    while len(processed) < len(normalized['categories']) and safety < 1000:
        safety += 1
        progress = False
        for c in normalized['categories']:
            cid = c.get('client_id') or c.get('clientId') or ''
            if not cid or cid in processed:
                continue
            pid = parent_map.get(cid)
            if pid and pid not in processed:
                continue  # 等父先建
            parent_obj = None
            if pid:
                parent_pk = client_id_to_pk.get(pid)
                if parent_pk:
                    parent_obj = RuleCategory.objects.get(pk=parent_pk)
            level = (parent_obj.level + 1) if parent_obj else 1
            if level > MAX_CATEGORY_LEVEL:
                raise ValueError(f'分类 {cid} 层级 {level} 超过最大 {MAX_CATEGORY_LEVEL}')
            cat = RuleCategory.objects.create(
                rule=rule,
                parent=parent_obj,
                name=(c.get('name') or '').strip(),
                order=int(c.get('order', 0)),
                allow_custom=bool(c.get('allow_custom') or c.get('allowCustom') or False),
                level=level,
            )
            client_id_to_pk[cid] = cat.id
            # assignments (兼容 tagIds camelCase)
            tag_ids = c.get('tag_ids') or c.get('tagIds') or []
            for idx, tid in enumerate(tag_ids):
                CategoryAssignment.objects.create(
                    category=cat, tag_id=tid, order=idx,
                )
            processed.add(cid)
            progress = True
        if not progress:
            raise ValueError('categories 存在循环或孤悬引用')
    # 处理没 client_id 的 categories (按出现顺序, parent 为 None)
    for c in normalized['categories']:
        cid = c.get('client_id') or c.get('clientId') or ''
        if cid:
            continue
        cat = RuleCategory.objects.create(
            rule=rule,
            parent=None,
            name=(c.get('name') or '').strip(),
            order=int(c.get('order', 0)),
            allow_custom=bool(c.get('allow_custom') or c.get('allowCustom') or False),
            level=1,
        )
        for idx, tid in enumerate(c.get('tag_ids') or []):
            CategoryAssignment.objects.create(category=cat, tag_id=tid, order=idx)

    # scenes
    for s in normalized['scenes']:
        try:
            RuleSceneAssignment.objects.create(rule=rule, scene=s)
        except IntegrityError as e:
            raise IntegrityError(f'scene {s}: {e}')

    return rule
