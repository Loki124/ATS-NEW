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

        # 4) 校验 scene(入口)+类型 唯一性 (Q6) — 笛卡尔积组合不可被其它规则占用
        scenes = payload.get('scenes', [])
        recruit_types = payload.get('recruit_types') or ['social']
        scene_pairs = {(s, rt) for s in scenes for rt in recruit_types}
        self._check_scene_conflicts(rule_id, scene_pairs)

        # 5) 更新头部
        rule.name = (payload.get('name') or rule.name).strip() or rule.name
        rule.description = payload.get('description', rule.description)
        # 用户可选数量 (0 表示不限制)
        if 'max_selectable_tags' in payload:
            mst = payload.get('max_selectable_tags')
            rule.max_selectable_tags = max(0, int(mst)) if mst is not None else rule.max_selectable_tags
        # Item2: 系统预置规则保持不可停用 — enabled 强制 True
        if rule.is_system:
            rule.enabled = True
        elif 'enabled' in payload:
            rule.enabled = bool(payload['enabled'])
        # 同名校验
        if SceneRule.objects.filter(name=rule.name).exclude(pk=rule.pk).exists():
            raise BizException(BizCode.RULE_NAME_DUPLICATED, '该规则名已存在', status_code=400)
        rule.save(update_fields=['name', 'description', 'enabled', 'max_selectable_tags', 'updated_at'])

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
            # BUGFIX (2026-09-22): 不可盲目信任 payload 的 id —— 前端「添加子分类」
            # 给新分类分配的是客户端临时 id (uid() 形如 'c-xxx-1'), 该 id 并不存在于 DB。
            # 若直接拿它当 FK 建 category_assignment, 会触发 IntegrityError 并被下方
            # except 笼统误报为「标签重复」(用户实际看到的正是这种假重复).
            # 权威来源 = client_id 映射: step 6 已把「已有分类 client_id→db id」与
            # 「新分类临时 id→新 db id」全部登记进 client_id_to_new_id。
            # 仅当 payload 未带 client_id 时, 才回退到 id —— 且必须确认它是真实存在的
            # DB 分类 (existing_cats 为本次 diff 前的快照, 已更新分类必在其中)。
            cat_pk = client_id_to_new_id.get(cid) if cid else None
            if not cat_pk and existing_id and existing_id in existing_cats:
                cat_pk = existing_id
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

        # Item4 (修订): 规则内唯一 — 同一标签在当前规则内只可被使用一次。
        # 判定粒度 = 末级分类: 非末级(父级容器)分类不计入"使用次数", 仅末级分类上的
        # 赋值参与唯一性校验。这样当一级分类被拆分为多个子级时, 挂在原父级容器上的标签
        # 不会被误判为"跨分类重复" (用户明确意图: 校验的是标签在规则内只被使用一次)。
        # 跨规则共享标签池仍是合法业务需求, 不做全局限制。
        _all_cats = RuleCategory.objects.filter(rule=rule)
        _parent_ids = set(filter(None, _all_cats.values_list('parent_id', flat=True)))
        _leaf_ids = {c.id for c in _all_cats if c.id not in _parent_ids}
        tag_to_cats: dict = {}
        for cat_pk, tag_pks in target_assignments.items():
            if cat_pk not in _leaf_ids:
                continue  # 非末级容器分类: 不计入标签"使用次数"
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
                except IntegrityError as exc:
                    # 兜底 (2026-09-22 修订): category_assignment 已无 DB 唯一约束
                    # (Meta.constraints=[]), 规则内唯一完全由上方应用层校验保证; 故此处的
                    # IntegrityError 通常并非「标签重复」, 而是外键异常等真实缺陷
                    # (历史 bug: 新分类用客户端临时 id 建 FK → 1452, 被笼统误报为标签重复)。
                    # 因此必须: (1) 记录真实 DB 错误便于定位; (2) 回显标签名而非 id。
                    tag = ReasonTag.objects.filter(pk=tpk).first()
                    logger.warning(
                        'CategoryAssignment create failed: rule=%s category=%s tag=%s err=%s',
                        rule.pk, cat_pk, tpk, exc,
                    )
                    raise BizException(
                        BizCode.TAG_ALREADY_ASSIGNED,
                        f'同一规则内标签不可跨分类重复选择 (tag={tag.name if tag else tpk})',
                        status_code=409,
                    ) from exc

        # 8) Diff rule_scene_assignment (先删后增 — UNIQUE(scene, recruit_type) 兜底)
        #    规则应用范围 = 所选场景(入口) × 所选类型 的笛卡尔积
        recruit_types = payload.get('recruit_types') or ['social']
        desired_pairs = {(s, rt) for s in (scenes or []) for rt in recruit_types}
        if scenes is not None:
            existing_assigns = list(RuleSceneAssignment.objects.filter(rule=rule))
            existing_pairs = {(a.scene, a.recruit_type) for a in existing_assigns}
            to_delete = existing_pairs - desired_pairs
            if to_delete:
                del_ids = [a.id for a in existing_assigns if (a.scene, a.recruit_type) in to_delete]
                RuleSceneAssignment.objects.filter(rule=rule, id__in=del_ids).delete()
            # 预检冲突 (排除自身已有组合)
            self._check_scene_conflicts(rule.pk, desired_pairs)
            for (s, rt) in (desired_pairs - existing_pairs):
                try:
                    RuleSceneAssignment.objects.create(rule=rule, scene=s, recruit_type=rt)
                except IntegrityError:
                    raise BizException(
                        BizCode.RULE_SCENE_CONFLICT,
                        f'场景 {s}/类型 {rt} 已被其他规则占用',
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
        """拓扑排序: 父在前, 子在后; 同级按 order。

        ⚠️ 不能对整个结果按 order 做全局重排 —— 子级 order 常小于父级 order
        (如 addChild 生成的首个子分类 order=1, 而父级 order=3), 全局排序会把子级
        排到父级之前, 导致后端建 client_id → id 映射时父级尚未写入 → 父级解析为
        None → parent_id 丢失 (『保存后层级关系消失』的根因)。
        改为: 先按 order 预排序输入 (保证同级兄弟顺序), 再做 DFS 拓扑 (保证父在子前)。
        """
        def _cid(c): return (c.get('client_id') or c.get('clientId') or '').strip()
        def _pid(c): return (c.get('parent_client_id') or c.get('parentClientId') or '').strip()
        cids = {_cid(c) for c in categories if _cid(c)}
        # 先按 order 预排序: 同级兄弟保持 order; 拓扑 DFS 会把父级提到其子级之前
        ordered_input = sorted(categories, key=lambda c: int(c.get('order', 0)))
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

        for c in ordered_input:
            visit(c)
        return out

    def _check_scene_conflicts(self, current_rule_id: str, pairs: set) -> None:
        """校验 (scene, recruit_type) 组合不与其它规则冲突 (排除当前 rule 自己)。

        pairs: set of (scene, recruit_type) — 通常来自 场景(入口) × 类型 的笛卡尔积。
        """
        if not pairs:
            return
        occupied = RuleSceneAssignment.objects.filter(
            scene__in={p[0] for p in pairs},
            recruit_type__in={p[1] for p in pairs},
        ).exclude(rule_id=current_rule_id).values_list('scene', 'recruit_type')
        occupied_set = {(s, rt) for s, rt in occupied}
        bad = occupied_set & set(pairs)
        if bad:
            raise BizException(
                BizCode.RULE_SCENE_CONFLICT,
                f'以下场景/类型组合已被其它规则占用: {sorted(bad)}',
                status_code=409,
                extra={'conflicting_pairs': [list(p) for p in sorted(bad)]},
            )
