from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions_v2 import V2Permission

from .models import School, Company
from .serializers import SchoolSerializer, CompanySerializer


class SchoolViewSet(viewsets.ReadOnlyModelViewSet):
    """院校 - 2026-06-29 stub, 真实 CRUD 留给 G41 任务"""
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
    pagination_class = None  # FE 不分页, 简单 list 即可

    @action(detail=False, methods=['get'])
    def provinces(self, request):
        """返所有不重复省份"""
        qs = School.objects.values_list('province', flat=True).distinct()
        return Response({'success': True, 'data': [p for p in qs if p]})


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    """公司 - 2026-06-29 stub"""
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
    pagination_class = None

    @action(detail=False, methods=['get'])
    def industries(self, request):
        qs = Company.objects.values_list('industry', flat=True).distinct()
        return Response({'success': True, 'data': [i for i in qs if i]})
