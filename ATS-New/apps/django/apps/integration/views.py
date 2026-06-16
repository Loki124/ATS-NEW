"""Integration Views (DRF) - PRD v4 §14.4"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsSuperAdmin

from .models import IntegrationConfig, IntegrationSyncLog
from .serializers import (
    IntegrationConfigSerializer,
    IntegrationSyncLogSerializer,
)


class IntegrationConfigViewSet(AuditMixin, viewsets.ModelViewSet):
    """集成配置 ViewSet - 仅超管可操作"""
    queryset = IntegrationConfig.objects.all()
    serializer_class = IntegrationConfigSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['type', 'name']

    @action(detail=True, methods=['post'], url_path='test')
    def test(self, request, pk=None):
        """测试集成连接"""
        instance = self.get_object()
        try:
            from .services import (
                send_email, send_sms, send_wecom_message, sync_candidate_from_moka,
            )
            if instance.type == 'EMAIL':
                ok = send_email(
                    to=request.user.email or 'test@example.com',
                    subject='[集成测试]',
                    body='集成测试邮件',
                )
            elif instance.type == 'SMS':
                ok = send_sms(phone='13800138000', content='测试短信')
            elif instance.type == 'WECOM':
                ok = send_wecom_message(user_id='', content='测试消息')
            elif instance.type == 'MOKA':
                result = sync_candidate_from_moka(moka_id='test')
                ok = result.get('success', False)
            else:
                ok = False
            return Response({
                'success': True,
                'data': {'ok': ok, 'message': '测试完成'},
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'测试失败: {e}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IntegrationSyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """集成同步日志 ViewSet - 只读"""
    queryset = IntegrationSyncLog.objects.all()
    serializer_class = IntegrationSyncLogSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['config', 'sync_type', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('config')
