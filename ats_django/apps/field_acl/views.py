"""Field ACL Views (DRF) - PRD v4 §4.4"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsSuperAdmin

from .models import FieldACL
from .serializers import FieldACLSerializer


class FieldACLViewSet(AuditMixin, viewsets.ModelViewSet):
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
