"""统一规则引擎 —— 只读 API 视图（Phase 1）。

严格只读：仅 GET 列表 / 目录，无任何写端点（POST/PUT/DELETE）。
聚合逻辑在 adapters.aggregate_rules（纯 DB 读 + 映射），本层只做分页与序列化。
"""
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsSetPagination

from .adapters import aggregate_rules
from .models import UnifiedOperator, UnifiedTriggerType
from .serializers import UnifiedRuleSerializer


class RuleListView(generics.ListAPIView):
    """聚合列出全部 legacy 规则（统一呈现）。

    GET /api/v1/rule-engine/rules/?category=&trigger_type=&enabled=&source_app=
    过滤在 aggregate_rules 内完成（返回普通 list，故关闭 DRF filter_backends 以免
    对非 QuerySet 调用 .model）。
    """

    serializer_class = UnifiedRuleSerializer
    # 聚合结果是 list[UnifiedRuleDTO]，非 QuerySet；关闭 DRF 默认 filter_backends
    filter_backends = []
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        params = self.request.query_params
        filters = {}
        for key in ('category', 'trigger_type', 'enabled', 'source_app'):
            val = params.get(key)
            if val is not None:
                filters[key] = val
        return aggregate_rules(filters)


class TriggerCatalogView(APIView):
    """触发器目录：返回 UnifiedTriggerType 的 (value, label) 列表。"""

    def get(self, request):
        data = [{'value': v, 'label': l} for v, l in UnifiedTriggerType.choices]
        return Response(data)


class OperatorCatalogView(APIView):
    """运算符目录：返回 UnifiedOperator 的 (value, label) 列表（11 种）。"""

    def get(self, request):
        data = [{'value': v, 'label': l} for v, l in UnifiedOperator.choices]
        return Response(data)
