"""Application Views (PRD v4 §6, §13, §14.4)

API Endpoints:
- GET    /api/v1/applications/                申请列表
- POST   /api/v1/applications/                创建申请
- GET    /api/v1/applications/{id}/           申请详情
- POST   /api/v1/applications/{id}/start/     启动
- POST   /api/v1/applications/{id}/advance/  推进
- POST   /api/v1/applications/{id}/jump/     跳过到指定阶段
- POST   /api/v1/applications/{id}/soft-reject/  软拒
- POST   /api/v1/applications/{id}/withdraw/  撤回
- POST   /api/v1/applications/{id}/pause/    暂停
- POST   /api/v1/applications/{id}/resume/   恢复
- POST   /api/v1/applications/{id}/upgrade-version/ 升版本
- POST   /api/v1/applications/{id}/change-process/  跨流程线迁移
- POST   /api/v1/applications/{id}/grab/     抢单认领
- POST   /api/v1/applications/{id}/release/  抢单释放
- GET    /api/v1/applications/{id}/histories/ 操作历史
- GET    /api/v1/applications/{id}/records/  阶段记录

- GET    /api/v1/grab-pool/                  抢单池        (URLconf: urls_grab_pool.py)
- POST   /api/v1/grab-pool/reassign/         抢单超时重分配（管理员）
- GET    /api/v1/grab-pool/summary/          抢单池汇总

⚠️ 2026-08-06 寇豆码: 本模块的 InvitationViewSet 已从 URLconf 摘除 —
   /api/v1/invitations/ 统一由 apps/invitation/urls.py + apps/invitation/views.InvitationViewSet
   提供。原因：两处同名同 basename='invitation' 注册会造成 URL name 冲突（reverse 结果
   取决于注册顺序），且本类的 list/create/respond/send 路由本就被同一 router 上先注册的
   ApplicationViewSet 的 `^$` / `^(?P<id>[^/.]+)/$` 吃掉，长期不可达（仅 by-code/{code}/
   因为是两段路径而侥幸可达）。类保留（InvitationService 逻辑仍可复用），不再暴露 HTTP 路由。
"""
from __future__ import annotations

import logging

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.exceptions import NotFound, StateTransitionError
from apps.common.mixins import SoftDeleteViewSetMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.common.search import keyword_q
from apps.common.views import EnvelopeWriteMixin
from apps.core.permissions import IsHROrAbove
from apps.core.permissions_v2 import ScopeQuerysetMixin, V2Permission

from .models import Application
from .serializers import (
    ApplicationAdvanceSerializer,
    ApplicationChangeProcessSerializer,
    ApplicationCreateSerializer,
    ApplicationDetailSerializer,
    ApplicationGrabSerializer,
    ApplicationHistorySerializer,
    ApplicationJumpSerializer,
    ApplicationListSerializer,
    ApplicationPauseSerializer,
    ApplicationReleaseSerializer,
    ApplicationSoftRejectSerializer,
    ApplicationStageRecordSerializer,
    ApplicationWithdrawSerializer,
    GrabPoolQuerySerializer,
    InvitationCreateSerializer,
    InvitationRespondSerializer,
)
from .services import (
    ApplicationCreateData,
    ApplicationService,
)
from .services.grab import GrabService, InvitationService
from .services.soft_reject import SoftRejectService

logger = logging.getLogger(__name__)


class ApplicationViewSet(EnvelopeWriteMixin, ScopeQuerysetMixin, SoftDeleteViewSetMixin, viewsets.ModelViewSet):
    """申请 ViewSet - 按职位部门 scope 过滤 (Fix 1)"""
    queryset = Application.objects.filter(deleted_at__isnull=True).select_related(
        'candidate', 'position', 'process', 'current_link', 'current_stage', 'grabbed_by',
        # #9 (2026-10-09): ApplicationListSerializer.get_is_in_grab_pool 逐行访问
        # obj.current_link.stage_rule.is_grab_mode, 列表 N 行 -> N 次查询。
        'current_link__stage_rule',
    )
    permission_classes = [V2Permission]
    permission_required = 'recruit:application:list'
    pagination_class = StandardResultsSetPagination
    lookup_field = 'id'
    scope_field = 'position__department'
    scope_creator_field = 'created_by'

    def get_serializer_class(self):
        if self.action == 'list':
            return ApplicationListSerializer
        return ApplicationDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 状态筛选
        state = self.request.query_params.get('state')
        if state:
            qs = qs.filter(state=state)
        # 候选人
        candidate_id = self.request.query_params.get('candidate')
        if candidate_id:
            qs = qs.filter(candidate_id=candidate_id)
        # 职位
        position_id = self.request.query_params.get('position')
        if position_id:
            qs = qs.filter(position_id=position_id)
        # 当前阶段
        stage_id = self.request.query_params.get('stage')
        if stage_id:
            qs = qs.filter(current_stage_id=stage_id)
        # 抢单人
        grabbed_by = self.request.query_params.get('grabbed_by')
        if grabbed_by:
            qs = qs.filter(grabbed_by_id=grabbed_by)
        # 关键词
        keyword = self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(keyword_q(keyword, 'code', 'candidate__name', 'position__title'))
        # IDOR scope (Fix 1)
        qs = self.scope_queryset(qs)
        return qs.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """创建申请"""
        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        data = ApplicationCreateData(
            candidate_id=v['candidate_id'],
            position_id=v['position_id'],
            process_id=v.get('process_id') or None,
            initial_stage_id=v.get('initial_stage_id') or None,
            actor=request.user,
            extra=v.get('extra'),
        )
        try:
            application = ApplicationService.create_application(data)
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        except NotFound as e:
            return Response(
                {'error': str(e), 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(
            ApplicationDetailSerializer(application).data,
            status_code=status.HTTP_201_CREATED,
        )

    # ----------------------------------------------------------
    # 启动
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, id=None):
        """启动申请 (PENDING → ACTIVE)"""
        application = self.get_object()
        try:
            application = ApplicationService.start_application(application, actor=request.user)
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ApplicationDetailSerializer(application).data)

    # ----------------------------------------------------------
    # 推进
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='advance')
    def advance(self, request, id=None):
        """推进到下一阶段"""
        application = self.get_object()
        serializer = ApplicationAdvanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        try:
            result = ApplicationService.advance_application_to_next_stage(
                application,
                actor=request.user,
                skip_entry_condition=v.get('skip_entry_condition', False),
                reason=v.get('reason', ''),
            )
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({
            'application': ApplicationDetailSerializer(result.application).data,
            'from_stage_id': result.from_stage_id,
            'to_stage_id': result.to_stage_id,
            'to_stage_name': result.to_stage_name,
            'record_id': result.record.id,
        })

    # ----------------------------------------------------------
    # 阶段流转预检 (dry-run advance)  ← G38, 2026-06-17
    # FE: checkApplicationStageTransition(applicationId, entryConditionId?)
    # 返回 {allowed, reason?, prompt?} — 不实际推进, 只评估下一阶段的 entry condition.
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='check-stage-transition')
    def check_stage_transition(self, request, id=None):
        """检查能否推进到下一阶段(不实际推进)"""
        from apps.entry_condition.models import EntryConditionRule
        from apps.entry_condition.services import evaluate_stage_entry
        from apps.process.models import ProcessStageLink

        application = self.get_object()
        entry_condition_id = (request.data or {}).get('entryConditionId')

        # 找下一 link (跟 advance_application_to_next_stage 同款查询)
        if not application.current_link:
            return Response({'success': True, 'data': {'allowed': False, 'reason': 'no_current_link'}})
        next_link = ProcessStageLink.objects.filter(
            process=application.process,
            order__gt=application.current_link.order,
            deleted_at__isnull=True,
        ).order_by('order').first()
        if not next_link:
            return Response({'success': True, 'data': {'allowed': False, 'reason': 'no_next_stage'}})

        # 如果 FE 指定了特定 entryConditionId, 用它的 link; 否则用 next_link
        if entry_condition_id:
            try:
                rule = EntryConditionRule.objects.get(id=entry_condition_id, deleted_at__isnull=True)
                eval_link = rule.link
            except EntryConditionRule.DoesNotExist:
                return Response(
                    {'success': False, 'code': 'entry_condition_not_found', 'message': '进入条件规则不存在'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            eval_link = next_link

        try:
            result = evaluate_stage_entry(eval_link, application.candidate)
        except Exception as e:  # noqa: BLE001 — 进入条件评估异常必须返 500 (evaluate 内部已用 narrow set, 此处是最终兜底)
            logger.exception('check_stage_transition: evaluate failed: %s', e)
            return Response(
                {'success': False, 'code': 'evaluation_error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            'success': True,
            'data': {
                'allowed': result.overall_passed,
                'reason': None if result.overall_passed else 'entry_condition_not_met',
                'prompt': result.reject_message or None,
            },
        })

    # ----------------------------------------------------------
    # 跳过到指定阶段
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='jump')
    def jump(self, request, id=None):
        """跳过到指定阶段"""
        application = self.get_object()
        serializer = ApplicationJumpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        try:
            result = ApplicationService.jump_application_to_stage(
                application,
                target_stage_id=v['target_stage_id'],
                actor=request.user,
                skip_entry_condition=v.get('skip_entry_condition', False),
                reason=v.get('reason', ''),
            )
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        except NotFound as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            'application': ApplicationDetailSerializer(result.application).data,
            'from_stage_id': result.from_stage_id,
            'to_stage_id': result.to_stage_id,
            'to_stage_name': result.to_stage_name,
        })

    # ----------------------------------------------------------
    # 软拒
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='soft-reject')
    def soft_reject(self, request, id=None):
        """软拒当前阶段（保留历史）"""
        application = self.get_object()
        serializer = ApplicationSoftRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                application = ApplicationService.soft_reject(
                    application, reason=serializer.validated_data['reason'],
                    actor=request.user,
                )
                # 检查是否触发入人才库
                SoftRejectService.check_threshold_and_pool(
                    application.candidate_id, application.process_id,
                    application.current_stage_id, actor=request.user,
                )
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ApplicationDetailSerializer(application).data)

    # ----------------------------------------------------------
    # 撤回
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='withdraw')
    def withdraw(self, request, id=None):
        """候选人主动撤回"""
        application = self.get_object()
        serializer = ApplicationWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = ApplicationService.withdraw(
                application, reason=serializer.validated_data['reason'],
                actor=request.user,
            )
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ApplicationDetailSerializer(application).data)

    # ----------------------------------------------------------
    # 暂停 / 恢复
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='pause')
    def pause(self, request, id=None):
        """暂停"""
        application = self.get_object()
        serializer = ApplicationPauseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = ApplicationService.pause(
                application, reason=serializer.validated_data.get('reason', ''),
                actor=request.user,
            )
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ApplicationDetailSerializer(application).data)

    @action(detail=True, methods=['post'], url_path='resume')
    def resume(self, request, id=None):
        """恢复"""
        application = self.get_object()
        try:
            application = ApplicationService.resume(
                application, actor=request.user,
            )
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ApplicationDetailSerializer(application).data)

    # ----------------------------------------------------------
    # 升版本
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='upgrade-version')
    def upgrade_version(self, request, id=None):
        """升版本（BR-104）"""
        application = self.get_object()
        try:
            application = ApplicationService.upgrade_workflow_version(
                application, actor=request.user,
            )
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ApplicationDetailSerializer(application).data)

    # ----------------------------------------------------------
    # 跨流程线迁移
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='change-process')
    def change_process(self, request, id=None):
        """跨流程线迁移（§3.1）

        与 upgrade-version 的分工：同 code 换版本走 upgrade-version（服务端算落点），
        跨 code 换流程线走这里（落点由操作员显式指定，服务端只校验）。

        状态码分工：
        - 400：入参形态不合法（缺 target_process_id / target_stage_id / reason，或 reason 空白）
        - 404：target_process_id / target_stage_id 指向不存在（或已软删）的行
        - 409：业务校验不通过（同流程 / 目标已归档 / 阶段不属于目标流程 / 目标已软删）
        """
        from apps.process.models import ProcessStageLink, RecruitmentProcess

        application = self.get_object()
        serializer = ApplicationChangeProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data

        # 软删过滤必写：§1.5 跨模块约定。漏掉会让已删除的流程/阶段被选成迁移目标，
        # 且服务层的 deleted_at 兜底只在对象真被取出来时才生效。
        try:
            target_process = RecruitmentProcess.objects.get(
                id=v['target_process_id'], deleted_at__isnull=True,
            )
        except RecruitmentProcess.DoesNotExist as e:
            raise NotFound(f'Process {v["target_process_id"]} not found') from e
        try:
            target_stage_link = ProcessStageLink.objects.select_related('stage').get(
                id=v['target_stage_id'], deleted_at__isnull=True,
            )
        except ProcessStageLink.DoesNotExist as e:
            raise NotFound(f'Stage link {v["target_stage_id"]} not found') from e

        try:
            application = ApplicationService.change_process(
                application,
                target_process=target_process,
                target_stage_link=target_stage_link,
                actor=request.user,
                reason=v['reason'],
            )
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ApplicationDetailSerializer(application).data)

    # ----------------------------------------------------------
    # 抢单
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='grab')
    def grab(self, request, id=None):
        """抢单认领"""
        application = self.get_object()
        serializer = ApplicationGrabSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = GrabService.grab(application, request.user)
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({
            'application': ApplicationDetailSerializer(result.application).data,
            'grabbed_by': result.grabbed_by.username if result.grabbed_by else None,
        })

    @action(detail=True, methods=['post'], url_path='release')
    def release(self, request, id=None):
        """释放抢单"""
        application = self.get_object()
        serializer = ApplicationReleaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = GrabService.release(
                application, request.user,
                reason=serializer.validated_data.get('reason', ''),
            )
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ApplicationDetailSerializer(application).data)

    # ----------------------------------------------------------
    # 操作历史 / 阶段记录
    # ----------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='histories')
    def histories(self, request, id=None):
        """操作历史"""
        application = self.get_object()
        histories = application.histories.filter(deleted_at__isnull=True)
        action_type = request.query_params.get('action')
        if action_type:
            histories = histories.filter(action=action_type)
        page = self.paginate_queryset(histories)
        if page is not None:
            serializer = ApplicationHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ApplicationHistorySerializer(histories, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='records')
    def records(self, request, id=None):
        """所有阶段记录"""
        application = self.get_object()
        records = application.stage_records.filter(deleted_at__isnull=True)
        state = request.query_params.get('state')
        if state:
            records = records.filter(state=state)
        records = records.order_by('entered_at')
        page = self.paginate_queryset(records)
        if page is not None:
            serializer = ApplicationStageRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ApplicationStageRecordSerializer(records, many=True)
        return Response(serializer.data)

    # ----------------------------------------------------------
    # 二次投递建议
    # ----------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='reapply-suggest')
    def reapply_suggest(self, request):
        """建议二次投递的初始阶段"""
        candidate_id = request.query_params.get('candidate_id')
        position_id = request.query_params.get('position_id')
        if not candidate_id or not position_id:
            return Response(
                {'error': 'candidate_id and position_id are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.position.models import Position
        try:
            position = Position.objects.get(id=position_id, deleted_at__isnull=True)
        except Position.DoesNotExist:
            return Response(
                {'error': 'position not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        stage_links = position.process.stage_links.filter(
            deleted_at__isnull=True, is_required=True,
        ).order_by('order')
        suggested = SoftRejectService.suggest_reapply_initial_stage(
            candidate_id, position_id, list(stage_links),
        )
        rejected_stages = SoftRejectService.get_rejected_stages(candidate_id, position_id)
        return Response({
            'suggested_stage_id': suggested.stage_id if suggested else None,
            'suggested_stage_name': suggested.stage.name if suggested else None,
            'rejected_stage_ids': rejected_stages,
        })


class GrabPoolViewSet(viewsets.GenericViewSet):
    """抢单池 ViewSet

    2026-08-06 寇豆码: 原来继承 viewsets.ViewSet（APIView 系），它**没有**
    paginate_queryset / get_paginated_response —— 那两个方法来自 GenericAPIView，
    所以 list() 里的 `self.paginate_queryset(apps)` 必然 AttributeError → 500。
    之前因为整个 ViewSet 的路由被 ApplicationViewSet 吃掉，这个 500 从未被触发。
    改继承 GenericViewSet 后声明的 pagination_class 才真正生效。
    queryset/serializer_class 显式声明：list() 虽直接用 GrabService 取数不走
    get_queryset()，但 drf-spectacular 生成 schema 时会访问，避免告警。
    """
    permission_classes = [IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    queryset = Application.objects.none()
    serializer_class = ApplicationListSerializer

    def list(self, request):
        """抢单池列表"""
        serializer = GrabPoolQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        apps = GrabService.get_pool(
            stage_id=v.get('stage_id') or None,
            position_id=v.get('position_id') or None,
            limit=v.get('limit', 50),
        )
        # 2026-08-07 寇豆码: 改用 self.get_serializer(...) 取代裸 ApplicationListSerializer(...)。
        # 根因: 裸实例化不带 context，get_candidate_phone 取不到 request.user 直接走脱敏分支，
        # 导致 grab-pool 端点对超管也返回掩码号码，与 applications 端点语义分叉。
        # self.get_serializer 自动注入 {'request','view','format'} context，与 ApplicationViewSet.list()
        # （DRF ListModelMixin 走 self.get_serializer）完全一致，从根本上保证两边行为统一。
        page = self.paginate_queryset(apps)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(self.get_serializer(apps, many=True).data)

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """抢单池汇总"""
        return Response(GrabService.get_grab_pool_summary())

    @action(detail=False, methods=['post'], url_path='reassign')
    def reassign(self, request):
        """抢单超时重分配"""
        threshold = int(request.data.get('threshold_minutes', 30))
        results = GrabService.reassign_overdue(threshold_minutes=threshold)
        return Response({
            'reassigned_count': len(results),
            'threshold_minutes': threshold,
            'results': [
                {
                    'application_code': r.application.code,
                    'grabbed_by': r.grabbed_by.username if r.grabbed_by else None,
                }
                for r in results
            ],
        })


class InvitationViewSet(viewsets.ViewSet):
    """邀请 ViewSet"""
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
    # 2026-10-08: 写操作显式授权。respond 是候选人/面试官回填响应, 只需「可见邀请」即可,
    #   过度收紧会让候选人无法应答; create/send 才有实际副作用, 要求 invitation:create。
    permission_required_map = {
        'create': 'recruit:invitation:create',
        'send_invitation': 'recruit:invitation:create',
        'respond': 'recruit:invitation:list',
    }

    def create(self, request):
        """创建邀请"""
        from .services.grab import InvitationCreateData
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        data = InvitationCreateData(
            application_id=v['application_id'],
            channel=v.get('channel', 'EMAIL'),
            template_code=v.get('template_code'),
            sender_id=str(request.user.id) if request.user else None,
            custom_message=v.get('custom_message'),
            expires_hours=v.get('expires_hours', 72),
        )
        try:
            result = InvitationService.create_invitation(data)
        except NotFound as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'invitation_id': result.invitation_id,
            'code': result.code,
            'url': result.url,
            'expires_at': result.expires_at,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='send')
    def send_invitation(self, request, pk=None):
        """发送邀请"""
        try:
            result = InvitationService.send_invitation(pk)
        except NotFound as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except StateTransitionError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(result)

    @action(detail=False, methods=['get'], url_path='by-code/(?P<code>[^/]+)')
    def by_code(self, request, code=None):
        """按 code 查询邀请"""
        try:
            result = InvitationService.get_invitation_by_code(code)
        except NotFound as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response(result)

    @action(detail=False, methods=['post'], url_path='respond')
    def respond(self, request):
        """候选人响应"""
        serializer = InvitationRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        try:
            result = InvitationService.respond_invitation(
                code=v['code'], accept=v['accept'], note=v.get('note', ''),
            )
        except NotFound as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except StateTransitionError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(result)
