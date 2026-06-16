"""Audit Views (DRF) - PRD v4 §4.4, §13"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsSuperAdmin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """审计日志 ViewSet - 只读（仅超管可访问）"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['action', 'entity', 'entity_id', 'user']
    search_fields = ['entity', 'entity_id', 'field']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('user')
