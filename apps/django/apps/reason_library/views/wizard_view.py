"""Wizard 三步原子保存视图 (T06 / T12).

POST /rules/{id}/wizard/save/
- body: WizardSaveSerializer 校验过的 payload (name/desc/enabled + categories + scenes)
- 校验: level <= 4, scene 不与其它规则冲突, 乐观锁
- 事务内:
  1) select_for_update() 锁 scene_rule 行
  2) diff categories (按 client_id ↔ existing id)
  3) diff assignments
  4) diff rule_scene_assignment (先删后增保证 UNIQUE)
  5) 更新头部
"""
from __future__ import annotations

import logging

from rest_framework.request import Request
from rest_framework.views import APIView

from ..exceptions import ApiResponse, BizCode, BizException
from ..permissions import SystemOrAdminPermission
from ..serializers import SceneRuleDetailSerializer, WizardSaveSerializer
from ..services.active_query_service import invalidate_active_cache
from ..services.wizard_service import WizardService
from . import _api

logger = logging.getLogger(__name__)


class WizardSaveView(APIView):
    """POST /rules/{id}/wizard/save/ - 三步原子保存。"""

    permission_classes = [SystemOrAdminPermission]

    @_api
    def post(self, request: Request, pk: str, **kwargs):
        serializer = WizardSaveSerializer(data=request.data)
        if not serializer.is_valid():
            raise BizException(
                BizCode.VALIDATION_FAILED, '参数校验失败',
                status_code=400, extra={'errors': serializer.errors},
            )
        payload = serializer.validated_data

        service = WizardService()
        updated_rule = service.save(
            rule_id=pk,
            payload=payload,
            user=request.user,
        )
        invalidate_active_cache()
        return ApiResponse.ok(SceneRuleDetailSerializer(updated_rule).data)
