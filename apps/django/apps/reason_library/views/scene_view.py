"""Scene 视图 (T07 / T12) - GET 全场景绑定, PUT 全量替换。

端点:
- GET  /scenes/   →  6 个场景 × 2 个招聘类型 的当前绑定
                      items: [{scene, recruitType, ruleId, ruleName}]
- PUT  /scenes/   →  整表替换: items: [{scene, recruitType, ruleId}]

Q6 强制: 同一 (场景, 类型) 组合仅可使用一个规则; 删除规则时 CASCADE 释放占用;
启用/停用规则时校验: 被引用的规则不可停用。
"""
from __future__ import annotations

import logging

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..exceptions import ApiResponse, BizCode, BizException
from ..models import (
    RECRUIT_TYPES, RuleSceneAssignment, SCENE_OPTIONS, SceneRule,
)
from ..permissions import IsAdminOrReadOnly, IsAuthenticatedReadOnly
from ..serializers import SceneBulkUpdateSerializer
from ..services.active_query_service import invalidate_active_cache
from . import _api

logger = logging.getLogger(__name__)


class SceneView(APIView):
    """GET /scenes/  列出所有 (场景 × 类型) 组合的当前绑定;  PUT /scenes/ 全量替换绑定。"""

    permission_classes = [IsAuthenticatedReadOnly, IsAdminOrReadOnly]

    @_api
    def get(self, request, *args, **kwargs):
        # 列出所有 (场景 × 类型) 组合的当前绑定, 未绑定的 ruleId = null
        # 排除预置默认规则: 它覆盖全部场景×类型作系统兜底, 不参与"场景占用"展示,
        # 否则其它规则编辑时会把默认规则当成"已占用"而误报冲突。
        assignments = (
            RuleSceneAssignment.objects
            .exclude(rule__is_system=True, rule__name='预置默认规则')
            .select_related('rule')
            .all()
        )
        mapping = {(a.scene, a.recruit_type): a.rule for a in assignments}
        result = []
        for scene in SCENE_OPTIONS:
            for rt in RECRUIT_TYPES:
                rule = mapping.get((scene, rt))
                result.append({
                    'scene': scene,
                    'recruitType': rt,
                    'ruleId': rule.id if rule else None,
                    'ruleName': rule.name if rule else None,
                })
        return ApiResponse.ok({'items': result})

    @_api
    def put(self, request, *args, **kwargs):
        """全量替换绑定 (按 scene+type 组合)。"""
        serializer = SceneBulkUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            raise BizException(
                BizCode.VALIDATION_FAILED, '参数校验失败',
                status_code=400, extra={'errors': serializer.errors},
            )
        items = serializer.validated_data['items']

        # 校验 rule_id 都存在
        rule_ids = {it['rule_id'] for it in items if it.get('rule_id')}
        existing = SceneRule.objects.filter(pk__in=rule_ids).values_list('id', flat=True)
        missing = rule_ids - set(existing)
        if missing:
            raise BizException(
                BizCode.VALIDATION_FAILED,
                f'rule_id 不存在: {sorted(missing)}',
                status_code=400,
            )

        try:
            with transaction.atomic():
                # 先清空, 再批量创建 (DB UNIQUE(scene, recruit_type) 兜底)
                RuleSceneAssignment.objects.all().delete()
                for it in items:
                    rule_id = it.get('rule_id')
                    if not rule_id:
                        continue  # 允许 (scene, type) 解绑
                    RuleSceneAssignment.objects.create(
                        scene=it['scene'],
                        recruit_type=it.get('recruit_type') or 'social',
                        rule_id=rule_id,
                    )
        except IntegrityError as e:
            raise BizException(
                BizCode.RULE_SCENE_CONFLICT,
                f'场景/类型组合绑定冲突 (DB UNIQUE 兜底触发): {e}',
                status_code=409,
            )

        invalidate_active_cache()
        # 返回最新视图
        return self.get(request, *args, **kwargs)
