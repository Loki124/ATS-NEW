from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import School, Company
from .serializers import SchoolSerializer, CompanySerializer


class SchoolViewSet(viewsets.ReadOnlyModelViewSet):
    """院校 - 2026-06-29 stub, 真实 CRUD 留给 G41 任务"""
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    pagination_class = None

    @action(detail=False, methods=['get'])
    def industries(self, request):
        qs = Company.objects.values_list('industry', flat=True).distinct()
        return Response({'success': True, 'data': [i for i in qs if i]})
