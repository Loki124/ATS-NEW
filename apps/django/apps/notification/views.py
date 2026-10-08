"""Notification Views (DRF) - PRD v4 §14.10"""
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.views import EnvelopeWriteMixin
from apps.core.permissions import IsHROrAbove
from apps.core.permissions_v2 import V2Permission

from .models import NotificationLog, NotificationTemplate
from .serializers import (
    NotificationLogListSerializer,
    NotificationLogSerializer,
    NotificationMarkReadSerializer,
    NotificationTemplateSerializer,
)


class NotificationTemplateViewSet(EnvelopeWriteMixin, AuditMixin, viewsets.ModelViewSet):
    """通知模板 ViewSet"""
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['event', 'is_active']
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'created_at']
    ordering = ['code']


class NotificationLogViewSet(AuditMixin, viewsets.ReadOnlyModelViewSet):
    """通知日志 ViewSet - 只读（用户只能看自己的）"""
    queryset = NotificationLog.objects.all()
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
    # 2026-10-08: mark_read 只作用于 recipient=当前用户 的通知, 不存在"给别人授权"
    #   的概念, 故声明为自助操作豁免写守卫。用集合而非开关, 便于脚本扫描审计。
    v2_self_service_actions = {'mark_read'}
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['event', 'channel', 'recipient']
    ordering_fields = ['created_at', 'sent_at', 'read_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationLogListSerializer
        return NotificationLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 普通用户只能看自己的
        if not self.request.user.is_staff:
            qs = qs.filter(recipient=self.request.user)
        return qs.select_related('template', 'recipient')

    @action(detail=False, methods=['get'], url_path='unread')
    def unread(self, request):
        """未读通知"""
        qs = self.get_queryset().filter(read_at__isnull=True)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = NotificationLogListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = NotificationLogListSerializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """未读数量"""
        count = self.get_queryset().filter(read_at__isnull=True).count()
        return Response({'success': True, 'data': {'count': count}})

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        """标记已读"""
        serializer = NotificationMarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        qs = self.get_queryset().filter(read_at__isnull=True)
        if data.get('mark_all'):
            count = qs.update(read_at=timezone.now())
        else:
            ids = data.get('notification_ids', [])
            if not ids:
                return Response({'success': False, 'message': '需提供 notification_ids 或 mark_all=true'}, status=status.HTTP_400_BAD_REQUEST)
            count = qs.filter(id__in=ids).update(read_at=timezone.now())
        return Response({'success': True, 'data': {'updated': count}})
