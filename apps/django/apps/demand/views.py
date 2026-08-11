"""Demand Views (DRF) - PRD v4 §14.1"""
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from nanoid import generate as nanoid_generate
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import NotFound, ValidationError
from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions_v2 import V2Permission, ScopeQuerysetMixin
from apps.process.models import RecruitmentProcess

from .models import Demand, DemandApproval
from .serializers import (
    DemandApprovalSerializer,
    DemandCreateSerializer,
    DemandDetailSerializer,
    DemandListSerializer,
    DemandTransitionSerializer,
    DemandUpgradeProcessSerializer,
)
from .services import DemandService


class DemandViewSet(ScopeQuerysetMixin, AuditMixin, viewsets.ModelViewSet):
    """招聘需求 ViewSet - 按部门 scope 过滤"""
    queryset = Demand.objects.all().order_by('-created_at')
    permission_classes = [V2Permission]
    permission_required = 'recruit:demand:list'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['state', 'department', 'hr', 'requested_by', 'priority']
    search_fields = ['code', 'title', 'position_title']
    ordering_fields = ['code', 'created_at', 'submitted_at']
    ordering = ['-created_at']
    scope_field = 'department'
    scope_creator_field = 'requested_by'

    def get_serializer_class(self):
        if self.action == 'list':
            return DemandListSerializer
        if self.action == 'retrieve':
            return DemandDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return DemandCreateSerializer
        if self.action == 'transition':
            return DemandTransitionSerializer
        if self.action == 'upgrade_process_version':
            return DemandUpgradeProcessSerializer
        return DemandDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        qs = qs.select_related('department', 'requested_by', 'hr', 'process')
        # IDOR scope 过滤 (Fix 1)
        qs = self.scope_queryset(qs)
        return qs

    def perform_destroy(self, instance):
        # 软删除
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    def perform_create(self, serializer):
        """建需求：requested_by / hr 取当前用户，process 默认最新启用流程。

        前端建需求表单仅收集 title / department / headcount 等业务字段，不收集
        提出人 / 负责HR / 流程（无流程选择器）。这些服务端已知项在此统一填充，
        既避免信任客户端伪造提出人，也保证 process FK 必填可满足。
        保留 AuditMixin 的 created_by / updated_by 审计注入。
        """
        user = self.request.user
        process = (
            RecruitmentProcess.objects
            .filter(is_latest=True, status='ENABLED', deleted_at__isnull=True)
            .first()
            or RecruitmentProcess.objects.filter(deleted_at__isnull=True).first()
        )
        # 生成需求编号 D + yyyymmdd + 4位（与 DemandService.create_demand 同款格式）。
        # API 建需求走 serializer 直建、不经过 DemandService，故此处补生成，否则
        # code 留空会撞 demands.code 唯一约束（第二次创建即 500）。
        code = f'D{timezone.now().strftime("%Y%m%d")}{nanoid_generate(size=4).upper()}'
        audit_kwargs = self.build_audit_kwargs(
            serializer,
            (self.audit_created_by_field, self.audit_updated_by_field),
        )
        serializer.save(
            requested_by=user, hr=user, process=process,
            code=code,
            process_version=process.current_version if process else 'V1.0',
            **audit_kwargs,
        )

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

    @action(detail=True, methods=['post'], url_path='upgrade-process-version')
    def upgrade_process_version(self, request, pk=None):
        """需求升级到最新流程版本（T9 / §4.1）。

        契约：
        - 成功升级 → 200，``upgraded=true``，``moved_position_ids`` 为实际改指的职位 id。
        - 已在最新版 → 200 幂等，``upgraded=false``，``moved_position_ids=[]``。
          （这是正常状态而非冲突，与 archive/clone 的 409「状态非法」语义不同。）
        - 目标版本已归档 / 非最新 / 跨流程线 / 流程线无可用最新版 / 需求未关联流程
          → 409（``StateTransitionError``，由全局 exception handler 转换）。

        **不改指 Application**：BR-102 硬红线，在跑候选人继续走创建时的版本。
        """
        instance = self.get_object()
        serializer = DemandUpgradeProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_process = None
        target_process_id = serializer.validated_data.get('target_process_id') or None
        if target_process_id:
            from apps.process.models import RecruitmentProcess
            target_process = RecruitmentProcess.objects.filter(
                id=target_process_id, deleted_at__isnull=True,
            ).first()
            if target_process is None:
                raise NotFound(f'流程版本 {target_process_id} 不存在')

        old_process_id = instance.process_id  # §1.3.2：快照早于任何赋值
        demand, moved = DemandService.upgrade_demand_process(
            instance, actor=request.user, target_process=target_process,
        )
        out = DemandDetailSerializer(demand, context={'request': request})
        return Response({
            'success': True,
            'data': {
                'demand': out.data,
                'moved_position_ids': moved,
                'upgraded': demand.process_id != old_process_id,
                'previous_process_id': old_process_id,
            },
        })

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
