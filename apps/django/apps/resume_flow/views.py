"""Resume Flow Views — 审批流 API

端点:
- GET    /resumes/approval-flows       列表
- POST   /resumes/approval-flows       新建
- GET    /resumes/approval-flows/{id}  详情
- POST   /resumes/approval-flows/{id}/approve   批准
- POST   /resumes/approval-flows/{id}/reject    驳回
- POST   /resumes/approval-flows/{id}/delegate  转交
"""
from __future__ import annotations

import logging
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.exceptions import NotFound, PermissionDenied, StateTransitionError, ValidationError
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.common.views import EnvelopeReadOnlyMixin
from apps.core.permissions_v2 import V2Permission

from .models import ApprovalFlow, ApprovalFlowHistory
from .serializers import (
    ApprovalFlowCreateSerializer,
    ApprovalFlowDetailSerializer,
    ApprovalFlowListSerializer,
    ApprovalFlowTransitionSerializer,
)

logger = logging.getLogger(__name__)


class ApprovalFlowViewSet(EnvelopeReadOnlyMixin, viewsets.ModelViewSet):
    """审批流 ViewSet

    list:      列出当前用户相关的审批流
    retrieve:  详情（含 nodes + histories）
    create:    新建审批流
    approve:   批准当前节点
    reject:    驳回
    delegate:  转交
    """
    queryset = ApprovalFlow.objects.all()
    permission_classes = [V2Permission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'candidate']
    search_fields = ['id', 'candidate__name']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ApprovalFlowListSerializer
        if self.action == 'retrieve':
            return ApprovalFlowDetailSerializer
        if self.action == 'create':
            return ApprovalFlowCreateSerializer
        if self.action in ('approve', 'reject', 'delegate'):
            return ApprovalFlowTransitionSerializer
        return ApprovalFlowDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.select_related('candidate', 'created_by')
        qs = qs.annotate(history_count=Count('histories'))
        return qs

    def create(self, request, *args, **kwargs):
        """新建审批流 — 写入 ApprovalFlowHistory(CREATED)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        flow = serializer.save()

        # 写审计历史
        ApprovalFlowHistory.objects.create(
            flow=flow,
            action='CREATED',
            from_node='',
            to_node=flow.current_node_id,
            operated_by=request.user,
            comment='创建审批流',
        )

        out = ApprovalFlowDetailSerializer(flow, context={'request': request})
        # 2026-09-30 信封 initiative: 收敛到 success_response 补齐 code
        return success_response(out.data, status_code=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """编辑审批流 — 包 {success, data} 信封 (create/approve/reject/delegate 为自定义, 不动)."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='approve',
            permission_classes=[V2Permission])
    def approve(self, request, pk=None):
        """批准当前节点 → 推进 current_node_id"""
        flow = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        node_id = serializer.validated_data['node_id']
        comment = serializer.validated_data.get('comment', '')

        if flow.status not in ('PENDING', 'IN_PROGRESS'):
            raise StateTransitionError(f'当前状态 {flow.status} 不可批准')

        # 找到当前节点在 nodes 数组中的位置
        nodes = flow.nodes or []
        current_idx = None
        for i, node in enumerate(nodes):
            if node.get('nodeId') == node_id:
                current_idx = i
                break

        if current_idx is None:
            raise ValidationError(f'节点 {node_id} 不在审批流中')

        # 标记当前节点为已决定
        nodes[current_idx]['decidedAt'] = str(flow.updated_at)
        nodes[current_idx]['comment'] = comment
        nodes[current_idx]['decision'] = 'APPROVED'

        # 推进到下一节点
        next_idx = current_idx + 1
        from_node = node_id
        if next_idx < len(nodes):
            flow.current_node_id = nodes[next_idx].get('nodeId', '')
            flow.status = 'IN_PROGRESS'
            to_node = flow.current_node_id
        else:
            flow.current_node_id = ''
            flow.status = 'APPROVED'
            to_node = ''

        flow.nodes = nodes
        flow.save(update_fields=['nodes', 'current_node_id', 'status', 'updated_at'])

        # 写历史
        ApprovalFlowHistory.objects.create(
            flow=flow, action='APPROVED',
            from_node=from_node, to_node=to_node,
            operated_by=request.user, comment=comment,
        )

        out = ApprovalFlowDetailSerializer(flow, context={'request': request})
        return Response({'success': True, 'data': out.data})

    @action(detail=True, methods=['post'], url_path='reject',
            permission_classes=[V2Permission])
    def reject(self, request, pk=None):
        """驳回 → status=REJECTED"""
        flow = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        node_id = serializer.validated_data['node_id']
        comment = serializer.validated_data.get('comment', '')

        if flow.status not in ('PENDING', 'IN_PROGRESS'):
            raise StateTransitionError(f'当前状态 {flow.status} 不可驳回')

        # 标记当前节点
        nodes = flow.nodes or []
        for node in nodes:
            if node.get('nodeId') == node_id:
                node['decidedAt'] = str(flow.updated_at)
                node['comment'] = comment
                node['decision'] = 'REJECTED'
                break

        flow.nodes = nodes
        flow.status = 'REJECTED'
        flow.current_node_id = ''
        flow.save(update_fields=['nodes', 'status', 'current_node_id', 'updated_at'])

        ApprovalFlowHistory.objects.create(
            flow=flow, action='REJECTED',
            from_node=node_id, to_node='',
            operated_by=request.user, comment=comment,
        )

        out = ApprovalFlowDetailSerializer(flow, context={'request': request})
        return Response({'success': True, 'data': out.data})

    @action(detail=True, methods=['post'], url_path='delegate',
            permission_classes=[V2Permission])
    def delegate(self, request, pk=None):
        """转交 → 更新当前节点 approverId"""
        flow = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        node_id = serializer.validated_data['node_id']
        delegate_to = serializer.validated_data.get('delegate_to', '')
        comment = serializer.validated_data.get('comment', '')

        if not delegate_to:
            raise ValidationError('delegate_to 不能为空')

        if flow.status not in ('PENDING', 'IN_PROGRESS'):
            raise StateTransitionError(f'当前状态 {flow.status} 不可转交')

        nodes = flow.nodes or []
        for node in nodes:
            if node.get('nodeId') == node_id:
                old_approver = node.get('approverId', '')
                node['approverId'] = delegate_to
                break

        flow.nodes = nodes
        flow.save(update_fields=['nodes', 'updated_at'])

        ApprovalFlowHistory.objects.create(
            flow=flow, action='DELEGATED',
            from_node=node_id, to_node=node_id,
            operated_by=request.user,
            comment=f'转交: {delegate_to}. {comment}',
        )

        out = ApprovalFlowDetailSerializer(flow, context={'request': request})
        return Response({'success': True, 'data': out.data})
