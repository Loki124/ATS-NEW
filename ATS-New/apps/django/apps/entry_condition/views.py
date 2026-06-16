"""Entry Condition Views (DRF)

API:
- list/retrieve/create/update/destroy: 规则 CRUD
- evaluate: 对候选人评估指定 link 的进入条件
- logs: 查看评估日志
- reorder: 重新排序规则的 rule_seq
- toggle: 启用/停用规则
"""
from __future__ import annotations

import logging
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.candidate.models import Candidate
from apps.common.exceptions import NotFound, PermissionDenied, ValidationError
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import HasProcessPermission
from apps.process.models import ProcessStageLink

from .models import EntryConditionLog, EntryConditionRule, EntryConditionRuleStatus
from .serializers import (
    EntryConditionEvaluateRequestSerializer,
    EntryConditionLogSerializer,
    EntryConditionRuleCreateSerializer,
    EntryConditionRuleReorderSerializer,
    EntryConditionRuleSerializer,
)
from .services import EntryConditionEvaluator, evaluate_stage_entry

logger = logging.getLogger(__name__)


class EntryConditionRuleViewSet(viewsets.ModelViewSet):
    """进入条件规则 ViewSet"""
    queryset = EntryConditionRule.objects.all()
    permission_classes = [IsAuthenticated, HasProcessPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['link', 'status', 'link__process']
    search_fields = ['rule_name']
    ordering_fields = ['rule_seq', 'created_at']
    ordering = ['link', 'rule_seq']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return EntryConditionRuleCreateSerializer
        return EntryConditionRuleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('link', 'link__stage', 'link__process')

    @extend_schema(
        summary='评估进入条件',
        request=EntryConditionEvaluateRequestSerializer,
        responses={200: dict},
    )
    @action(detail=False, methods=['post'], url_path='evaluate')
    def evaluate(self, request):
        serializer = EntryConditionEvaluateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidate_id = serializer.validated_data['candidate_id']
        link_id = serializer.validated_data.get('link_id')
        demand_id = serializer.validated_data.get('demand_id')

        try:
            candidate = Candidate.objects.get(id=candidate_id, deleted_at__isnull=True)
        except Candidate.DoesNotExist:
            raise NotFound('候选人不存在')

        if link_id:
            try:
                link = ProcessStageLink.objects.get(id=link_id, deleted_at__isnull=True)
            except ProcessStageLink.DoesNotExist:
                raise NotFound('流程-阶段关联不存在')
        else:
            # 找该候选人最近一次的申请关联
            link = self._get_link_for_candidate(candidate, demand_id)
            if not link:
                raise NotFound('未找到该候选人的流程-阶段关联')

        # 构造 context
        context = {}
        if demand_id:
            from apps.demand.models import Demand
            try:
                context['demand'] = Demand.objects.get(id=demand_id)
            except Demand.DoesNotExist:
                pass

        result = evaluate_stage_entry(link, candidate, context)
        return Response({
            'success': True,
            'data': {
                'overall_passed': result.overall_passed,
                'matched_rule_seq': result.matched_rule_seq,
                'reject_message': result.reject_message,
                'stage_id': result.stage_id,
                'stage_name': result.stage_name,
                'rule_results': [
                    {
                        'rule_id': r.rule_id,
                        'rule_name': r.rule_name,
                        'rule_seq': r.rule_seq,
                        'passed': r.passed,
                        'reject_message': r.reject_message,
                        'items': [
                            {
                                'item_seq': ir.item_seq,
                                'field': ir.field,
                                'operator': ir.operator,
                                'value': ir.value,
                                'actual_value': ir.actual_value,
                                'passed': ir.passed,
                                'error': ir.error,
                            }
                            for ir in r.item_results
                        ],
                    }
                    for r in result.rule_results
                ],
            },
        })

    def _get_link_for_candidate(self, candidate, demand_id=None):
        from apps.application.models import Application
        qs = Application.objects.filter(candidate=candidate, deleted_at__isnull=True)
        if demand_id:
            qs = qs.filter(demand_id=demand_id)
        application = qs.first()
        if not application:
            return None
        # 找到当前阶段的 link
        return ProcessStageLink.objects.filter(
            process=application.process, stage=application.current_stage, deleted_at__isnull=True,
        ).first()

    @extend_schema(summary='评估日志')
    @action(detail=False, methods=['get'], url_path='logs')
    def logs(self, request):
        link_id = request.query_params.get('link_id')
        candidate_id = request.query_params.get('candidate_id')
        rule_id = request.query_params.get('rule_id')

        qs = EntryConditionLog.objects.all()
        if link_id:
            qs = qs.filter(link_id=link_id)
        if candidate_id:
            qs = qs.filter(candidate_id=candidate_id)
        if rule_id:
            qs = qs.filter(rule_id=rule_id)

        qs = qs.order_by('-created_at')[:200]
        serializer = EntryConditionLogSerializer(qs, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })

    @extend_schema(
        summary='重新排序规则',
        request=EntryConditionRuleReorderSerializer,
    )
    @action(detail=False, methods=['post'], url_path='reorder')
    @transaction.atomic
    def reorder(self, request):
        serializer = EntryConditionRuleReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule_orders = serializer.validated_data['rule_orders']

        for item in rule_orders:
            rule_id = item.get('rule_id')
            new_seq = item.get('rule_seq')
            if rule_id is None or new_seq is None:
                continue
            EntryConditionRule.objects.filter(id=rule_id).update(rule_seq=new_seq)

        return Response({'success': True, 'message': f'已更新 {len(rule_orders)} 条规则顺序'})

    @extend_schema(summary='启用/停用规则')
    @action(detail=True, methods=['post'], url_path='toggle')
    @transaction.atomic
    def toggle(self, request, pk=None):
        instance = self.get_object()
        new_status = (
            EntryConditionRuleStatus.DISABLED
            if instance.status == EntryConditionRuleStatus.ENABLED
            else EntryConditionRuleStatus.ENABLED
        )
        instance.status = new_status
        instance.save(update_fields=['status', 'updated_at'])
        return Response({
            'success': True,
            'data': {'id': instance.id, 'status': new_status},
        })
