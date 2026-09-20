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
from apps.core.permissions_v2 import V2Permission
# T01.2 (2026-08-04 寇豆码): HasProcessPermission / V2Permission 自身已校验登录, 显式
# 移除裸 IsAuthenticated, 避免被全局 deny-by-default 拦截.

from .models import (
    CandidateRecommendation,
    CandidateScreen,
    InterviewRound,
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
    InterviewRoundCreateSerializer,
    InterviewRoundSerializer,
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
    permission_classes = [HasProcessPermission]
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

    @extend_schema(
        summary='阶段类型枚举 (系统内置)',
        description='返回 7 个固定阶段类型 [{value, label}], 系统级默认数据, 不依赖数据字典',
        responses={200: dict},
    )
    @action(detail=False, methods=['get'], url_path='stage-types')
    def stage_types(self, request):
        from apps.process.models import StageType
        return Response([
            {'value': value, 'label': label}
            for value, label in StageType.choices
        ])


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
    permission_classes = [HasProcessPermission]
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
        description='BR-106: 流程无停用态，只能归档。归档作用于整条流程线（同 code 的全部版本行），归档后只读。',
        responses={200: RecruitmentProcessDetailSerializer},
    )
    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        instance = self.get_object()
        # 产品 Q5：归档的作用域是整条 code 线，故「重复归档」的判据也必须是整条线——
        # 「该 code 下已无 ENABLED 行」。原判据只看当前这一行的 status：从一个历史版本
        # 行（多半已是 ARCHIVED）发起归档会被误判成重复归档而 409，而该线的最新版
        # 其实还是 ENABLED，真正需要归档的行反而永远归不掉。
        has_enabled_row = RecruitmentProcess.objects.filter(
            code=instance.code, deleted_at__isnull=True, status='ENABLED',
        ).exists()
        if not has_enabled_row:
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
        # 产品 Q3：因阶段变更被跳过/禁用的自动化规则要回给前端，用于提示
        # 「N 条自动化规则因阶段变更需要重新配置」。服务层把清单挂在返回对象上
        # （而非改成元组返回），既不破坏既有调用方也不用动序列化器。
        degraded_rules = getattr(new_process, '_degraded_automation_rules', [])
        return Response(
            {
                'success': True,
                'data': serializer.data,
                'extra': {'degraded_automation_rules': degraded_rules},
            },
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

    # 已废弃并删除：POST /processes/{id}/bump-version/（T2，产品 Q1 裁定）
    # 该端点是三重错配——summary 写"升版本(BR-104 候选人升版)"、路由叫 bump-version、
    # 实现却是"原地改流程自己的版本号"且完全忽略 target_version 入参；与 BR-101
    # 「配置修改生成新版本」/ BR-103「历史版本只读」直接冲突。前端零调用、零测试覆盖。
    # 「产生新版本」在产品上有且只有一个动作 = clone-version（上方 clone_version）。

    # ============================================================
    # Phase 2 T06: batch/screen + batch/recommend 真实现
    # ============================================================
    @extend_schema(
        summary='批量筛选候选人',
        description='对一批候选人做筛选结论（通过/淘汰/待议），写入 CandidateScreen 审计记录。',
        request={'type': 'object', 'properties': {
            'candidate_ids': {'type': 'array', 'items': {'type': 'string'}},
            'decision': {'type': 'string', 'enum': ['PASS', 'REJECT', 'KEEP']},
            'stage_id': {'type': 'string', 'description': '当前阶段ID'},
            'comment': {'type': 'string'},
        }, 'required': ['candidate_ids', 'decision']},
        responses={200: {'type': 'object', 'properties': {
            'success': {'type': 'boolean'},
            'data': {'type': 'object', 'properties': {
                'results': {'type': 'array'},
            }},
        }}},
    )
    @action(detail=True, methods=['post'], url_path='batch-screen',
            permission_classes=[V2Permission])
    def batch_screen(self, request, pk=None):
        """批量筛选候选人

        保持现有响应壳 {results: [{candidateId, success, result, screenId}]}。
        """
        process = self.get_object()
        candidate_ids = request.data.get('candidate_ids', [])
        decision = request.data.get('decision', 'PASS')
        stage_id = request.data.get('stage_id', '')
        comment = request.data.get('comment', '')

        if not candidate_ids:
            raise ValidationError('candidate_ids 不能为空')

        from apps.candidate.models import Candidate

        results = []
        for cid in candidate_ids:
            try:
                cand = Candidate.objects.get(pk=cid)
                screen_record = CandidateScreen.objects.create(
                    process=process,
                    candidate=cand,
                    stage_id=stage_id or None,
                    screen_result={'decision': decision, 'comment': comment},
                    screened_by=request.user,
                )
                results.append({
                    'candidate_id': cid,
                    'success': True,
                    'result': decision,
                    'screen_id': screen_record.id,
                })
            except Candidate.DoesNotExist:
                results.append({
                    'candidate_id': cid,
                    'success': False,
                    'result': None,
                    'error': 'CANDIDATE_NOT_FOUND',
                })

        return Response({
            'success': True,
            'data': {'results': results},
        })

    @extend_schema(
        summary='批量推荐候选人',
        description='为一批候选人创建推荐记录，recommendationId 由真 model 主键填充。',
        request={'type': 'object', 'properties': {
            'candidate_ids': {'type': 'array', 'items': {'type': 'string'}},
            'reason': {'type': 'string', 'description': '推荐理由'},
        }, 'required': ['candidate_ids']},
        responses={200: {'type': 'object', 'properties': {
            'success': {'type': 'boolean'},
            'data': {'type': 'object', 'properties': {
                'results': {'type': 'array'},
            }},
        }}},
    )
    @action(detail=True, methods=['post'], url_path='batch-recommend',
            permission_classes=[V2Permission])
    def batch_recommend(self, request, pk=None):
        """批量推荐候选人

        保持现有响应壳 {results: [{candidateId, success, recommendationId}]}。
        """
        process = self.get_object()
        candidate_ids = request.data.get('candidate_ids', [])
        reason = request.data.get('reason', '')

        if not candidate_ids:
            raise ValidationError('candidate_ids 不能为空')

        from apps.candidate.models import Candidate

        results = []
        for cid in candidate_ids:
            try:
                cand = Candidate.objects.get(pk=cid)
                rec = CandidateRecommendation.objects.create(
                    process=process,
                    candidate=cand,
                    reason=reason,
                    recommender=request.user,
                )
                results.append({
                    'candidate_id': cid,
                    'success': True,
                    'recommendation_id': rec.id,
                })
            except Candidate.DoesNotExist:
                results.append({
                    'candidate_id': cid,
                    'success': False,
                    'recommendation_id': None,
                    'error': 'CANDIDATE_NOT_FOUND',
                })

        return Response({
            'success': True,
            'data': {'results': results},
        })


# ============================================================
# 流程-阶段关联（ProcessStageLink）
# ============================================================
class ProcessStageLinkViewSet(viewsets.ModelViewSet):
    """流程-阶段关联 ViewSet"""
    queryset = ProcessStageLink.objects.all()
    serializer_class = ProcessStageLinkSerializer
    permission_classes = [HasProcessPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    # 2026-07-03: FE 用 ?processId= 调 list (axios 自动 camelCase),
    #   drf-camel-case 不转换 query string, 所以 django-filter 收到的 key 还是 'processId'.
    #   改成 'process_id' 让 drf-camel-case 的 JSON parser 把 'processId' 转成 'process_id'
    #   ... wait, query string 不走 JSON parser.
    #   实际方案: 加 custom filter 直接读 request.GET, 同时接受 'processId' 和 'process_id'.
    #   这里先用 'process_id' (FE 改 axios params 不转 camelCase, 或 FE 直接发 snake_case).
    #   -- 临时: 加 get_queryset 兜底, 兼容 processId / process_id / process 3 种 query key.
    filterset_fields = ['process_id', 'stage_id', 'is_required']
    ordering_fields = ['order', 'created_at']
    ordering = ['process', 'order']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        qs = qs.select_related('stage', 'process', 'stage_rule')
        # 2026-07-03: drf-camel-case 不处理 query string, FE 发 'processId' 不会被翻译.
        #   用 get_queryset 手动接受 processId / process_id / process 3 种 key 兜底.
        process_id = (
            self.request.query_params.get('processId')
            or self.request.query_params.get('process_id')
            or self.request.query_params.get('process')
        )
        if process_id:
            qs = qs.filter(process_id=process_id)
        stage_id = (
            self.request.query_params.get('stageId')
            or self.request.query_params.get('stage_id')
            or self.request.query_params.get('stage')
        )
        if stage_id:
            qs = qs.filter(stage_id=stage_id)
        return qs

    def perform_destroy(self, instance):
        # 系统必含起止阶段（START_END）不可删除：仅标软删会被「删了又建」绕过，
        # 直接业务拒绝（400）让 FE 明确收到「不可删除」语义。
        # 以 stage.is_start / is_end 为权威判据（覆盖存量数据 is_mandatory 可能为 False 的情况），
        # 同时兼容新建流程的 is_mandatory 标记。FE 隐藏删除按钮同样依据 stage.isStart/isEnd。
        if instance.is_mandatory or (instance.stage_id and (instance.stage.is_start or instance.stage.is_end)):
            raise ValidationError('系统必含阶段（起止阶段）不可删除')
        instance.soft_delete()

    @extend_schema(summary='重排阶段顺序')
    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """批量更新 stage_links 顺序
        Body: { "process_id": "...", "order": [{"link_id": "...", "order": 1}, ...] }

        起止边界强校验（BR-001 强化）：
        - 起始阶段(初评) 必须排在最前，且其后不可出现前序阶段
        - 结束阶段(正式录用) 必须排在最后，但其前可加前序阶段（其后不可再加）
        - 顺序值不可重复
        """
        process_id = request.data.get('process_id')
        order_data = request.data.get('order', [])
        if not process_id or not order_data:
            raise ValidationError('缺少 process_id 或 order')

        try:
            process = RecruitmentProcess.objects.get(id=process_id, deleted_at__isnull=True)
        except RecruitmentProcess.DoesNotExist:
            raise NotFound('流程不存在')

        links = ProcessStageLink.objects.filter(process=process, deleted_at__isnull=True)
        start_link = links.filter(stage__is_start=True).first()
        end_link = links.filter(stage__is_end=True).first()

        # 合并既有顺序与本次提交的新顺序，得到「预期最终顺序」
        new_order_map = {}
        for item in order_data:
            link_id = item.get('link_id')
            new_order = item.get('order')
            if link_id is None or new_order is None:
                continue
            new_order_map[link_id] = new_order

        effective = {l.id: new_order_map.get(l.id, l.order) for l in links}

        # 顺序不可重复（否则排序无意义且会破坏起止边界判定）
        if len(set(effective.values())) != len(effective):
            raise ValidationError('阶段顺序不可重复')

        min_order = min(effective.values())
        max_order = max(effective.values())

        # 起止阶段自身不可越出「最前 / 最后」锚点
        if start_link and effective.get(start_link.id) != min_order:
            raise ValidationError('起始阶段(初评)必须排在最前，不可被移动到其后')
        if end_link and effective.get(end_link.id) != max_order:
            raise ValidationError('结束阶段(正式录用)必须排在最后，不可被移动到其前')

        # 其它阶段必须严格落在 (start.order, end.order) 开区间内
        for l in links:
            if start_link and l.id == start_link.id:
                continue
            if end_link and l.id == end_link.id:
                continue
            o = effective[l.id]
            if start_link and o <= effective[start_link.id]:
                raise ValidationError('起始阶段(初评)前不可添加前序阶段')
            if end_link and o >= effective[end_link.id]:
                raise ValidationError('结束阶段(正式录用)后不可添加后续阶段')

        # 校验通过后再落库
        for l in links:
            new_order = effective[l.id]
            if new_order != l.order:
                ProcessStageLink.objects.filter(id=l.id).update(
                    order=new_order, updated_at=process.updated_at,
                )

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
    permission_classes = [HasProcessPermission]
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
# 面试轮次（InterviewRound）
# ============================================================
class InterviewRoundViewSet(AuditMixin, viewsets.ModelViewSet):
    """面试轮次库 ViewSet

    list:       列表（支持 keyword 搜索）
    create:     创建（自动生成 R+三位编号）
    update:     更新
    destroy:    软删除
    status:     切换启用/停用状态
    """
    queryset = InterviewRound.objects.all()
    permission_classes = [HasProcessPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'is_universal']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'created_at', 'updated_at']
    ordering = ['code']

    def get_serializer_class(self):
        if self.action == 'create':
            return InterviewRoundCreateSerializer
        return InterviewRoundSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        keyword = self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(
                Q(name__icontains=keyword)
                | Q(code__icontains=keyword)
                | Q(description__icontains=keyword)
            )
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()

    @extend_schema(
        summary='切换面试轮次状态',
        request={'type': 'object', 'properties': {'status': {'type': 'string', 'enum': ['ACTIVE', 'INACTIVE']}}},
        responses={200: InterviewRoundSerializer},
    )
    @action(detail=True, methods=['put'], url_path='status')
    def status(self, request, pk=None):
        instance = self.get_object()
        new_status = request.data.get('status')
        if new_status not in {'ACTIVE', 'INACTIVE'}:
            raise ValidationError({'status': '状态必须是 ACTIVE 或 INACTIVE'})
        instance.status = new_status
        instance.save(update_fields=['status', 'updated_at'])
        serializer = self.get_serializer(instance)
        return Response({'success': True, 'data': serializer.data})


# ============================================================
# 流程模板（ProcessTemplate）
# ============================================================
class ProcessTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """流程模板 - 只读 (由 seed/管理后台维护)"""
    queryset = ProcessTemplate.objects.filter(is_active=True)
    serializer_class = ProcessTemplateSerializer
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
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
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission.
    permission_classes = [V2Permission]

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


class EntryConditionFieldCatalogView(APIView):
    """进入条件字段目录 — 返回 source→condition_type→field→operator→value 字典树

    数据来源：apps/entry_condition/services.py:284-360 (_get_actual_value) 实际解析的字段
    （**非 demo**）：
    - STAGE_STATUS：来自 RecruitmentStage 表（value_source=STAGE_LIST，动态取已启用阶段名）
    - CANDIDATE：来自 Candidate 模型硬编码字段映射（AGE/GENDER/HIGHEST_EDU/WORK_YEARS/CITY）
    - DEMAND：来自 Position/Demand 硬编码字段映射（用人经理/上级/BU总裁/VP/职级/部门）
    运算符直接对齐 apps/entry_condition/models.py:33 ConditionOperator 文案。
    """
    permission_classes = [HasProcessPermission]

    def get(self, request):
        from apps.entry_condition.models import ConditionOperator

        common_operators = [
            ConditionOperator.EQ.value, ConditionOperator.NEQ.value,
            ConditionOperator.GT.value, ConditionOperator.GTE.value,
            ConditionOperator.LT.value, ConditionOperator.LTE.value,
            ConditionOperator.BETWEEN.value,
            ConditionOperator.IN.value, ConditionOperator.NOT_IN.value,
            ConditionOperator.IS_EMPTY.value, ConditionOperator.IS_NOT_EMPTY.value,
        ]

        sources = [
            {
                'key': 'DEMAND', 'label': '需求中', 'condition_type': 'DEMAND',
                'fields': [
                    {'key': 'HIRING_MANAGER', 'label': '用人经理',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'USER_LIST', 'value_hint': '自动过滤离职人员'},
                    {'key': 'HIRING_MANAGER_SUPER', 'label': '用人经理上级',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'USER_LIST', 'value_hint': '自动过滤离职人员'},
                    {'key': 'BU_PRESIDENT', 'label': 'BU 总裁',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'USER_LIST', 'value_hint': '自动过滤离职人员'},
                    {'key': 'SOLID_VP', 'label': '实线 VP',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'USER_LIST', 'value_hint': '自动过滤离职人员'},
                    {'key': 'DOTTED_VP', 'label': '虚线 VP',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'USER_LIST', 'value_hint': '自动过滤离职人员'},
                    {'key': 'DEMAND_LEVEL', 'label': '需求职级',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'DICT:demand_level'},
                    {'key': 'DEPARTMENT', 'label': '部门',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'DICT:department'},
                ],
            },
            {
                'key': 'CANDIDATE', 'label': '候选人中', 'condition_type': 'CANDIDATE',
                'fields': [
                    {'key': 'AGE', 'label': '年龄',
                     'operators': ['GT', 'GTE', 'LT', 'LTE', 'BETWEEN', 'EQ'],
                     'value_source': 'NUMBER'},
                    {'key': 'GENDER', 'label': '性别',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'DICT:gender'},
                    {'key': 'HIGHEST_EDU', 'label': '最高学历',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'DICT:highest_education'},
                    {'key': 'WORK_YEARS', 'label': '工作年限',
                     'operators': ['GT', 'GTE', 'LT', 'LTE', 'BETWEEN'],
                     'value_source': 'NUMBER'},
                    {'key': 'CURRENT_CITY', 'label': '当前城市',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'DICT:city'},
                    {'key': 'EXPECTED_CITY', 'label': '期望城市',
                     'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN'],
                     'value_source': 'DICT:city'},
                ],
            },
            {
                'key': 'STAGE_STATUS', 'label': '阶段状态', 'condition_type': 'STAGE_STATUS',
                'fields': [
                    {
                        'key': 'STAGE_NAME', 'label': '关联阶段名',
                        'operators': ['EQ', 'NEQ', 'IN', 'NOT_IN', 'IS_EMPTY', 'IS_NOT_EMPTY'],
                        'value_source': 'STAGE_LIST',
                        'value_hint': '候选人从前序阶段的评估结果',
                    }
                ],
            },
        ]
        return Response({
            'success': True,
            'data': {
                'sources': sources,
                'common_operators': common_operators,
            },
        })


# ============================================================
# 应用流程模板
# ============================================================
class ProcessApplyTemplateView(APIView):
    """应用流程模板创建新流程"""
    permission_classes = [HasProcessPermission]

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
