"""Talent Pool Views (DRF) - PRD v4 §14.7"""
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

# 2026-09-25: 入池触发点 —— 执行「入池」场景的指标规则
from apps.metrics.services.rule_trigger import evaluate_scene

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import is_super_admin
from apps.core.permissions_v2 import V2Permission, ScopeQuerysetMixin

from .models import TalentPoolEntry, TalentPoolTag
from .serializers import (
    TalentPoolEntryCreateSerializer,
    TalentPoolEntryDetailSerializer,
    TalentPoolEntryListSerializer,
    TalentPoolTagSerializer,
)


class TalentPoolEntryViewSet(ScopeQuerysetMixin, AuditMixin, viewsets.ModelViewSet):
    """人才库条目 ViewSet - 收紧权限仅 HR 可读写 (Fix 1)"""
    queryset = TalentPoolEntry.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:talent_pool:list'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['source', 'is_active', 'candidate']
    search_fields = ['candidate__name', 'source_detail']
    ordering_fields = ['created_at', 'last_activated_at', 'activated_count']
    ordering = ['-created_at']
    scope_field = 'last_position__department'
    scope_creator_field = 'created_by'

    def get_serializer_class(self):
        if self.action == 'list':
            return TalentPoolEntryListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return TalentPoolEntryCreateSerializer
        return TalentPoolEntryDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        qs = qs.select_related('candidate', 'last_position', 'last_stage')
        qs = self.scope_queryset(qs, entity='talent')
        return qs

    def perform_create(self, serializer):
        """入池前执行「入池」场景的指标规则（2026-09-25 触发点接入）。

        - 阻断型规则（blocking=True）不满足 → 拒绝入池，返回 400 + 人话原因
        - 非阻断规则 / 无规则 / 规则引擎异常 → 正常入池（安全默认，避免规则误配伤业务）
        """
        try:
            candidate = serializer.validated_data.get('candidate')
            if candidate is not None:
                outcome = evaluate_scene('TALENT_POOL', str(candidate.pk))
                if outcome.get('blocked'):
                    raise ValidationError(outcome.get('message') or '不满足入池规则')
        except ValidationError:
            raise
        except Exception:
            # 规则引擎异常一律放行，绝不让入池因规则故障失败
            pass
        serializer.save()

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """激活人才库候选人 (2026-07-02: 改用 F() 原子递增 + select_for_update 防并发)"""
        with transaction.atomic():
            instance = self.get_object().__class__.objects.select_for_update().get(pk=pk)
            instance.__class__.objects.filter(pk=instance.pk).update(
                is_active=True,
                last_activated_at=timezone.now(),
                activated_count=F('activated_count') + 1,
            )
            instance.refresh_from_db()
        out = TalentPoolEntryDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """停用"""
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        out = TalentPoolEntryDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})


class TalentPoolTagViewSet(AuditMixin, viewsets.ModelViewSet):
    """人才库标签 ViewSet"""
    queryset = TalentPoolTag.objects.all()
    serializer_class = TalentPoolTagSerializer
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['category', 'name']
