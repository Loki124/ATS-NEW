"""Demand Views (DRF) - PRD v4 §14.1"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import ValidationError
from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsHROrAbove

from .models import Demand, DemandApproval
from .serializers import (
    DemandApprovalSerializer,
    DemandCreateSerializer,
    DemandDetailSerializer,
    DemandListSerializer,
    DemandTransitionSerializer,
)


class DemandViewSet(AuditMixin, viewsets.ModelViewSet):
    """招聘需求 ViewSet - 含状态机流转"""
    queryset = Demand.objects.all()
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['state', 'department', 'hr', 'requested_by', 'priority']
    search_fields = ['code', 'title', 'position_title']
    ordering_fields = ['code', 'created_at', 'submitted_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return DemandListSerializer
        if self.action == 'retrieve':
            return DemandDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return DemandCreateSerializer
        if self.action == 'transition':
            return DemandTransitionSerializer
        return DemandDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        return qs.select_related('department', 'requested_by', 'hr', 'process')

    def perform_destroy(self, instance):
        # 软删除
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        """状态机流转：submit/approve/reject/start_recruiting/pause/resume/complete/cancel"""
        instance = self.get_object()
        serializer = DemandTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']
        method = getattr(instance, action_name, None)
        if not method:
            raise ValidationError(f'不支持的操作：{action_name}')
        method()  # django-fsm transition
        instance.save()
        out = DemandDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})

    @action(detail=True, methods=['get'], url_path='approvals')
    def approvals(self, request, pk=None):
        """获取需求审批记录"""
        instance = self.get_object()
        approvals = instance.approvals.all().order_by('level')
        serializer = DemandApprovalSerializer(approvals, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=True, methods=['post'], url_path='add-approval')
    def add_approval(self, request, pk=None):
        """添加审批人"""
        instance = self.get_object()
        approver_id = request.data.get('approver_id')
        level = request.data.get('level', 1)
        if not approver_id:
            raise ValidationError('缺少 approver_id')
        approval = DemandApproval.objects.create(
            demand=instance,
            approver_id=approver_id,
            level=level,
        )
        serializer = DemandApprovalSerializer(approval)
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_201_CREATED)
