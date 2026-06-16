"""Time Limit Views"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.candidate.models import Candidate
from apps.common.exceptions import NotFound
from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import HasProcessPermission
from apps.process.models import ProcessStageLink

from .models import TimeLimitRule
from .serializers import (
    TimeLimitCalculateRequestSerializer,
    TimeLimitRuleSerializer,
)
from .services import (
    TimeLimitCalcResult,
    calc_time_limit,
    compute_locked_until,
)


class TimeLimitRuleViewSet(AuditMixin, viewsets.ModelViewSet):
    """阶段限时规则 ViewSet"""
    queryset = TimeLimitRule.objects.all()
    serializer_class = TimeLimitRuleSerializer
    permission_classes = [IsAuthenticated, HasProcessPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['link', 'enabled', 'effective_scope', 'link__process']
    search_fields = ['rule_name']
    ordering_fields = ['priority', 'created_at', 'lock_duration']
    ordering = ['link', 'priority']

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('link', 'link__stage', 'link__process')

    def perform_destroy(self, instance):
        from django.utils import timezone
        if hasattr(instance, 'deleted_at'):
            instance.deleted_at = timezone.now()
        instance.save()

    @extend_schema(
        summary='计算候选人阶段限时',
        request=TimeLimitCalculateRequestSerializer,
    )
    @action(detail=False, methods=['post'], url_path='calculate')
    def calculate(self, request):
        serializer = TimeLimitCalculateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            link = ProcessStageLink.objects.get(
                id=serializer.validated_data['link_id'],
                deleted_at__isnull=True,
            )
            candidate = Candidate.objects.get(
                id=serializer.validated_data['candidate_id'],
                deleted_at__isnull=True,
            )
        except (ProcessStageLink.DoesNotExist, Candidate.DoesNotExist) as e:
            raise NotFound(str(e))

        result = calc_time_limit(
            link,
            candidate,
            interviewer_count=serializer.validated_data.get('interviewer_count', 1),
            process_version=serializer.validated_data.get('workflow_version'),
        )

        if result.matched and result.total_lock_days > 0:
            from django.utils import timezone
            result.locked_until = compute_locked_until(
                timezone.now(),
                result.total_lock_days,
            ).isoformat() if compute_locked_until(timezone.now(), result.total_lock_days) else None

        return Response({
            'success': True,
            'data': {
                'matched': result.matched,
                'rule_id': result.rule_id,
                'rule_name': result.rule_name,
                'base_lock_days': result.base_lock_days,
                'extension_days': result.extension_days,
                'extra_interviewer_days': result.extra_interviewer_days,
                'total_lock_days': result.total_lock_days,
                'effective_scope': result.effective_scope,
                'locked_until': result.locked_until,
            }
        })

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
