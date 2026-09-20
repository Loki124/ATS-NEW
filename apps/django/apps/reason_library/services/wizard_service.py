"""Wizard 三步原子保存服务 (T06).

事务内顺序 (2026-09-21: 行锁已移除; 乐观锁改为【可选】——if_match 非空才校验):
1. 读取 scene_rule 行
2. 可选乐观锁: if_match 非空则比对 updated_at → 抛 OPTIMISTIC_LOCK_FAILED (412)
3. 校验 categories 最大深度 (level<=4) → 抛 CATEGORY_LEVEL_EXCEED (400)
3. 校验 scenes 不与其它规则冲突 → 抛 RULE_SCENE_CONFLICT (409)
4. diff categories (按 client_id ↔ db id), 维护 level/order
5. diff category_assignments
6. diff rule_scene_assignment (先删后增)
7. 更新 scene_rule 头部

失败时回滚整事务; 抛出 BizException, 由 view 转 ApiResponse.error.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime

from ..exceptions import BizCode, BizException
from ..models import (
    MAX_CATEGORY_LEVEL,
    CategoryAssignment,
    ReasonTag,
    RuleCategory,
    RuleSceneAssignment,
    SceneRule,
)

logger = logging.getLogger(__name__)


class WizardService:
    """Wizard 三步原子保存。"""

    @transaction.atomic
    def save(
        self,
        rule_id: str,
        payload: Dict[str, Any],
        if_match: Optional[str] = None,
        user: Any = None,
    ) -> SceneRule:
        """保存 rule + 完整树 + scenes。

        payload keys:
          - name, description, enabled
          - categories: [{id?, client_id?, parent_client_id?, name, order, allow_custom, tag_ids}]
          - scenes: [scene_name, ...]
        """
        # 1) 读取规则行 (单人场景: 不加行锁)
        try:
            rule = SceneRule.objects.get(pk=rule_id)
        except SceneRule.DoesNotExist:
            raise BizException(BizCode.RULE_NOT_FOUND, '规则不存在', status_code=404)

        # 2) 乐观锁
        if if_match:
            expected = self._parse_dt(if_match)
            if expected is None:
                raise BizException(
                    BizCode.VALIDATION_FAILED,
                    f'If-Match 格式非法: {if_match}',
                    status_code=400,
                )
            # tz 统一: DB updated_at 是 aware UTC, naive 需补 tz 才能比较
            if expected.tzinfo is None:
                expected = expected.replace(tzinfo=timezone.utc)
            exp_trunc = expected.replace(microsecond=0)
            act_trunc = rule.updated_at.replace(microsecond=0)
            if exp_trunc != act_trunc:
                raise BizException(
                    BizCode.OPTIMISTIC_LOCK_FAILED,
                    f'数据已被他人修改 (expected={exp_trunc.isoformat()}, actual={act_trunc.isoformat()})',
                    status_code=412,
                    extra={
                        'expected_updated_at': exp_trunc.isoformat(),
                        'actual_updated_at': act_trunc.isoformat(),
                    },
                )

        # 2) 系统规则 HR 及以上可改 (write 端兜底, 与 SystemOrAdminPermission 一致);
        #    Item2: 取消"仅超管"限制, 但 enabled 保持强制 True (不可停用),
        #    见下方 step 5 头部更新。
        if rule.is_system:
            from apps.core.permissions import is_hr_or_above, is_super_admin
            if not (user and (is_super_admin(user) or is_hr_or_above(user))):
                raise BizException(
                    BizCode.SYSTEM_RULE_IMMUTABLE,
                    '系统预置规则仅 HR 及以上可改',
                    status_code=403,
                )

        # 3) 计算 categories level (按 parent_client_id 推导)
        categories_payload = payload.get('categories', [])
        client_id_to_level = self._compute_levels(categories_payload)

        # 4) 校验 scene 唯一性 (Q6)
        scenes = payload.get('scenes', [])
        self._check_scene_conflicts(rule_id, scenes)

        # 5) 更新头部
        rule.name = (payload.get('name') or rule.name).strip() or rule.name
        rule.description = payload.get('description', rule.description)
        # Item2: 系统预置规则保持不可停用 — enabled 强制 True
        if rule.is_system:
            rule.enabled = True
        elif 'enabled' in payload:
            rule.enabled = bool(payload['enabled'])
        # 同名校验
        if SceneRule.objects.filter(name=rule.name).exclude(pk=rule.pk).exists():
            raise BizException(BizCode.RULE_NAME_DUPLICATED, '该规则名已存在', status_code=400)
        rule.save(update_fields=['name', 'description', 'enabled', 'updated_at'])

        # 6) Diff categories: 维护 client_id → id 映射, 同时处理 add/update/delete
        existing_cats = {
            c.id: c for c in RuleCategory.objects.filter(rule=rule)
        }
        # 处理顺序: 按 parent 在前, 子在后的拓扑序
        ordered_cats = self._topo_sort_categories(categories_payload)

        client_id_to_new_id: Dict[str, str] = {}
        seen_db_ids = set()
        for cdef in ordered_cats:
            # 兼容 camelCase (前端 wire-format) 与 snake_case (DRF 转换后)
            cid = (cdef.get('client_id') or cdef.get('clientId') or '').strip()
            existing_id = (cdef.get('id') or '').strip() or None
            parent_client_id = (cdef.get('parent_client_id') or cdef.get('parentClientId') or '').strip()
            parent_obj = None
            if parent_client_id:
                parent_pk = client_id_to_new_id.get(parent_client_id)
                if parent_pk:
                    parent_obj = RuleCategory.objects.get(pk=parent_pk)
            name = (cdef.get('name') or '').strip()
            if not name:
                raise BizException(
                    BizCode.VALIDATION_FAILED,
                    f'分类名不能为空 (client_id={cid})',
                    status_code=400,
                )
            order = int(cdef.get('order', 0))
            allow_custom = bool(cdef.get('allow_custom', False))
            level = client_id_to_level.get(cid, 1)

            if existing_id and existing_id in existing_cats:
                # update
                cat = existing_cats[existing_id]
                cat.name = name
                cat.order = order
                cat.allow_custom = allow_custom
                cat.level = level
                cat.parent = parent_obj
                cat.save(update_fields=['name', 'order', 'allow_custom', 'level', 'parent'])
                seen_db_ids.add(existing_id)
                if cid:
                    client_id_to_new_id[cid] = cat.id
            else:
                # create (新增)
                cat = RuleCategory.objects.create(
                    rule=rule,
                    parent=parent_obj,
                    name=name,
                    order=order,
                    allow_custom=allow_custom,
                    level=level,
                )
                if cid:
                    client_id_to_new_id[cid] = cat.id
                if existing_id:
                    seen_db_ids.add(existing_id)

        # 删除 categories: 提交中未出现的 db id 即视为删
        to_delete = [cid for cid in existing_cats if cid not in seen_db_ids]
        if to_delete:
            RuleCategory.objects.filter(pk__in=to_delete).delete()

        # 7) Diff category_assignments
        # 重建当前 rule 完整 cat → tag_ids 映射 (从 payload 出发)
        # 用 category_id (= RuleCategory.pk) 做匹配, payload 用 client_id 时通过 client_id_to_new_id 映射
        target_assignments: Dict[str, set] = {}  # category_pk -> set(tag_pk)
        for cdef in categories_payload:
            cid = (cdef.get('client_id') or '').strip()
            existing_id = (cdef.get('id') or '').strip()
            cat_pk = existing_id or client_id_to_new_id.get(cid)
            if not cat_pk:
                continue
            tag_ids = cdef.get('tag_ids') or []
            # 校验 tag 都存在且未软删
            valid_tag_ids = set(
                ReasonTag.objects.filter(pk__in=tag_ids, deleted_at__isnull=True)
                .values_list('pk', flat=True)
            )
            missing = set(tag_ids) - valid_tag_ids
            if missing:
                raise BizException(
                    BizCode.VALIDATION_FAILED,
                    f'category {cid} 引用了不存在的标签: {sorted(missing)}',
                    status_code=400,
                )
            target_assignments[cat_pk] = valid_tag_ids

        # 已有 assignments
        existing_assignments_qs = CategoryAssignment.objects.filter(
            category__rule=rule
        ).values('id', 'category_id', 'tag_id', 'order')
        existing_set = {(a['category_id'], a['tag_id']): a for a in existing_assignments_qs}

        # Item4 (修订): 规则内唯一 — 同一标签在本规则内不可跨分类重复。
        # 跨规则共享标签池是合法业务需求, 不做全局限制。
        tag_to_cats: dict = {}
        for cat_pk, tag_pks in target_assignments.items():
            for tpk in tag_pks:
                tag_to_cats.setdefault(tpk, []).append(cat_pk)
        dup = {tpk: cats for tpk, cats in tag_to_cats.items() if len(cats) > 1}
        if dup:
            tpk = next(iter(dup))
            tag = ReasonTag.objects.filter(pk=tpk).first()
            raise BizException(
                BizCode.TAG_ALREADY_ASSIGNED,
                f'同一规则内标签不可跨分类重复选择 (tag={tag.name if tag else tpk})',
                status_code=409,
            )

        # 计算 diff
        new_pairs = set()
        for cat_pk, tag_pks in target_assignments.items():
            for tpk in tag_pks:
                new_pairs.add((cat_pk, tpk))

        # delete: 在 existing 但不在 new
        to_delete_asn_ids = [
            a['id'] for pair, a in existing_set.items()
            if pair not in new_pairs
        ]
        if to_delete_asn_ids:
            CategoryAssignment.objects.filter(pk__in=to_delete_asn_ids).delete()

        # create: 在 new 但不在 existing
        existing_pairs = set(existing_set.keys())
        for cat_pk, tpk in new_pairs:
            if (cat_pk, tpk) not in existing_pairs:
                try:
                    CategoryAssignment.objects.create(category_id=cat_pk, tag_id=tpk)
                except IntegrityError:
                    # Item4: 同规则内标签唯一 (应用层校验的并发兜底)
                    raise BizException(
                        BizCode.TAG_ALREADY_ASSIGNED,
                        f'同一规则内标签不可跨分类重复选择 (tag={tpk})',
                        status_code=409,
                    )

        # 8) Diff rule_scene_assignment (先删后增 — UNIQUE 兜底)
        if scenes is not None:
            RuleSceneAssignment.objects.filter(rule=rule).delete()
            for s in scenes:
                try:
                    RuleSceneAssignment.objects.create(rule=rule, scene=s)
                except IntegrityError:
                    raise BizException(
                        BizCode.RULE_SCENE_CONFLICT,
                        f'场景 {s} 已被其他规则占用',
                        status_code=409,
                    )

        # 失效缓存 (import 在 view 层已 import 此函数, 这里同步)
        from .active_query_service import invalidate_active_cache
        invalidate_active_cache()

        # 重新读一次 (事务内可能 stale)
        rule.refresh_from_db()
        return rule

    # -----------------------------------------------------------------------
    # helpers
    def _parse_dt(self, raw: str) -> Optional[datetime]:
        dt = parse_datetime(raw)
        if dt is not None:
            return dt
        for fmt in ('%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S %z'):
            try:
                return datetime.strptime(raw, fmt)
            except (ValueError, TypeError):
                continue
        return None

    # -----------------------------------------------------------------------

    def _compute_levels(self, categories: List[Dict]) -> Dict[str, int]:
        """按 parent_client_id 推导 level, 同时校验无循环引用 + 无 level 超限。

        Returns: {client_id -> level}
        """
        # 兼容 camelCase 与 snake_case
        def _cid(c): return (c.get('client_id') or c.get('clientId') or '').strip()
        def _pid(c): return (c.get('parent_client_id') or c.get('parentClientId') or '').strip()
        # 建立 client_id → parent_client_id 映射
        cids = {_cid(c) for c in categories if _cid(c)}
        parent_of: Dict[str, str] = {}
        for c in categories:
            cid = _cid(c)
            pid = _pid(c)
            if cid and pid:
                parent_of[cid] = pid

        result: Dict[str, int] = {}
        # DFS 计算每个 cid 的 level
        for cid in cids:
            level = self._dfs_level(cid, parent_of, seen=set())
            if level > MAX_CATEGORY_LEVEL:
                raise BizException(
                    BizCode.CATEGORY_LEVEL_EXCEED,
                    f'分类 client_id={cid} 层级 {level} 超过最大 {MAX_CATEGORY_LEVEL}',
                    status_code=400,
                )
            result[cid] = level
        return result

    def _dfs_level(self, cid: str, parent_of: Dict[str, str], seen: set) -> int:
        if cid in seen:
            raise BizException(
                BizCode.VALIDATION_FAILED,
                f'分类引用存在循环: {cid}',
                status_code=400,
            )
        seen = seen | {cid}
        parent = parent_of.get(cid)
        if not parent:
            return 1
        # 父 client_id 必出现在 categories 中 (前端约定)
        return 1 + self._dfs_level(parent, parent_of, seen)

    def _topo_sort_categories(self, categories: List[Dict]) -> List[Dict]:
        """拓扑排序: 父在前, 子在后。同一层按出现顺序。"""
        def _cid(c): return (c.get('client_id') or c.get('clientId') or '').strip()
        def _pid(c): return (c.get('parent_client_id') or c.get('parentClientId') or '').strip()
        cids = {_cid(c) for c in categories if _cid(c)}
        index = {_cid(c): i for i, c in enumerate(categories) if _cid(c)}
        out: List[Dict] = []
        visited = set()

        def visit(cdef: Dict):
            cid = _cid(cdef)
            if cid in visited:
                return
            visited.add(cid)
            pid = _pid(cdef)
            if pid and pid in cids:
                # 找到 parent 的 def
                parent_def = next(
                    (c for c in categories if _cid(c) == pid),
                    None,
                )
                if parent_def:
                    visit(parent_def)
            out.append(cdef)

        for c in categories:
            visit(c)
        # 按原 order 字段排序 (output 顺序只保证父在前, 同一父的子顺序按 cdef.order)
        out.sort(key=lambda c: int(c.get('order', 0)))
        return out

    def _check_scene_conflicts(self, current_rule_id: str, scenes: List[str]) -> None:
        """校验 scenes 不与其它规则冲突 (排除当前 rule 自己)。"""
        if not scenes:
            return
        # 已经绑定其它 rule 的 scene
        occupied = RuleSceneAssignment.objects.filter(
            scene__in=scenes
        ).exclude(rule_id=current_rule_id).values_list('scene', flat=True)
        occupied_set = set(occupied)
        if occupied_set:
            raise BizException(
                BizCode.RULE_SCENE_CONFLICT,
                f'以下场景已被其它规则占用: {sorted(occupied_set)}',
                status_code=409,
                extra={'conflicting_scenes': sorted(occupied_set)},
            )
