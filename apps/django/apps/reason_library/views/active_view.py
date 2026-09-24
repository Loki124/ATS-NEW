"""Active 业务态查询 (T08) — 业务态走 active endpoint 取当前场景生效规则。

GET /active/?scene=xxx
- Q3: 显式引用 > 系统预置; 多条显式引用时取最新 updated_at
- Redis cache key: rl:scene:{scene_name}, TTL=300s
- 缓存失效: rule save / delete / wizard / scene PUT 时由 service 触发
- AllowAny (前端无需鉴权)
"""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..exceptions import ApiResponse, BizCode, BizException
from ..models import SCENE_OPTIONS
from ..services.active_query_service import get_active_rule
from . import _api

logger = logging.getLogger(__name__)


class ActiveRuleView(APIView):
    """GET /active/?scene=xxx  返回当前场景生效的规则 (含完整树)。"""

    permission_classes = [AllowAny]

    @_api
    def get(self, request: Request, **kwargs):
        scene = request.query_params.get('scene') or request.GET.get('scene')
        if not scene:
            raise BizException(BizCode.VALIDATION_FAILED, '缺少 scene 参数', status_code=400)
        if scene not in SCENE_OPTIONS:
            raise BizException(BizCode.VALIDATION_FAILED, f'非法 scene: {scene}', status_code=400)
        # 招聘类型维度 (2026-09-24): 业务流当前未真正传类型 (前端 system.ts 注释),
        # 不传时退化为纯按场景兜底; 一旦接入即可精确按 (场景,类型) 取规则。
        recruit_type = request.query_params.get('recruitType') or request.GET.get('recruitType') or None

        rule = get_active_rule(scene, recruit_type)
        if rule is None:
            return ApiResponse.ok(None, message='该场景当前无生效规则')
        # 业务态只取 enabled 规则 (Q-A5: 不按 user.role 区分)
        if not rule.enabled:
            return ApiResponse.ok(None, message='该场景当前规则已停用')
        # 复用 detail 序列化器, 输出完整树
        from ..serializers import SceneRuleDetailSerializer
        return ApiResponse.ok(SceneRuleDetailSerializer(rule).data)
