"""Invitation Views (DRF) - PRD v4 §14.6"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import ValidationError
from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsHROrAbove, ScopedQuerysetMixin

from .models import Invitation
from .serializers import (
    InvitationCreateSerializer,
    InvitationDetailSerializer,
    InvitationListSerializer,
    InvitationTransitionSerializer,
)


class InvitationViewSet(ScopedQuerysetMixin, AuditMixin, viewsets.ModelViewSet):
    """邀约 ViewSet - 收紧到 HR+ 可见, 按 application 部门 scope (Fix 1)"""
    queryset = Invitation.objects.all()
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['state', 'application', 'inviter', 'is_grab_pool']
    search_fields = ['application__code']
    ordering_fields = ['invited_at', 'expire_at']
    ordering = ['-invited_at']
    scope_field = 'application__position__department'
    scope_creator_field = 'inviter'

    def get_serializer_class(self):
        if self.action == 'list':
            return InvitationListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return InvitationCreateSerializer
        if self.action == 'transition':
            return InvitationTransitionSerializer
        return InvitationDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        qs = qs.select_related('application', 'inviter')
        qs = self.scope_queryset(qs)
        return qs

    def perform_destroy(self, instance):
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        instance = self.get_object()
        serializer = InvitationTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']
        kwargs = {}
        if action_name == 'fail':
            kwargs['response'] = serializer.validated_data.get('response', '')
            kwargs['note'] = serializer.validated_data.get('note', '')
        method = getattr(instance, action_name, None)
        if not method:
            raise ValidationError(f'不支持的操作：{action_name}')
        method(**kwargs)
        instance.save()
        out = InvitationDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})

    @action(detail=False, methods=['get'], url_path='grab-pool')
    def grab_pool(self, request):
        """抢单池 - 列出所有 is_grab_pool=True + state=INVITING 的邀约"""
        qs = self.get_queryset().filter(is_grab_pool=True, state='INVITING')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = InvitationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = InvitationListSerializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='claimable')
    def claimable(self, request):
        """可领取邀约 (grab-pool alias). 2026-07-01 stub: 走 grab-pool 同逻辑, FE 命名习惯 claimable."""
        qs = self.get_queryset().filter(is_grab_pool=True, state='INVITING')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = InvitationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = InvitationListSerializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='process-expired')
    def process_expired(self, request):
        """处理过期邀约 (定时任务用). 2026-07-01 stub: 返空 list."""
        return Response({'success': True, 'data': [], 'count': 0})

    @action(detail=True, methods=['post'], url_path='grab')
    def grab(self, request, pk=None):
        """抢单 - 把邀约分配给当前用户"""
        from django.utils import timezone
        instance = self.get_object()
        if not instance.is_grab_pool:
            raise ValidationError('该邀约不是抢单池模式')
        if instance.state != 'INVITING':
            raise ValidationError(f'当前状态 {instance.state} 不可抢单')
        instance.grabbed_by = request.user
        instance.grabbed_at = timezone.now()
        instance.save()
        out = InvitationDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})
