
"""Field ACL Views (DRF) - PRD v4 §4.4"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.common.viewsets import EnvelopeAuditModelViewSet
from apps.core.permissions import IsSuperAdmin

from .models import FieldACL
from .serializers import (
    FieldAclRuleSerializer,
    FieldACLSerializer,
    permission_to_action,
)


class FieldACLViewSet(EnvelopeAuditModelViewSet):
    """字段级 ACL ViewSet - 仅超管可操作"""
    queryset = FieldACL.objects.all()
    serializer_class = FieldACLSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['entity', 'field', 'role_code', 'permission']
    search_fields = ['entity', 'field', 'role_code']
    ordering_fields = ['entity', 'field', 'role_code']
    ordering = ['entity', 'field', 'role_code']

    @action(detail=False, methods=['get'], url_path='matrix')
    def matrix(self, request):
        """GET /field-acl/matrix - 返回前端 `FieldAclMatrix` 权限矩阵。

        把所有 FieldACL 行聚合成嵌套结构:
            { resource: { field: { roleCode: action } } }
        其中 resource ← entity, action ← permission (READ→VIEW / MASK→MASK / NONE→HIDE)。
        """
        matrix_dict: dict[str, dict[str, dict[str, str]]] = {}

        rows = FieldACL.objects.all().values_list(
            'entity', 'field', 'role_code', 'permission',
        )
        for entity, field_name, role_code, permission in rows:
            resource_bucket = matrix_dict.setdefault(entity, {})
            field_bucket = resource_bucket.setdefault(field_name, {})
            field_bucket[role_code] = permission_to_action(permission)

        return Response({'success': True, 'data': matrix_dict})

    @action(detail=False, methods=['get'], url_path='rules')
    def rules(self, request):
        """GET /field-acl/rules - 返回前端 `FieldAclRule[]` 规则列表。

        可选查询参数:
            resource: 过滤 entity (前端命名 → 模型命名)
            roleCode: 过滤 role_code
        """
        queryset = FieldACL.objects.all()

        resource = request.query_params.get('resource')
        if resource:
            queryset = queryset.filter(entity=resource)

        role_code = request.query_params.get('roleCode')
        if role_code:
            queryset = queryset.filter(role_code=role_code)

        serializer = FieldAclRuleSerializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='audit')
    def audit(self, request):
        """GET /field-acl/audit - ACL 访问审计日志。

        读取 FieldAclAccessLog 表 (由 FieldAclSerializerMixin 在 HTTP 序列化时
        按 (request, entity) 去重埋点写入)。可选查询参数: entity / username。
        返回最近 500 条 (按时间倒序)。
        """
        from .models import FieldAclAccessLog

        queryset = FieldAclAccessLog.objects.all()

        entity = request.query_params.get('entity')
        if entity:
            queryset = queryset.filter(entity=entity)

        username = request.query_params.get('username')
        if username:
            queryset = queryset.filter(username__icontains=username)

        rows = [
            {
                'id': r.id,
                'entity': r.entity,
                'user_id': r.user_id,
                'username': r.username,
                'role_codes': r.role_codes,
                'masked_fields': r.masked_fields,
                'hidden_fields': r.hidden_fields,
                'request_path': r.request_path,
                'client_ip': r.client_ip,
                'created_at': r.created_at.isoformat() if r.created_at else None,
            }
            for r in queryset.order_by('-created_at')[:500]
        ]
        return Response({'success': True, 'data': rows})
