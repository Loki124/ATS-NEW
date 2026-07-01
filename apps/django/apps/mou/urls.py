"""mou URLs - 2026-07-01 stub for permissions-v2/* (含 5 个 ViewSet)"""
from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import (
    MouAgreementViewSet, MouContainerViewSet,
    MutualExclusionGroupViewSet, AutomationRuleViewSet,
)

# config/urls.py: path('permissions-v2/', include('apps.mou.urls'))
# 这里 4 个 ViewSet + 1 个 stub audit-logs
router = DefaultRouter()
router.register(r'mou', MouAgreementViewSet, basename='mou')
router.register(r'containers', MouContainerViewSet, basename='mou-container')
router.register(r'mutual-exclusion-groups', MutualExclusionGroupViewSet, basename='mou-mutex')
router.register(r'automation-rules', AutomationRuleViewSet, basename='mou-automation')

# audit-logs stub: 走 audit app, 简单 stub 一下 (MouAuditLogSerializer 之前已定义)
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_logs_stub(request):
    """GET /permissions-v2/audit-logs — stub (实际走 audit app)"""
    return Response({
        'success': True,
        'data': [],
        'pagination': {'page': 1, 'pageSize': 20, 'total': 0, 'totalPages': 1, 'hasNext': False, 'hasPrevious': False}
    })


urlpatterns = router.urls + [
    path('audit-logs', audit_logs_stub, name='mou-audit-logs'),
    path('audit-logs/', audit_logs_stub),
]
