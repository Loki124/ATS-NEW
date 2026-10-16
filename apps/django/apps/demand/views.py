
"""Demand Views (DRF) - PRD v4 §14.1"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import NotFound, ValidationError
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permission_check import has_perm
from apps.core.permissions_v2 import V2Permission
from apps.core.viewsets import BaseModelViewSet
from apps.process.models import RecruitmentProcess

from .models import Demand, DemandApproval, DemandSetting
from .serializers import (
    DemandApprovalSerializer,
    DemandCreateSerializer,
    DemandDetailSerializer,
    DemandListSerializer,
    DemandRebindProcessSerializer,
    DemandTransitionSerializer,
    DemandUpgradeProcessSerializer,
)
from .services import DemandCreateData, DemandService
from apps.data_permission.enforcement import ensure_writable  # M07 写范围守卫


class DemandViewSet(BaseModelViewSet):
    """招聘需求 ViewSet - 按部门 scope 过滤"""
    queryset = Demand.objects.all().order_by('-created_at')
    permission_classes = [V2Permission]
    permission_required = 'recruit:demand:list'
    # G1: seed 定义的审批码在此真实消费。此前 transition 作为自定义 action 一律按
    # 派生码 recruit:demand:edit 校验，导致身份管理里单独勾「审批需求」不生效。
    # 类级 map 放行持有 approve/edit 任一码的请求进入 action，再按 FSM 动作细查。
    permission_required_map = {
        'transition': ['recruit:demand:approve', 'recruit:demand:edit'],
        # 2026-10-16: 改绑流程属需求编辑的一部分，沿用 :edit 派生码。
        # 显式列出而非依赖派生，是因为它是跨实体写入（改动 Position.process），
        # 将来若要拆独立权限码，这里是唯一改动点。
        'rebind_process': ['recruit:demand:edit'],
    }
    # 审批人决策动作（PENDING 阶段的 approve/reject）→ 审批码；
    # 其余动作（submit/start_recruiting/pause/...）按 :edit 校验
    TRANSITION_ACTION_PERM = {
        'approve': 'recruit:demand:approve',
        'reject': 'recruit:demand:approve',
    }
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    # 2026-10-16: 加 process —— 流程配置页「改绑引用」入口要按流程反查需求，
    # 否则前端只能拉全量再本地过滤，既漏（受分页截断）又慢。
    filterset_fields = [
        'state', 'department', 'hr', 'requested_by', 'priority', 'approval_status', 'process',
    ]
    search_fields = ['code', 'title', 'position_title']
    ordering_fields = ['code', 'created_at', 'submitted_at']
    ordering = ['-created_at']
    scope_field = 'department'
    scope_creator_field = 'requested_by'
    # M02: 数据权限 CUSTOM 规则的模块 key (ViewSet 只声明类属性, 零逻辑).
    data_perm_entity = 'demand'

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
        if self.action == 'rebind_process':
            return DemandRebindProcessSerializer
        return DemandDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        qs = qs.select_related('department', 'requested_by', 'hr', 'process')
        qs = qs.prefetch_related('positions')
        # IDOR scope 过滤 (Fix 1)
        qs = self.scope_queryset(qs)
        return qs

    def perform_destroy(self, instance):
        # 软删除
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    def perform_create(self, serializer):
        """建需求：委托 DemandService.create_demand 统一创建（收口 TODO-A 分叉）。

        前端建需求表单仅收集 title / department / headcount 等业务字段，不收集
        提出人 / 负责HR / 流程（无流程选择器）。这些服务端已知项在此统一填充，
        既避免信任客户端伪造提出人，也保证 process FK 必填可满足。

        此前本方法把「编号生成 + process 选取 + FK 填充 + 审计注入」内联重写在
        视图里，与 DemandService.create_demand 形成 API↔Service 分叉：两处逻辑
        漂移、软删过滤与审计要求各自维护。现统一收口到 Service 单一来源，
        created_by / updated_by 由 Service 写入（同 AuditMixin 语义），更新路径仍
        由 AuditMixin.perform_update 注入 updated_by，不受影响。
        """
        user = self.request.user
        vd = serializer.validated_data
        process = (
            RecruitmentProcess.objects
            .filter(is_latest=True, status='ENABLED', deleted_at__isnull=True)
            .first()
            or RecruitmentProcess.objects.filter(deleted_at__isnull=True).first()
        )
        if process is None:
            # Demand.process 为 NOT NULL：无可用流程时创建本就非法，显式 400 而非
            # 让 serializer.save(process=None) 撞库约束 500（旧实现 latent 缺陷）。
            raise ValidationError('无可用招聘流程，无法创建需求')
        data = DemandCreateData(
            title=vd.get('title', ''),
            department_id=str(vd['department'].id),
            requested_by_id=user.id,
            hr_id=user.id,
            headcount=vd.get('headcount', 1),
            process_id=process.id,
            level=vd.get('level', ''),
            position_title=vd.get('position_title', ''),
            jd=vd.get('jd', ''),
            requirements=vd.get('requirements', ''),
            priority=vd.get('priority', 'P1'),
            demand_type=vd.get('demand_type', 'SOCIAL'),
            # 2026-10-12 字段结构对齐规范: 透传新增预置列
            talent_level=vd.get('talent_level', ''),
            talent_nature=vd.get('talent_nature', ''),
            date_range=vd.get('date_range') or [],
            sharers=vd.get('sharers') or [],
            # 写入守卫: recruit_type 由请求上下文(中间件按 X-Recruit-Type 注入)权威决定,
            # 覆盖模型列默认值。否则新建需求恒落 'social', 在 campus 系统下被读侧分区过滤掉,
            # 表现为"创建成功但列表不显示"。
            recruit_type=getattr(self.request, 'recruit_type', 'social'),
            actor=user,
        )
        demand = DemandService.create_demand(data)
        serializer.instance = demand

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        """状态机流转：submit/approve/reject/start_recruiting/pause/resume/complete/cancel"""
        instance = self.get_object()
        ensure_writable(request.user, 'demand', instance, action='transition')
        serializer = DemandTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']
        # 细粒度校验：审批动作要求审批码，其余流转动作要求 :edit（G1）
        required = self.TRANSITION_ACTION_PERM.get(action_name, 'recruit:demand:edit')
        if not has_perm(request.user, required):
            raise PermissionDenied(f'无权执行该操作，缺少权限码 {required}')
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

    @action(detail=True, methods=['post'], url_path='rebind-process')
    def rebind_process(self, request, pk=None):
        """需求改绑到另一条流程线（方案 A，2026-10-16）。

        与 ``upgrade_process_version`` 的分工：upgrade 是**同 code 线内**升到最新版；
        本 action 是**跨 code 换流程**，换掉整套阶段编排。

        契约：
        - 成功 → 200，``rebound=true``，``moved_position_ids`` 为实际改指的职位 id
        - 目标与当前已是同一行 → 200 幂等（``rebound=false``）
        - 目标不存在 / 已归档 / 非最新版 / 跨线有在跑候选人 → 409（StateTransitionError）

        **不动 Application**：BR-102 硬红线，在跑候选人继续走创建时的版本。
        """
        instance = self.get_object()
        ensure_writable(request.user, 'demand', instance, action='edit')

        serializer = DemandRebindProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_process = RecruitmentProcess.objects.filter(
            id=serializer.validated_data['target_process_id'],
            deleted_at__isnull=True,
        ).first()
        if target_process is None:
            raise NotFound(f'流程 {serializer.validated_data["target_process_id"]} 不存在')

        old_process_id = instance.process_id  # §1.3.2：快照早于任何赋值
        demand, moved = DemandService.rebind_demand_process(
            instance, target_process=target_process, actor=request.user,
        )
        out = DemandDetailSerializer(demand, context={'request': request})
        return Response({
            'success': True,
            'data': {
                'demand': out.data,
                'moved_position_ids': moved,
                'rebound': demand.process_id != old_process_id,
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


class DemandConfigView(APIView):
    """招聘需求设置全局配置端点 —— FE DemandConfig.vue 调用

    GET  /api/v1/system/config/demand  → {success:True, data:<config dict>}
    POST /api/v1/system/config/demand  → 保存整份 form，回显 {success:True, data}
    PUT  /api/v1/system/config/demand  → 同 POST

    说明：config 以 JSONField 自由 dict 存储，与前端 formData 同构。
    camel-case 解析器入参 snake 化、渲染器出参 camel 化，round-trip 安全。
    """

    permission_classes = [V2Permission]
    # 读按列表码; PUT/POST 走派生 :edit (demand-config:edit)
    permission_required = 'recruit:settings:demand-config:list'

    @staticmethod
    def _get_or_create():
        obj, _ = DemandSetting.objects.get_or_create(key='demand')
        return obj

    def get(self, request):
        obj = self._get_or_create()
        return Response({'success': True, 'data': obj.config or {}})

    def post(self, request):
        obj = self._get_or_create()
        obj.config = request.data
        if request.user and request.user.is_authenticated:
            obj.updated_by = request.user
        obj.save()
        return Response({'success': True, 'data': obj.config})

    def put(self, request):
        return self.post(request)