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
- POST   /api/v1/applications/{id}/grab/     抢单认领
- POST   /api/v1/applications/{id}/release/  抢单释放
- GET    /api/v1/applications/{id}/histories/ 操作历史
- GET    /api/v1/applications/{id}/records/  阶段记录

- GET    /api/v1/grab-pool/                  抢单池
- POST   /api/v1/grab-pool/reassign/         抢单超时重分配（管理员）
- GET    /api/v1/grab-pool/summary/          抢单池汇总

- POST   /api/v1/invitations/                创建邀请
- POST   /api/v1/invitations/{id}/send/      发送
- GET    /api/v1/invitations/by-code/{code}/  按 code 查询
- POST   /api/v1/invitations/respond/        候选人响应
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import NotFound, StateTransitionError
from apps.common.mixins import SoftDeleteViewSetMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsHROrAbove

from .models import Application, ApplicationHistory, ApplicationStageRecord
from .serializers import (
    ApplicationAdvanceSerializer,
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


class ApplicationViewSet(SoftDeleteViewSetMixin, viewsets.ModelViewSet):
    """申请 ViewSet"""
    queryset = Application.objects.filter(deleted_at__isnull=True).select_related(
        'candidate', 'position', 'process', 'current_link', 'current_stage', 'grabbed_by',
    )
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    lookup_field = 'id'

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
            qs = qs.filter(
                Q(code__icontains=keyword) |
                Q(candidate__name__icontains=keyword) |
                Q(position__title__icontains=keyword),
            )
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
        return Response(
            ApplicationDetailSerializer(application).data,
            status=status.HTTP_201_CREATED,
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
            application = ApplicationService.withdraw_application(
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
            application = ApplicationService.pause_application(
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
            application = ApplicationService.resume_application(
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


class GrabPoolViewSet(viewsets.ViewSet):
    """抢单池 ViewSet"""
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination

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
        page = self.paginate_queryset(apps)
        if page is not None:
            serializer = ApplicationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(ApplicationListSerializer(apps, many=True).data)

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
    permission_classes = [IsAuthenticated]

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
