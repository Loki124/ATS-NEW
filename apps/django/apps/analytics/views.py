"""Analytics Views (DRF) - PRD v4 §14.9"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsHROrAbove
from apps.core.permissions_v2 import V2Permission

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
    permission_classes = [IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report_type', 'generated_by']
    search_fields = ['name']
    ordering_fields = ['generated_at', 'created_at']
    ordering = ['-generated_at']


class ExportTaskViewSet(AuditMixin, viewsets.ModelViewSet):
    """数据导出任务 ViewSet"""
    queryset = ExportTask.objects.all()
    permission_classes = [IsHROrAbove]
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


# ============================================================
# 数据看板 KPI (G35 数据中心)  ← 2026-06-17
# FE 调 /api/v1/data/kpi, 之前 302 → admin (路由没挂)
# 返回 DashboardKpi TS interface 期望的精确 shape.
# ============================================================
class KpiViewSet(viewsets.ViewSet):
    """数据看板 KPI 汇总 — HR 看板上方的 6 个数字.

    字段定义来自 web/app/src/api/data.ts:DashboardKpi interface.
    全部包 try/except (含 queryset 构造): 任何 model 字段名漂移都不会 500, 顶多返 0.
    """
    permission_classes = [V2Permission]

    def list(self, request):
        from django.utils import timezone

        def _safe_count(builder):
            """builder: 无参 callable, 返回 QuerySet; 在 callable 内做 .filter() 让异常落入 try."""
            try:
                return builder().count()
            except Exception:
                return 0

        # 延迟 import: 任一 model 字段漂移都不会 500 (因为在 builder 内)
        def _candidate_total():
            from apps.candidate.models import Candidate
            return Candidate.objects.filter(deleted_at__isnull=True)

        def _active_demands():
            from apps.demand.models import Demand
            # Demand.state 枚举 (apps/demand/models.py:13): DRAFT/PENDING/REJECTED/APPROVED/RECRUITING/PAUSED/COMPLETED/CANCELLED
            return Demand.objects.filter(deleted_at__isnull=True, state__in=('RECRUITING', 'APPROVED'))

        def _open_positions():
            from apps.position.models import Position
            # Position.state: DRAFT/PENDING_PUBLISH/PUBLISHED/RECRUITING/PAUSED/UNPUBLISHED/CLOSED
            return Position.objects.filter(deleted_at__isnull=True, state__in=('RECRUITING', 'PUBLISHED'))

        def _ongoing_interviews():
            from apps.interview.models import Interview
            # Interview.status: SCHEDULED/IN_PROGRESS/COMPLETED/CANCELLED/NO_SHOW
            return Interview.objects.filter(deleted_at__isnull=True, status__in=('SCHEDULED', 'IN_PROGRESS'))

        def _sent_offers():
            from apps.offer.models import Offer
            # Offer.state: DRAFT/PENDING_APPROVAL/REJECTED/PENDING_SEND/SENT/NEGOTIATING/ACCEPTED/REJECTED_BY_CANDIDATE/WITHDRAWN/PENDING_ONBOARDING
            return Offer.objects.filter(deleted_at__isnull=True, state__in=('SENT', 'NEGOTIATING', 'ACCEPTED', 'PENDING_ONBOARDING'))

        def _pending_onboardings():
            from apps.onboarding.models import Onboarding
            # Onboarding.state: PENDING/PREPARING/DELAYED/COMPLETED/PROBATION/REGULARIZED/RESIGNED_DURING_PROBATION
            return Onboarding.objects.filter(deleted_at__isnull=True, state__in=('PENDING', 'PREPARING', 'DELAYED'))

        return Response({
            'success': True,
            'data': {
                'totalCandidates':   _safe_count(_candidate_total),
                'activeDemands':     _safe_count(_active_demands),
                'openPositions':     _safe_count(_open_positions),
                'ongoingInterviews': _safe_count(_ongoing_interviews),
                'sentOffers':        _safe_count(_sent_offers),
                'pendingOnboardings': _safe_count(_pending_onboardings),
                'generatedAt':       timezone.now().isoformat(),
            },
        })

