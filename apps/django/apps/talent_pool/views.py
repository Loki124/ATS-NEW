"""Talent Pool Views (DRF) - PRD v4 §14.7"""
from django.db import transaction
from django.db.models import F, Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status

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
    TalentPoolEntryPoolSerializer,
    TalentPoolTagSerializer,
)

# 2026-09-26: 6 子库定义（前端 TalentPool.vue tab 契约）。顺序即默认激活子库（首项 PASSIVE）。
POOL_DEFINITIONS = [
    ('PASSIVE', '被动人才库', '暂未主动接触、储备中的人才'),
    ('ACTIVE', '主动人才库', '正在沟通或推进中的人才'),
    ('HIRED', '已入职人才库', '已完成入职流程的人才'),
    ('REJECTED', '未通过人才库', '本流程未通过的人才'),
    ('BLACKLIST', '黑名单人才库', '列入黑名单、不可再触达的人才'),
    ('GENERAL', '总人才库', '全部人才的总览'),
]


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

    # ============================================================
    # 2026-09-26: 6 子库 API（前端 TalentPool.vue 契约，此前后端从未实现 → 页面空渲染）
    #   GET  /talent-pool/types/            → {data:{CODE:{code,label,description}}}
    #   GET  /talent-pool/stats/            → {data:{stats:{CODE:count}}}
    #   GET  /talent-pool/pool/<pool>/      → {data:{list:[...]}}  按 pool_type 过滤
    #   POST /talent-pool/pool/<pool>/move/ → 跨池移动（改写 pool_type + source_detail）
    # ============================================================
    @action(detail=False, methods=['get'], url_path='types')
    def pool_types(self, request):
        """6 子库定义（前端 tab 渲染 + 默认激活池）。"""
        data = {
            code: {'code': code, 'label': label, 'description': desc}
            for code, label, desc in POOL_DEFINITIONS
        }
        return Response({'data': data})

    @action(detail=False, methods=['get'], url_path='stats')
    def pool_stats(self, request):
        """各子库条目计数（尊重 scope 过滤）。"""
        qs = self.filter_queryset(self.get_queryset())
        rows = qs.values('pool_type').annotate(cnt=Count('id'))
        stats = {code: 0 for code, _, _ in POOL_DEFINITIONS}
        for row in rows:
            stats[row['pool_type']] = row['cnt']
        return Response({'data': {'stats': stats}})

    @action(detail=False, methods=['get'], url_path='pool/(?P<pool>[^/.]+)')
    def pool_list(self, request, pool=None):
        """某子库下的条目列表（前端 TalentPool.vue 列字段契约）。"""
        qs = self.filter_queryset(self.get_queryset()).filter(pool_type=pool)
        serializer = TalentPoolEntryPoolSerializer(qs, many=True, context={'request': request})
        return Response({'data': {'list': serializer.data}})

    @action(detail=False, methods=['post'], url_path='pool/(?P<pool>[^/.]+)/move')
    def pool_move(self, request, pool=None):
        """跨池移动：把指定条目移入目标子库（pool_type）。

        前端 confirmMove 实际 POST {candidateId: <entry.id>, reason} —— candidateId 里装的是
        列表行的 entry.id（项目全局 parser 会把 camelCase 键转 snake_case，故此处读 candidate_id）。
        """
        entry_id = request.data.get('candidate_id') or request.data.get('entry_id')
        reason = (request.data.get('reason') or '').strip()
        if not entry_id:
            return Response({'success': False, 'message': '缺少条目 ID'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            entry = self.get_queryset().get(pk=entry_id)
        except TalentPoolEntry.DoesNotExist:
            return Response({'success': False, 'message': '人才库条目不存在'}, status=status.HTTP_404_NOT_FOUND)
        entry.pool_type = pool
        if reason:
            entry.source_detail = reason
        entry.save(update_fields=['pool_type', 'source_detail', 'updated_at'])
        return Response({'success': True, 'data': {'id': entry.id, 'poolType': entry.pool_type}})


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
