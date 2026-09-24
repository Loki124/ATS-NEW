"""Scene Rule CRUD + 详情快照 (T05 / T11).

端点:
- GET    /rules/                    列表
- POST   /rules/                    创建 (头部, 后续 wizard/save 灌树)
- GET    /rules/{id}/               详情 (完整树: rule + categories + assignments + scenes)
- PATCH  /rules/{id}/               更新头部 (is_system=True 仅超管)
- DELETE /rules/{id}/               删除 (system 不可删; 有引用 scene 不可删)
- POST   /rules/{id}/snapshot/      复制为 custom 副本 (name + "(副本)")
- POST   /rules/{id}/wizard/save/   三步原子保存 (见 wizard_view.py)
- POST   /rules/import/             JSON 导入完整 draft (T09)

并发策略: 单人维护场景默认不启用; 后端保留【可选乐观锁】——仅当请求带 If-Match
头时才比对 updated_at (不带则直接跳过, 前端默认不发), 未来多人协作时前端开启即可。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from django.utils.dateparse import parse_datetime

from ..exceptions import ApiResponse, BizCode, BizException
from ..filters import SceneRuleFilter
from ..models import (
    CategoryAssignment, ReasonTag, RuleCategory,
    RuleSceneAssignment, SceneRule,
)
from ..permissions import (
    IsAdminOrReadOnly, IsAuthenticatedReadOnly, SystemOrAdminPermission,
)
from ..serializers import (
    SceneRuleCreateSerializer, SceneRuleDetailSerializer,
    SceneRuleListSerializer, SceneRuleUpdateSerializer,
)
from ..services.active_query_service import invalidate_active_cache
from ..services.import_export_service import (
    create_rule_from_import, export_rule_json,
)
from . import _api

logger = logging.getLogger(__name__)

def _parse_if_match(request: Request):
    """解析 If-Match header → datetime 或 None。"""
    raw = request.headers.get('If-Match') or request.META.get('HTTP_IF_MATCH')
    if not raw:
        return None
    # RFC1123 / ISO 都尝试
    dt = parse_datetime(raw)
    if dt is not None:
        return dt
    # 兼容 RFC1123 ('%a, %d %b %Y %H:%M:%S %Z')
    for fmt in ('%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(raw, fmt)
        except (ValueError, TypeError):
            continue
    return None


class SceneRuleViewSet(viewsets.ModelViewSet):
    """场景规则 CRUD。"""

    queryset = SceneRule.objects.all()
    permission_classes = [IsAuthenticatedReadOnly, SystemOrAdminPermission]
    filterset_class = SceneRuleFilter
    lookup_field = 'pk'
    ordering = ['-is_system', '-updated_at']
    search_fields = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return SceneRuleListSerializer
        if self.action == 'create':
            return SceneRuleCreateSerializer
        if self.action in ('update', 'partial_update'):
            return SceneRuleUpdateSerializer
        if self.action == 'retrieve':
            return SceneRuleDetailSerializer
        return SceneRuleDetailSerializer

    # ----- queryset (N+1 优化) -----
    def get_queryset(self):
        qs = super().get_queryset()
        # 列表接口一次性 annotate 出每条规则的「启用且未软删」标签去重数量,
        # 供 SceneRuleListSerializer.tag_count 直接读取, 避免逐条 ORM 查询 (N+1)。
        # 业务口径与 serializers.get_tag_ids 一致:
        #   tag__enabled=True & tag__deleted_at__isnull=True,
        #   关联路径 categories__assignments__tag, distinct=True 去重标签。
        # retrieve / partial_update 用单实例且未 annotate, 由序列化器回退 ORM 查询。
        if self.action == 'list':
            qs = qs.annotate(
                tag_count=Count(
                    'categories__assignments__tag',
                    filter=Q(
                        categories__assignments__tag__enabled=True,
                        categories__assignments__tag__deleted_at__isnull=True,
                    ),
                    distinct=True,
                )
            )
        return qs

    # ----- list -----
    @_api
    def list(self, request: Request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            data = SceneRuleListSerializer(page, many=True).data
            return self._paginated_response(data)
        data = SceneRuleListSerializer(qs, many=True).data
        return ApiResponse.ok(data)

    @_api
    def retrieve(self, request: Request, *args, **kwargs):
        try:
            obj = self.get_object()
        except SceneRule.DoesNotExist:
            raise BizException(BizCode.RULE_NOT_FOUND, '规则不存在', status_code=404)
        return ApiResponse.ok(SceneRuleDetailSerializer(obj).data)

    @_api
    def create(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            raise BizException(
                BizCode.VALIDATION_FAILED, '参数校验失败',
                status_code=400, extra={'errors': serializer.errors},
            )
        try:
            with transaction.atomic():
                rule = serializer.save()
        except IntegrityError:
            raise BizException(BizCode.RULE_NAME_DUPLICATED, '该规则名已存在', status_code=400)
        return ApiResponse.created(SceneRuleDetailSerializer(rule).data)

    @_api
    def partial_update(self, request: Request, *args, **kwargs):
        try:
            obj = self.get_object()
        except SceneRule.DoesNotExist:
            raise BizException(BizCode.RULE_NOT_FOUND, '规则不存在', status_code=404)
        # Item2: 系统预置规则 HR 及以上可改 (对象权限由 SystemOrAdminPermission 兜底);
        #        但 enabled 强制 True — 系统预置规则保持不可停用。
        # 预置默认规则 (is_system AND name=='预置默认规则'): 名称/状态/覆盖均不可调整
        # (覆盖在 wizard_service.save 内守卫), 此处拦截改名 — 名称锁定以保 is_preset_default 判定稳定。
        if obj.is_system:
            data = dict(request.data)
            data['enabled'] = True
            if obj.is_preset_default:
                data.pop('name', None)
        else:
            data = request.data
        # 可选乐观锁: 仅当请求带 If-Match 头时校验 (单人场景前端不发 → 自动跳过)
        self._check_optimistic_lock(request, obj)

        serializer = self.get_serializer(obj, data=data, partial=True)
        if not serializer.is_valid():
            raise BizException(
                BizCode.VALIDATION_FAILED, '参数校验失败',
                status_code=400, extra={'errors': serializer.errors},
            )
        try:
            with transaction.atomic():
                rule = serializer.save()
        except IntegrityError:
            raise BizException(BizCode.RULE_NAME_DUPLICATED, '该规则名已存在', status_code=400)
        invalidate_active_cache()
        return ApiResponse.ok(SceneRuleListSerializer(rule).data)

    @_api
    def destroy(self, request: Request, *args, **kwargs):
        try:
            obj = self.get_object()
        except SceneRule.DoesNotExist:
            raise BizException(BizCode.RULE_NOT_FOUND, '规则不存在', status_code=404)
        # Q-A3 + 兵哥拍板: 系统预置规则一律不可删 (即使超管) — 删除是危险操作,
        # 会 CASCADE 释放 scene 占用 + 删分类树。修改 (PUT) 允许超管改字段,
        # 删除保持硬保护。需要"重置"系统规则请走 fixture + 二次确认流程。
        if obj.is_system:
            raise BizException(
                BizCode.SYSTEM_RULE_IMMUTABLE,
                '系统预置规则不可删除 (仅超管可改字段, 不允许删除)',
                status_code=403,
            )
        # 有场景引用时, 若调用方没显式解绑 scene, 自动解绑 (CASCADE 自带)
        # 此处不报错, 因为 rule 一删 scene 绑定自动释放
        rule_id = obj.id
        rule_name = obj.name
        with transaction.atomic():
            obj.delete()
        invalidate_active_cache()
        return ApiResponse.ok({'id': rule_id, 'name': rule_name})

    # ----- snapshot -----
    @action(
        detail=True, methods=['post'], url_path='snapshot',
        permission_classes=[IsAuthenticatedReadOnly, SystemOrAdminPermission],
    )
    @_api
    def snapshot(self, request: Request, pk=None, **kwargs):
        """复制规则为 custom 副本 (name + '(副本)'), 含完整树。"""
        try:
            src = SceneRule.objects.get(pk=pk)
        except SceneRule.DoesNotExist:
            raise BizException(BizCode.RULE_NOT_FOUND, '规则不存在', status_code=404)

        new_name = f'{src.name}(副本)'
        # 防重名: 重复加 (副本 2)
        counter = 2
        while SceneRule.objects.filter(name=new_name).exists():
            new_name = f'{src.name}(副本{counter})'
            counter += 1

        with transaction.atomic():
            new_rule = SceneRule.objects.create(
                name=new_name,
                is_system=False,  # 副本必为 custom
                enabled=src.enabled,
                description=f'[{src.name}] 副本',
            )
            # 复制 categories (递归: 按 parent 引用重建)
            old_to_new: dict = {}
            cats = list(src.categories.select_related('parent').order_by('level', 'order'))
            for cat in cats:
                new_parent = old_to_new.get(cat.parent_id) if cat.parent_id else None
                new_cat = RuleCategory.objects.create(
                    rule=new_rule,
                    parent=new_parent,
                    name=cat.name,
                    order=cat.order,
                    allow_custom=cat.allow_custom,
                    level=cat.level,
                )
                old_to_new[cat.id] = new_cat
            # 标签绑定 (category_assignments) 不复制: 标签全局单归属
            # (UNIQUE(tag_id), 2026-09-21), 同一标签不能同时挂在原规则与副本的
            # 分类下。副本保留分类树结构与 allow_custom 配置, 标签需重新分配。
            # 复制 scenes (Q6 语义: 同一 scene 全局唯一, snapshot 时把 src 的场景
            # 转移到 new_rule, 原 rule 不再持有这些场景 — 类似 Git fork 行为)
            for sa in src.scene_assignments.all():
                # 先释放 src 的绑定
                sa.delete()
                try:
                    RuleSceneAssignment.objects.create(rule=new_rule, scene=sa.scene)
                except IntegrityError:
                    raise BizException(
                        BizCode.RULE_SCENE_CONFLICT,
                        f'场景 {sa.scene} 已被其他规则占用, 无法复制',
                        status_code=409,
                    )
        invalidate_active_cache()
        return ApiResponse.created(SceneRuleDetailSerializer(new_rule).data)

    # ----- JSON import -----
    @action(
        detail=False, methods=['post'], url_path='import',
        permission_classes=[IsAuthenticatedReadOnly, IsAdminOrReadOnly],
    )
    @_api
    def import_json(self, request: Request, **kwargs):
        """POST /rules/import/ 接收 JSON payload 创建为 custom rule (T09)."""
        payload = request.data
        if not isinstance(payload, dict):
            raise BizException(BizCode.JSON_FORMAT_INVALID, 'payload 必须为 JSON 对象', status_code=400)
        try:
            new_rule = create_rule_from_import(payload)
        except ValueError as e:
            raise BizException(BizCode.JSON_FORMAT_INVALID, str(e), status_code=400)
        except IntegrityError as e:
            raise BizException(
                BizCode.RULE_SCENE_CONFLICT,
                f'场景冲突: {e}',
                status_code=409,
            )
        invalidate_active_cache()
        return ApiResponse.created(SceneRuleDetailSerializer(new_rule).data)

    # ----- JSON export (用于下载 + 单元测试) -----
    @action(
        detail=True, methods=['get'], url_path='export',
        permission_classes=[IsAuthenticatedReadOnly, IsAdminOrReadOnly],
    )
    @_api
    def export(self, request: Request, pk=None, **kwargs):
        """GET /rules/{id}/export/ 导出完整 draft JSON."""
        try:
            src = SceneRule.objects.get(pk=pk)
        except SceneRule.DoesNotExist:
            raise BizException(BizCode.RULE_NOT_FOUND, '规则不存在', status_code=404)
        return ApiResponse.ok(export_rule_json(src))

    # ----- helpers -----
    def _check_optimistic_lock(self, request: Request, obj: SceneRule):
        expected = _parse_if_match(request)
        if expected is None:
            return  # 无 If-Match 头 → 跳过校验 (兼容未带头的客户端)
        # tz 统一: DB updated_at 是 aware UTC, parse 后 naive 需要补 tz 才能比较
        if expected.tzinfo is None:
            expected = expected.replace(tzinfo=timezone.utc)
        # 比较: 用 ISO 字符串截断到秒 (DB 精度限制)
        expected_trunc = expected.replace(microsecond=0)
        actual_trunc = obj.updated_at.replace(microsecond=0)
        if expected_trunc != actual_trunc:
            raise BizException(
                BizCode.OPTIMISTIC_LOCK_FAILED,
                f'数据已被他人修改, 请刷新后重试 (expected={expected_trunc.isoformat()}, actual={actual_trunc.isoformat()})',
                status_code=412,
                extra={
                    'expected_updated_at': expected_trunc.isoformat(),
                    'actual_updated_at': actual_trunc.isoformat(),
                },
            )

    def _paginated_response(self, data):
        resp = self.get_paginated_response(data)
        # 修复: count 从项目分页类的 pagination.total 取 (resp.data.count 恒 None → 前端 total 失真)
        pg = resp.data.get('pagination') or {}
        return ApiResponse.ok({
            'results': data,
            'count': pg.get('total'),
            'next': pg.get('has_next'),
            'previous': pg.get('has_previous'),
        })
