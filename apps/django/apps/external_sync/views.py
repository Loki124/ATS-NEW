"""external_sync views — 2026-06-29 stub."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class CompanySyncViewSet(viewsets.ViewSet):
    """外部公司同步 - 真实 G40 实现留给后续."""
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def list(self, request):
        return Response({'success': True, 'data': [], 'pagination': {'total': 0}})

    @action(detail=False, methods=['get'])
    def syncs(self, request):
        """GET /external-sync/syncs 同步历史"""
        return Response({'success': True, 'data': [], 'pagination': {'total': 0}})

    @action(detail=False, methods=['post'], url_path=r'sync/(?P<company_id>[^/.]+)/(?P<system>[^/.]+)')
    def trigger_sync(self, request, company_id=None, system=None):
        """POST /external-sync/sync/{companyId}/{system}"""
        return Response({
            'success': False,
            'message': f'G40 外部同步 ({system}) 暂未实现, company={company_id}',
        }, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        return Response({
            'success': False,
            'message': 'G40 重试功能开发中',
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
