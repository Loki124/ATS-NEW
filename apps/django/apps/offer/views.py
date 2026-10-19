
"""Offer Views (DRF) - PRD v4 §14.5"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.common.exceptions import ValidationError
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permission_check import has_perm
from apps.core.permissions_v2 import V2Permission
from apps.core.viewsets import BaseModelViewSet

from .models import Offer
from .serializers import (
    OfferCreateSerializer,
    OfferDetailSerializer,
    OfferListSerializer,
    OfferTransitionSerializer,
)
from apps.data_permission.enforcement import ensure_writable  # M07 写范围守卫


class OfferViewSet(BaseModelViewSet):
    """Offer ViewSet - 含 8 个状态流转；按职位部门 scope 过滤"""
    queryset = Offer.objects.all()
    permission_classes = [V2Permission]
    # 读（list/retrieve）由 recruit:candidate:offer:list 统一授权 —— 候选人详情页 Offer 页签的
    # 「查看」权限（兵哥 2026-10-19：查看权限基于权限管理配置，做成可配置资源，非硬编码）。
    permission_required = 'recruit:candidate:offer:list'
    # 写动作逐一显式声明，杜绝 V2Permission 按 action 派生到不存在的 recruit:candidate:offer:delete
    # 后回退到 recruit:candidate:offer:list（那样任何能查看的人都能删，属越权）。
    # transition 放行持有 approve/edit 任一码的请求进入 action，再按 FSM 动作细查（G1）。
    permission_required_map = {
        'create': 'recruit:candidate:offer:create',
        'update': 'recruit:candidate:offer:edit',
        'partial_update': 'recruit:candidate:offer:edit',
        'destroy': 'recruit:candidate:offer:edit',
        'transition': ['recruit:candidate:offer:approve', 'recruit:candidate:offer:edit'],
    }
    # 审批人决策动作（PENDING_APPROVAL 阶段）→ 审批码；未收录动作按 :edit 校验
    TRANSITION_ACTION_PERM = {
        'approve': 'recruit:candidate:offer:approve',
        'reject': 'recruit:candidate:offer:approve',
    }
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['state', 'candidate', 'position', 'level']
    search_fields = ['code', 'candidate__name', 'position__title']
    ordering_fields = ['created_at', 'sent_at', 'responded_at']
    ordering = ['-created_at']
    scope_field = 'position__department'
    scope_creator_field = 'created_by'

    def get_serializer_class(self):
        if self.action == 'list':
            return OfferListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return OfferCreateSerializer
        if self.action == 'transition':
            return OfferTransitionSerializer
        return OfferDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        qs = qs.select_related('candidate', 'position', 'application')
        # IDOR: 按部门 scope 过滤 (Fix 1)
        qs = self.scope_queryset(qs)
        return qs

    def perform_destroy(self, instance):
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        instance = self.get_object()
        ensure_writable(request.user, 'offer', instance, action='transition')
        serializer = OfferTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']
        # 细粒度校验：审批动作要求审批码，其余流转动作要求 :edit（G1）
        required = self.TRANSITION_ACTION_PERM.get(action_name, 'recruit:candidate:offer:edit')
        if not has_perm(request.user, required):
            raise PermissionDenied(f'无权执行该操作，缺少权限码 {required}')
        kwargs = {}
        if action_name == 'candidate_reject':
            kwargs['reason'] = serializer.validated_data.get('reason', '')
        method = getattr(instance, action_name, None)
        if not method:
            raise ValidationError(f'不支持的操作：{action_name}')
        method(**kwargs)
        instance.save()
        out = OfferDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})