"""mou URLs - 2026-07-01 stub for permissions-v2/* (含 5 个 endpoint + scopes)"""
from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from django.urls import path
from rest_framework.permissions import IsAuthenticated

from .views import (
    MouAgreementViewSet, MouContainerViewSet,
    MutualExclusionGroupViewSet, AutomationRuleViewSet,
)


class MouAgreementViewSetWithScopes(MouAgreementViewSet):
    """加 scopes action"""
    @action(detail=True, methods=['get', 'put'], url_path='scopes')
    def scopes(self, request, pk=None):
        """GET  /mou/{id}/scopes — 返 MOU 的 scopes list
        PUT  /mou/{id}/scopes — 更新 scopes
        """
        instance = self.get_object()
        if request.method == 'GET':
            return Response({'success': True, 'data': instance.scopes or []})
        # PUT
        scopes = request.data.get('scopes', [])
        if not isinstance(scopes, list):
            return Response({'success': False, 'code': 'validation_error', 'message': 'scopes 必须是 list'}, status=400)
        instance.scopes = scopes
        instance.save(update_fields=['scopes', 'updated_at'])
        return Response({'success': True, 'data': instance.scopes})


router = DefaultRouter()
router.register(r'mou', MouAgreementViewSetWithScopes, basename='mou')
router.register(r'containers', MouContainerViewSet, basename='mou-container')
router.register(r'mutual-exclusion-groups', MutualExclusionGroupViewSet, basename='mou-mutex')
router.register(r'automation-rules', AutomationRuleViewSet, basename='mou-automation')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_logs_stub(request):
    return Response({
        'success': True,
        'data': [],
        'pagination': {'page': 1, 'pageSize': 20, 'total': 0, 'totalPages': 1, 'hasNext': False, 'hasPrevious': False}
    })


urlpatterns = router.urls + [
    path('audit-logs', audit_logs_stub, name='mou-audit-logs'),
    path('audit-logs/', audit_logs_stub),
]
