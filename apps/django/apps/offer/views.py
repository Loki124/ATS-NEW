
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


class OfferViewSet(BaseModelViewSet):
    """Offer ViewSet - 含 8 个状态流转；按职位部门 scope 过滤"""
    queryset = Offer.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:offer:list'
    # G1: seed 定义的审批码在此真实消费。此前 transition 作为自定义 action 一律按
    # 派生码 recruit:offer:edit 校验，导致身份管理里单独勾「审批Offer」不生效。
    # 类级 map 放行持有 approve/edit 任一码的请求进入 action，再按 FSM 动作细查。
    permission_required_map = {
        'transition': ['recruit:offer:approve', 'recruit:offer:edit'],
    }
    # 审批人决策动作（PENDING_APPROVAL 阶段）→ 审批码；未收录动作按 :edit 校验
    TRANSITION_ACTION_PERM = {
        'approve': 'recruit:offer:approve',
        'reject': 'recruit:offer:approve',
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
        serializer = OfferTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']
        # 细粒度校验：审批动作要求审批码，其余流转动作要求 :edit（G1）
        required = self.TRANSITION_ACTION_PERM.get(action_name, 'recruit:offer:edit')
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
