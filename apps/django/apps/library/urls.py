"""library URLs - 2026-07-01 简化: list/retrieve 走 StubViewSet 返空, 真实 CRUD 留给 G41"""
from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .serializers import SchoolSerializer, CompanySerializer


class _StubSchoolViewSet(viewsets.ViewSet):
    """2026-07-01 stub: 不连 School model, list 返空. G41 再加真 CRUD."""
    permission_classes = [IsAuthenticated]
    serializer_class = SchoolSerializer

    def list(self, request):
        return Response({'success': True, 'data': [], 'pagination': {'page': 1, 'pageSize': 999, 'total': 0, 'totalPages': 1, 'hasNext': False, 'hasPrevious': False}})

    def retrieve(self, request, pk=None):
        return Response({'success': True, 'data': None})


class _StubCompanyViewSet(viewsets.ViewSet):
    """2026-07-01 stub."""
    permission_classes = [IsAuthenticated]
    serializer_class = CompanySerializer

    def list(self, request):
        return Response({'success': True, 'data': [], 'pagination': {'page': 1, 'pageSize': 999, 'total': 0, 'totalPages': 1, 'hasNext': False, 'hasPrevious': False}})

    def retrieve(self, request, pk=None):
        return Response({'success': True, 'data': None})


# config/urls.py: path('library/', include(...))
# router r'' + urlpatterns = router.urls
router = DefaultRouter()
router.register(r'schools', _StubSchoolViewSet, basename='school')
router.register(r'companies', _StubCompanyViewSet, basename='company')

urlpatterns = router.urls
