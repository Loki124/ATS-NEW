"""GDPR Views (DRF) - PRD v4 §4.4"""
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import ValidationError
from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsSuperAdmin

from .models import GDPRRequest
from .serializers import (
    GDPRProcessSerializer,
    GDPRRequestCreateSerializer,
    GDPRRequestSerializer,
)


class GDPRRequestViewSet(AuditMixin, viewsets.ModelViewSet):
    """GDPR 请求 ViewSet"""
    queryset = GDPRRequest.objects.all()
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['request_type', 'status', 'candidate']
    search_fields = ['candidate__name', 'submitted_email']
    ordering_fields = ['created_at', 'processed_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ('create',):
            return GDPRRequestCreateSerializer
        return GDPRRequestSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('candidate', 'processed_by')

    @action(detail=True, methods=['post'], url_path='process')
    def process(self, request, pk=None):
        """处理 GDPR 请求（approve/reject）"""
        instance = self.get_object()
        if instance.status != 'PENDING':
            raise ValidationError(f'当前状态 {instance.status} 不可处理')
        serializer = GDPRProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']
        instance.status = 'PROCESSING'
        instance.processed_by = request.user
        if action_name == 'approve':
            instance.status = 'COMPLETED'
            instance.result = serializer.validated_data.get('result', '数据已处理')
        else:
            instance.status = 'REJECTED'
            instance.reject_reason = serializer.validated_data.get('reject_reason', '')
        instance.processed_at = timezone.now()
        instance.save()
        out = GDPRRequestSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})
