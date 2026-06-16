"""Process App Views (DRF)

包含：
- RecruitmentStageViewSet: 阶段库 CRUD
- RecruitmentProcessViewSet: 招聘流程 CRUD + 自定义 actions
- ProcessStageLinkViewSet: 流程-阶段关联
- ProcessTemplateViewSet: 流程模板
- ExpressionValidationView: 表达式校验
- ProcessApplyTemplateView: 应用模板
- ProcessArchiveView: 归档流程
"""
from __future__ import annotations

import logging
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.common.exceptions import (
    NotFound,
    PermissionDenied,
    StateTransitionError,
    ValidationError,
)
from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import HasProcessPermission

from .models import (
    ProcessStageLink,
    ProcessTemplate,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
    StageStatus,
)
from .serializers import (
    ExpressionValidationRequestSerializer,
    ExpressionValidationResponseSerializer,
    ProcessStageLinkSerializer,
    ProcessTemplateApplySerializer,
    ProcessTemplateSerializer,
    ProcessWithStagesCreateSerializer,
    RecruitmentProcessDetailSerializer,
    RecruitmentProcessListSerializer,
    RecruitmentProcessSerializer,
    RecruitmentStageCreateSerializer,
    RecruitmentStageSerializer,
    StageRuleSerializer,
)
from .services.expression_service import validate_expression
from .services.versioning import (
    archive_process,
    clone_process_with_new_version,
    is_process_referenced,
    list_process_versions,
    bump_version,
)

logger = logging.getLogger(__name__)


# ============================================================
# 阶段（RecruitmentStage）
# ============================================================
class RecruitmentStageViewSet(viewsets.ModelViewSet):
    """阶段库 ViewSet

    list:      列表 (支持 type/status 过滤)
    retrieve:  详情
    create:    创建 (HRBP+)
    update:    更新 (HRBP+)
    destroy:   删除 (HRBP+) - 引用中不可删
    """
    queryset = RecruitmentStage.objects.all()
    permission_classes = [IsAuthenticated, HasProcessPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['stage_type', 'status', 'is_builtin']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'created_at', 'updated_at']
    ordering = ['code']

    def get_serializer_class(self):
        if self.action == 'create':
            return RecruitmentStageCreateSerializer
        return RecruitmentStageSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 默认排除已软删
        qs = qs.filter(deleted_at__isnull=True)
        # 可选返回全部
        if self.request.query_params.get('include_deleted') == 'true':
            qs = RecruitmentStage.objects.all()
        return qs

    def destroy(self, request, *args, **kwargs):
        """BR-003: 阶段被引用时不可删除"""
        instance = self.get_object()
        if instance.is_builtin:
            raise PermissionDenied('预置阶段不可删除')
        if instance.is_referenced:
            raise PermissionDenied(
                f'阶段「{instance.name}」被 {instance.reference_count} 个流程引用，不可删除',
            )
        return super().destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # 软删除
        instance.soft_delete()

    @extend_schema(
        summary='停用阶段',
        description='BR-002: 阶段被任一流程引用时不可停用',
        responses={200: RecruitmentStageSerializer},
    )
    @action(detail=True, methods=['post'], url_path='disable')
    def disable(self, request, pk=None):
        instance = self.get_object()
        if instance.is_builtin:
            raise PermissionDenied('预置阶段不可停用')
        if instance.is_referenced:
            raise PermissionDenied(
                f'阶段「{instance.name}」被引用，不可停用',
            )
        instance.status = StageStatus.DISABLED
        instance.save(update_fields=['status', 'updated_at'])
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data,
        })

    @extend_schema(
        summary='启用阶段',
        responses={200: RecruitmentStageSerializer},
    )
    @action(detail=True, methods=['post'], url_path='enable')
    def enable(self, request, pk=None):
        instance = self.get_object()
        instance.status = StageStatus.ENABLED
        instance.save(update_fields=['status', 'updated_at'])
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data,
        })

    @extend_schema(
        summary='阶段引用情况',
    )
    @action(detail=True, methods=['get'], url_path='references')
    def references(self, request, pk=None):
        instance = self.get_object()
        links = instance.process_stage_links.filter(
            process__status__in=['ENABLED', 'ARCHIVED'],
        ).select_related('process')
        return Response({
            'success': True,
            'data': {
                'stage_id': instance.id,
                'stage_name': instance.name,
                'reference_count': links.count(),
                'processes': [
                    {
                        'process_id': l.process_id,
                        'process_name': l.process.name,
                        'process_code': l.process.code,
                        'order': l.order,
                    }
                    for l in links
                ],
            }
        })


# ============================================================
# 流程（RecruitmentProcess）
# ============================================================
class RecruitmentProcessViewSet(viewsets.ModelViewSet):
    """招聘流程 ViewSet

    list:           列表
    retrieve:       详情（含 stage_links）
    create:         创建（含 stages 嵌套写入）
    update:         基础信息更新
    destroy:        删除（无引用时）
    archive:        归档（替代停用）
    clone_version:  克隆新版本
    list_versions:  列出历史版本
    """
    queryset = RecruitmentProcess.objects.all()
    permission_classes = [IsAuthenticated, HasProcessPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'is_template', 'template_code', 'is_enabled']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'code']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return RecruitmentProcessListSerializer
        if self.action == 'retrieve':
            return RecruitmentProcessDetailSerializer
        if self.action == 'create_with_stages':
            return ProcessWithStagesCreateSerializer
        return RecruitmentProcessSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        return qs.select_related('created_by', 'updated_by')

    def create(self, request, *args, **kwargs):
        """创建流程（含 stages）"""
        serializer = ProcessWithStagesCreateSerializer(
            data=request.data, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        process = serializer.save()
        out = RecruitmentProcessDetailSerializer(process, context={'request': request})
        return Response(
            {'success': True, 'data': out.data},
            status=status.HTTP_201_CREATED,
        )

    def perform_destroy(self, instance):
        if is_process_referenced(instance):
            raise PermissionDenied(
                f'流程「{instance.name}」被 {instance.reference_count} 个需求引用，不可删除',
            )
        instance.soft_delete()

    @extend_schema(
        summary='归档流程',
        description='BR-106: 流程无停用态，只能归档。归档后只读。',
        responses={200: RecruitmentProcessDetailSerializer},
    )
    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        instance = self.get_object()
        if instance.status == 'ARCHIVED':
            raise StateTransitionError('流程已归档')
        result = archive_process(instance, actor=request.user)
        serializer = RecruitmentProcessDetailSerializer(instance, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data,
            'message': '流程已归档',
            'extra': result,
        })

    @extend_schema(
        summary='克隆为新版本',
        description='BR-101: 引用中流程的配置修改将生成新版本',
        request=None,
        responses={201: RecruitmentProcessDetailSerializer},
    )
    @action(detail=True, methods=['post'], url_path='clone-version')
    def clone_version(self, request, pk=None):
        instance = self.get_object()
        new_process = clone_process_with_new_version(
            instance,
            new_name=request.data.get('name'),
            actor=request.user,
        )
        serializer = RecruitmentProcessDetailSerializer(new_process, context={'request': request})
        return Response(
            {'success': True, 'data': serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary='列出该流程编号的所有历史版本')
    @action(detail=True, methods=['get'], url_path='versions')
    def list_versions(self, request, pk=None):
        instance = self.get_object()
        versions = list_process_versions(instance.code)
        return Response({
            'success': True,
            'data': versions,
        })

    @extend_schema(
        summary='升版本',
        description='BR-104: 支持历史候选人升版本到最新版本',
        request={'type': 'object', 'properties': {
            'target_version': {'type': 'string', 'description': '目标版本号，如 V1.2'},
        }},
    )
    @action(detail=True, methods=['post'], url_path='bump-version')
    def bump_version_action(self, request, pk=None):
        instance = self.get_object()
        new_version = bump_version(instance)
        return Response({
            'success': True,
            'data': {
                'id': instance.id,
                'current_version': new_version,
            }
        })


# ============================================================
# 流程-阶段关联（ProcessStageLink）
# ============================================================
class ProcessStageLinkViewSet(viewsets.ModelViewSet):
    """流程-阶段关联 ViewSet"""
    queryset = ProcessStageLink.objects.all()
    serializer_class = ProcessStageLinkSerializer
    permission_classes = [IsAuthenticated, HasProcessPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['process', 'stage', 'is_required']
    ordering_fields = ['order', 'created_at']
    ordering = ['process', 'order']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        return qs.select_related('stage', 'process', 'stage_rule')

    def perform_destroy(self, instance):
        instance.soft_delete()

    @extend_schema(summary='重排阶段顺序')
    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """批量更新 stage_links 顺序
        Body: { "process_id": "...", "order": [{"link_id": "...", "order": 1}, ...] }
        """
        process_id = request.data.get('process_id')
        order_data = request.data.get('order', [])
        if not process_id or not order_data:
            raise ValidationError('缺少 process_id 或 order')

        try:
            process = RecruitmentProcess.objects.get(id=process_id, deleted_at__isnull=True)
        except RecruitmentProcess.DoesNotExist:
            raise NotFound('流程不存在')

        for item in order_data:
            link_id = item.get('link_id')
            new_order = item.get('order')
            if link_id is None or new_order is None:
                continue
            ProcessStageLink.objects.filter(
                id=link_id, process=process,
            ).update(order=new_order, updated_at=process.updated_at)

        # 返回新顺序
        links = ProcessStageLink.objects.filter(
            process=process, deleted_at__isnull=True,
        ).order_by('order')
        serializer = ProcessStageLinkSerializer(links, many=True, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data,
        })


# ============================================================
# 阶段规则（StageRule）
# ============================================================
class StageRuleViewSet(viewsets.ModelViewSet):
    """阶段规则 ViewSet"""
    queryset = StageRule.objects.all()
    serializer_class = StageRuleSerializer
    permission_classes = [IsAuthenticated, HasProcessPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['link', 'processing_rule', 'is_grab_mode']
    ordering_fields = ['created_at']
    ordering = ['link', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        return qs.select_related('link', 'link__stage', 'link__process')


# ============================================================
# 流程模板（ProcessTemplate）
# ============================================================
class ProcessTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """流程模板 - 只读 (由 seed/管理后台维护)"""
    queryset = ProcessTemplate.objects.filter(is_active=True)
    serializer_class = ProcessTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'is_builtin', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['-is_builtin', 'name']
    ordering = ['-is_builtin', 'name']


# ============================================================
# 表达式校验（独立 API）
# ============================================================
class ExpressionValidationView(APIView):
    """表达式校验 - 实时反馈给前端"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='条件表达式校验',
        description='校验语法、引用编号范围、是否括号匹配，并提供修复建议',
        request=ExpressionValidationRequestSerializer,
        responses={200: ExpressionValidationResponseSerializer},
    )
    def post(self, request):
        serializer = ExpressionValidationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expression = serializer.validated_data['expression']
        max_id = serializer.validated_data['max_id']

        result = validate_expression(expression, max_id)

        return Response({
            'success': True,
            'data': result.to_dict(),
        })


# ============================================================
# 应用流程模板
# ============================================================
class ProcessApplyTemplateView(APIView):
    """应用流程模板创建新流程"""
    permission_classes = [IsAuthenticated, HasProcessPermission]

    @extend_schema(
        summary='从模板创建流程',
        request=ProcessTemplateApplySerializer,
        responses={201: RecruitmentProcessDetailSerializer},
    )
    def post(self, request):
        serializer = ProcessTemplateApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            template = ProcessTemplate.objects.get(id=serializer.validated_data['template_id'])
        except ProcessTemplate.DoesNotExist:
            raise NotFound('模板不存在')

        # 基于模板快照创建流程
        from .services.template_apply import apply_template_to_process
        process = apply_template_to_process(
            template,
            name=serializer.validated_data['name'],
            code=serializer.validated_data['code'],
            actor=request.user,
        )
        out = RecruitmentProcessDetailSerializer(process, context={'request': request})
        return Response(
            {'success': True, 'data': out.data},
            status=status.HTTP_201_CREATED,
        )
