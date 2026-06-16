"""Automation Views"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import HasProcessPermission

from .models import AutomationLog, AutomationRule
from .serializers import (
    AutomationLogSerializer,
    AutomationRuleSerializer,
    AutomationTriggerRequestSerializer,
)
from .services import AutomationEngine, TriggerContext


class AutomationRuleViewSet(AuditMixin, viewsets.ModelViewSet):
    """自动化规则 ViewSet"""
    queryset = AutomationRule.objects.all()
    serializer_class = AutomationRuleSerializer
    permission_classes = [IsAuthenticated, HasProcessPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['process', 'stage', 'trigger_type', 'action_type', 'enabled', 'priority']
    search_fields = ['name']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-enabled', 'priority', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('process', 'stage', 'next_stage', 'created_by', 'updated_by')

    def perform_destroy(self, instance):
        instance.soft_delete()

    @extend_schema(summary='切换启用状态')
    @action(detail=True, methods=['post'], url_path='toggle')
    def toggle(self, request, pk=None):
        instance = self.get_object()
        instance.enabled = not instance.enabled
        instance.save(update_fields=['enabled', 'updated_at'])
        return Response({
            'success': True,
            'data': {'id': instance.id, 'enabled': instance.enabled},
        })

    @extend_schema(summary='查看规则执行日志')
    @action(detail=True, methods=['get'], url_path='logs')
    def logs(self, request, pk=None):
        instance = self.get_object()
        qs = AutomationLog.objects.filter(rule=instance).order_by('-trigger_time')[:200]
        serializer = AutomationLogSerializer(qs, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })

    @extend_schema(summary='统计 - 失败率')
    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        instance = self.get_object()
        logs = AutomationLog.objects.filter(rule=instance)
        total = logs.count()
        matched = logs.filter(evaluate_result='MATCHED').count()
        unmatched = logs.filter(evaluate_result='UNMATCHED').count()
        error = logs.filter(evaluate_result='ERROR').count()
        recent = logs.order_by('-trigger_time')[:100]
        recent_failed = sum(1 for l in recent if l.evaluate_result == 'ERROR' or l.error_message)
        recent_failure_rate = recent_failed / max(1, len(recent))
        return Response({
            'success': True,
            'data': {
                'rule_id': instance.id,
                'rule_name': instance.name,
                'total_executions': total,
                'matched': matched,
                'unmatched': unmatched,
                'error': error,
                'recent_100_failure_rate': round(recent_failure_rate, 4),
                'circuit_open': recent_failure_rate > (instance.failure_rate_threshold or 0.5),
            }
        })


class AutomationTriggerView(viewsets.ViewSet):
    """手动触发自动化引擎（用于测试 / 重放）"""
    permission_classes = [IsAuthenticated, HasProcessPermission]
    pagination_class = None

    @extend_schema(
        summary='手动触发',
        request=AutomationTriggerRequestSerializer,
    )
    def create(self, request):
        serializer = AutomationTriggerRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        context = TriggerContext(
            trigger_type=serializer.validated_data['trigger_type'],
            candidate_id=serializer.validated_data['candidate_id'],
            application_id=serializer.validated_data.get('application_id') or None,
            stage_id=serializer.validated_data.get('stage_id') or None,
            extra=serializer.validated_data.get('extra', {}),
        )

        engine = AutomationEngine(context, actor=request.user)
        results = engine.run()

        return Response({
            'success': True,
            'data': [
                {
                    'rule_id': r.rule_id,
                    'rule_name': r.rule_name,
                    'matched': r.matched,
                    'action_taken': r.action_taken,
                    'skip_reason': r.skip_reason,
                    'error_message': r.error_message,
                    'execution_ms': r.execution_ms,
                }
                for r in results
            ]
        }, status=status.HTTP_200_OK)


class AutomationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """自动化执行日志"""
    queryset = AutomationLog.objects.all()
    serializer_class = AutomationLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['rule', 'candidate_id', 'evaluate_result']
    ordering_fields = ['trigger_time']
    ordering = ['-trigger_time']
