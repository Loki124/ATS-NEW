"""数据权限规则 ViewSet (管理面)。

仅超管可配置。enforcement 由 scope_resolver / FieldAclService 消费本表, 不在本视图内。
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsSuperAdmin

from .models import (
    DataPermissionRule,
    DimensionType, RuleLevel, RowScopeType, ColumnPermission,
)
from .serializers import DataPermissionRuleSerializer


class DataPermissionRuleViewSet(viewsets.ModelViewSet):
    queryset = DataPermissionRule.objects.all()
    serializer_class = DataPermissionRuleSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['dimension_type', 'dimension_value', 'level']
    ordering_fields = ['priority', 'created_at']
    ordering = ['-priority', '-created_at']

    @action(detail=False, methods=['get'], url_path='options')
    def options(self, request):
        """GET /data-permissions/options/ — 前端配置表单所需的枚举选项。"""
        return Response({
            'success': True,
            'data': {
                'dimension_types': [{'value': c, 'label': l} for c, l in DimensionType.choices],
                'levels': [{'value': c, 'label': l} for c, l in RuleLevel.choices],
                'row_scopes': [{'value': c, 'label': l} for c, l in RowScopeType.choices],
                'column_permissions': [{'value': c, 'label': l} for c, l in ColumnPermission.choices],
            },
        })
