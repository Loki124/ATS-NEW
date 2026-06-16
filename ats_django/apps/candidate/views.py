"""Candidate Views (PRD v4 §14.3)

API Endpoints:
- GET    /api/v1/candidates/                  候选人列表
- POST   /api/v1/candidates/                  创建候选人
- GET    /api/v1/candidates/{id}/             候选人详情
- PATCH  /api/v1/candidates/{id}/             更新候选人基本信息
- DELETE /api/v1/candidates/{id}/             软删除
- POST   /api/v1/candidates/{id}/transition/  状态机转换
- GET    /api/v1/candidates/{id}/histories/   操作历史
- GET    /api/v1/candidates/{id}/applications/ 该候选人所有申请
- POST   /api/v1/candidates/merge/            合并重复候选人
- POST   /api/v1/candidates/import/           批量导入
- POST   /api/v1/candidates/moka-sync/        摩卡同步
- GET    /api/v1/candidate-tags/              标签字典
- POST   /api/v1/candidates/search/           高级搜索
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import StateTransitionError
from apps.common.mixins import SoftDeleteViewSetMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsHROrAbove

from .models import Candidate, CandidateTag
from .serializers import (
    CandidateCreateSerializer,
    CandidateDetailSerializer,
    CandidateHistorySerializer,
    CandidateImportSerializer,
    CandidateListSerializer,
    CandidateMergeSerializer,
    CandidateMokaSyncSerializer,
    CandidateStateTransitionSerializer,
    CandidateTagSerializer,
    CandidateUpdateSerializer,
)
from .services import CandidateService

logger = logging.getLogger(__name__)


class CandidateViewSet(SoftDeleteViewSetMixin, viewsets.ModelViewSet):
    """候选人 ViewSet"""
    queryset = Candidate.objects.filter(deleted_at__isnull=True).select_related(
        'source_channel', 'referrer',
    )
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.action == 'list':
            return CandidateListSerializer
        if self.action in ('create', 'import_candidates'):
            return CandidateCreateSerializer
        if self.action in ('update', 'partial_update'):
            return CandidateUpdateSerializer
        return CandidateDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 状态筛选
        state = self.request.query_params.get('state')
        if state:
            qs = qs.filter(current_state=state)
        # 来源筛选
        source = self.request.query_params.get('source_channel')
        if source:
            qs = qs.filter(source_channel_id=source)
        # 推荐人
        referrer = self.request.query_params.get('referrer')
        if referrer:
            qs = qs.filter(referrer_id=referrer)
        # 关键词
        keyword = self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(
                Q(name__icontains=keyword) |
                Q(phone__icontains=keyword) |
                Q(email__icontains=keyword) |
                Q(current_company__icontains=keyword),
            )
        # 黑名单
        blacklisted = self.request.query_params.get('blacklisted')
        if blacklisted is not None:
            qs = qs.filter(is_blacklisted=blacklisted.lower() == 'true')
        return qs.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """创建候选人（含幂等查重）"""
        serializer = CandidateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.to_data()
        candidate = CandidateService.create_candidate(data, actor=request.user)
        out = CandidateDetailSerializer(candidate)
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新候选人基本信息"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = CandidateUpdateSerializer(
            instance, data=request.data, partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CandidateDetailSerializer(instance).data)

    # ----------------------------------------------------------
    # 状态机转换
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, id=None):
        """候选人状态机转换"""
        candidate = self.get_object()
        serializer = CandidateStateTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        action_name = data['action']

        try:
            with transaction.atomic():
                if action_name == 'enter_process':
                    candidate = CandidateService.enter_process(
                        candidate, actor=request.user,
                        application_id=data.get('extra', {}).get('application_id'),
                    )
                elif action_name == 'send_offer':
                    candidate = CandidateService.send_offer(
                        candidate, offer_id=data.get('offer_id', ''),
                        actor=request.user,
                    )
                elif action_name == 'mark_onboarded':
                    candidate = CandidateService.mark_onboarded(
                        candidate, actor=request.user,
                        onboarding_id=data.get('onboarding_id'),
                    )
                elif action_name == 'withdraw':
                    candidate = CandidateService.withdraw(
                        candidate, reason=data.get('reason', ''),
                        actor=request.user,
                    )
                elif action_name == 'move_to_talent_pool':
                    from apps.talent_pool.services import move_candidate_to_pool
                    candidate = CandidateService.move_to_talent_pool(
                        candidate,
                        entry_source=data.get('entry_source', 'MANUAL'),
                        reason=data.get('reason', ''),
                        actor=request.user,
                    )
                    # 同步人才库记录
                    try:
                        move_candidate_to_pool(
                            candidate_id=candidate.id,
                            entry_source=data.get('entry_source', 'MANUAL'),
                            entry_reason=data.get('reason', ''),
                            actor=request.user,
                        )
                    except Exception as e:
                        logger.warning('Talent pool sync failed: %s', e)
                elif action_name == 'mark_process_failed':
                    candidate = CandidateService.mark_process_failed(
                        candidate, reason=data.get('reason', ''),
                        actor=request.user,
                    )
                elif action_name == 'pause_process':
                    candidate = CandidateService.pause_process(
                        candidate, reason=data.get('reason', ''),
                        actor=request.user,
                    )
                elif action_name == 'resume_process':
                    candidate = CandidateService.resume_process(
                        candidate, actor=request.user,
                    )
                else:
                    return Response(
                        {'error': f'Unknown action: {action_name}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except StateTransitionError as e:
            return Response(
                {'error': str(e), 'code': 'STATE_TRANSITION_ERROR'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(CandidateDetailSerializer(candidate).data)

    # ----------------------------------------------------------
    # 操作历史
    # ----------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='histories')
    def histories(self, request, id=None):
        """候选人操作历史"""
        candidate = self.get_object()
        histories = candidate.histories.filter(deleted_at__isnull=True)
        # 分页
        page = self.paginate_queryset(histories)
        if page is not None:
            serializer = CandidateHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = CandidateHistorySerializer(histories, many=True)
        return Response(serializer.data)

    # ----------------------------------------------------------
    # 申请列表
    # ----------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='applications')
    def applications(self, request, id=None):
        """候选人的所有申请"""
        candidate = self.get_object()
        apps = candidate.applications.filter(deleted_at__isnull=True).order_by('-created_at')
        from apps.application.serializers import ApplicationListSerializer
        page = self.paginate_queryset(apps)
        if page is not None:
            serializer = ApplicationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ApplicationListSerializer(apps, many=True)
        return Response(serializer.data)

    # ----------------------------------------------------------
    # 软拒统计
    # ----------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='soft-reject-stats')
    def soft_reject_stats(self, request, id=None):
        """候选人软拒统计"""
        candidate = self.get_object()
        from apps.application.services.soft_reject import SoftRejectService
        return Response(SoftRejectService.get_soft_reject_stats(candidate.id))

    @action(detail=True, methods=['get'], url_path='soft-reject-list')
    def soft_reject_list(self, request, id=None):
        """候选人软拒明细（按职位）"""
        candidate = self.get_object()
        position_id = request.query_params.get('position_id')
        if not position_id:
            return Response(
                {'error': 'position_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.application.services.soft_reject import SoftRejectService
        return Response(SoftRejectService.get_position_soft_reject_list(
            candidate.id, position_id,
        ))

    # ----------------------------------------------------------
    # 黑名单
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='blacklist')
    def blacklist(self, request, id=None):
        """加入黑名单"""
        candidate = self.get_object()
        reason = request.data.get('reason', '')
        candidate.is_blacklisted = True
        candidate.blacklist_reason = reason
        candidate.save()
        from .models import CandidateHistory
        CandidateHistory.objects.create(
            candidate=candidate,
            action='BLACKLISTED',
            detail={'reason': reason},
            operator=request.user,
        )
        return Response(CandidateDetailSerializer(candidate).data)

    @action(detail=True, methods=['post'], url_path='unblacklist')
    def unblacklist(self, request, id=None):
        """移出黑名单"""
        candidate = self.get_object()
        candidate.is_blacklisted = False
        candidate.blacklist_reason = ''
        candidate.save()
        from .models import CandidateHistory
        CandidateHistory.objects.create(
            candidate=candidate,
            action='UNBLACKLISTED',
            detail={},
            operator=request.user,
        )
        return Response(CandidateDetailSerializer(candidate).data)

    # ----------------------------------------------------------
    # 合并
    # ----------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='merge')
    def merge(self, request):
        """合并重复候选人"""
        serializer = CandidateMergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = CandidateService.merge_candidates(
            primary_id=serializer.validated_data['primary_id'],
            duplicate_ids=serializer.validated_data['duplicate_ids'],
            actor=request.user,
        )
        return Response({
            'primary_id': result.primary.id,
            'merged_from': [d.id for d in result.duplicates],
            'merged_fields': result.merged_fields,
        })

    # ----------------------------------------------------------
    # 批量导入
    # ----------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='import')
    def import_candidates(self, request):
        """批量导入候选人"""
        serializer = CandidateImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = []
        for item in serializer.validated_data['candidates']:
            try:
                data = item.to_data()
                c = CandidateService.create_candidate(data, actor=request.user)
                results.append({'success': True, 'id': c.id, 'name': c.name})
            except Exception as e:
                results.append({'success': False, 'error': str(e), 'data': item.validated_data})
        return Response({'results': results, 'total': len(results)})

    # ----------------------------------------------------------
    # 摩卡同步
    # ----------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='moka-sync')
    def moka_sync(self, request):
        """摩卡同步候选人"""
        serializer = CandidateMokaSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidate = CandidateService.sync_from_moka(
            moka_data=serializer.validated_data['moka_data'],
            actor=request.user,
        )
        return Response(CandidateDetailSerializer(candidate).data)

    # ----------------------------------------------------------
    # 高级搜索
    # ----------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='search')
    def search(self, request):
        """高级搜索"""
        from datetime import datetime
        data = request.data
        keyword = data.get('keyword')
        state = data.get('state')
        source_channel_id = data.get('source_channel_id')
        referrer_id = data.get('referrer_id')
        tag = data.get('tag')
        created_from = data.get('created_from')
        created_to = data.get('created_to')
        if created_from:
            created_from = datetime.fromisoformat(created_from.replace('Z', '+00:00'))
        if created_to:
            created_to = datetime.fromisoformat(created_to.replace('Z', '+00:00'))
        limit = int(data.get('limit', 50))
        offset = int(data.get('offset', 0))
        results = CandidateService.search_candidates(
            keyword=keyword, state=state,
            source_channel_id=source_channel_id, referrer_id=referrer_id,
            tag=tag, created_from=created_from, created_to=created_to,
            limit=limit, offset=offset,
        )
        return Response({
            'count': len(results),
            'results': CandidateListSerializer(results, many=True).data,
        })


class CandidateTagViewSet(viewsets.ModelViewSet):
    """候选人标签字典"""
    queryset = CandidateTag.objects.all()
    serializer_class = CandidateTagSerializer
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
