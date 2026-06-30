"""scraped_resume views — 2026-06-29 花无缺 stub (无 model)."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class ScrapedResumeViewSet(viewsets.ViewSet):
    """无 model 桩 — FE 接口可调, 返 501 让 UI 知道 "未实现"."""
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def list(self, request):
        return Response({'success': True, 'data': [], 'pagination': {'total': 0}})

    def retrieve(self, request, pk=None):
        return Response({
            'success': False,
            'message': '简历抓取详情未实现 (G30)',
        }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def scrape(self, request):
        return Response({
            'success': False,
            'code': 'not_implemented',
            'message': 'G30 RPA 抓取功能开发中',
        }, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['post'])
    def import_to(self, request, pk=None):
        return Response({
            'success': False,
            'message': '导入功能开发中',
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
