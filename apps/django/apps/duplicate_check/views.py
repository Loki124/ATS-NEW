"""duplicate_check views — 2026-06-29 stub."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions_v2 import V2Permission


class DuplicateCheckViewSet(viewsets.ViewSet):
    """简历查重 - 真实 G45 实现留给后续."""
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]

    @action(detail=False, methods=['post'])
    def check(self, request):
        """POST /duplicate-check/check"""
        # 真实实现: 比较 phone/email/name
        return Response({
            'success': True,
            'data': [],  # 返空 candidates list (无重复)
            'message': 'G45 查重 stub, 暂不实际比较',
        })

    @action(detail=False, methods=['post'])
    def ocr_parse(self, request):
        """POST /duplicate-check/ocr-parse"""
        return Response({
            'success': False,
            'message': 'G45 OCR 解析依赖 affinda, 暂未实现',
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
