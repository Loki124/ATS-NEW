"""data views — 2026-06-29 stub.

FE api (data.ts):
  GET  /api/v1/data/kpi/
  GET  /api/v1/data/subscriptions/
  POST /api/v1/data/subscriptions/
  DELETE /api/v1/data/subscriptions/{id}
  GET  /api/v1/data/export/{resource}   (blob)

实际 KPI/export 应走 analytics/ — 此 stub 让 /data/* 不 404.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class DataViewSet(viewsets.ViewSet):
    """数据中心 stub - 真实 G35 任务实现."""
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def list(self, request):
        return Response({
            'success': True,
            'data': {
                'totalCandidates': 0, 'activeDemands': 0, 'openPositions': 0,
                'ongoingInterviews': 0, 'sentOffers': 0, 'pendingOnboardings': 0,
                'generatedAt': '2026-06-29T00:00:00Z',
            }
        })

    @action(detail=False, methods=['get'])
    def kpi(self, request):
        """GET /data/kpi/"""
        return self.list(request)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        return Response({'success': True, 'data': [], 'pagination': {'total': 0}})

    @action(detail=False, methods=['post'])
    def create_subscription(self, request):
        return Response({
            'success': False,
            'message': 'G35 订阅功能开发中',
        }, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['delete'])
    def destroy_subscription(self, request, pk=None):
        return Response({'success': True})
