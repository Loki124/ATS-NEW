"""Analytics Views (DRF) - PRD v4 §14.9"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsHROrAbove

from .models import ExportTask, ReportSnapshot
from .serializers import (
    ExportTaskCreateSerializer,
    ExportTaskSerializer,
    ReportSnapshotSerializer,
)


class ReportSnapshotViewSet(AuditMixin, viewsets.ModelViewSet):
    """报表快照 ViewSet"""
    queryset = ReportSnapshot.objects.all()
    serializer_class = ReportSnapshotSerializer
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report_type', 'generated_by']
    search_fields = ['name']
    ordering_fields = ['generated_at', 'created_at']
    ordering = ['-generated_at']


class ExportTaskViewSet(AuditMixin, viewsets.ModelViewSet):
    """数据导出任务 ViewSet"""
    queryset = ExportTask.objects.all()
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['entity', 'format', 'status', 'requested_by']
    ordering_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ExportTaskCreateSerializer
        return ExportTaskSerializer

    @action(detail=True, methods=['post'], url_path='run')
    def run_task(self, request, pk=None):
        """触发执行导出任务（实际执行交给 Celery）"""
        instance = self.get_object()
        from .tasks import run_export_task
        run_export_task.delay(instance.id)
        instance.status = 'PENDING'
        instance.save(update_fields=['status'])
        return Response({'success': True, 'message': '导出任务已加入队列'})

    @action(detail=False, methods=['get'], url_path='dashboard-summary')
    def dashboard_summary(self, request):
        """HR 个人看板汇总数据（简版）"""
        from django.db.models import Count
        from apps.candidate.models import Candidate
        from apps.application.models import Application
        from apps.demand.models import Demand
        from apps.position.models import Position

        return Response({
            'success': True,
            'data': {
                'candidates_total': Candidate.objects.filter(deleted_at__isnull=True).count(),
                'applications_total': Application.objects.filter(deleted_at__isnull=True).count(),
                'demands_total': Demand.objects.filter(deleted_at__isnull=True).count(),
                'positions_open': Position.objects.filter(deleted_at__isnull=True, state='RECRUITING').count(),
                'applications_by_state': dict(
                    Application.objects.filter(deleted_at__isnull=True)
                    .values_list('state').annotate(count=Count('id'))
                ),
            }
        })
