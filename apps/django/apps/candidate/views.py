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

logger = logging.getLogger(__name__)

import logging

from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.common.exceptions import StateTransitionError
from apps.common.mixins import SoftDeleteViewSetMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.common.views import EnvelopeReadOnlyMixin
from apps.core.permissions import IsHROrAbove
from apps.core.permissions_v2 import V2Permission, ScopeQuerysetMixin
from apps.core.scope_resolver import scope_filter_q

from .models import (
    Candidate,
    CandidateTag,
    CandidateFieldValue,
    CandidateScreening,
    CandidatePositionRecommendation,
)
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


class CandidateViewSet(EnvelopeReadOnlyMixin, ScopeQuerysetMixin, SoftDeleteViewSetMixin, viewsets.ModelViewSet):
    """候选人 ViewSet — 增加部门 scope 过滤防 IDOR"""
    queryset = Candidate.objects.filter(deleted_at__isnull=True).select_related(
        'source_channel', 'referrer',
    )
    permission_classes = [V2Permission]
    permission_required = 'recruit:candidate:list'
    pagination_class = StandardResultsSetPagination
    lookup_field = 'id'
    # Candidate 模型无 department 字段; 用 referrer (推荐人) 间接 scope: HR 看本部门推荐人.
    # 普通 HRBP+ 仍按 created_by 兜底.
    scope_field = 'referrer__department'
    scope_creator_field = 'created_by'

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
        # 2026-09-25: 候选人 ID 白名单（逗号分隔）—— 供指标库「按规则筛选」结果集回传。
        # 规则含派生指标（需计算，无法 SQL 化），故由 metrics 侧先算得 passedIds，
        # 再由本参数收敛结果集，保证分页与总数正确。
        ids = self.request.query_params.get('ids')
        if ids:
            id_list = [i.strip() for i in ids.split(',') if i.strip()]
            if id_list:
                qs = qs.filter(id__in=id_list)
        # 黑名单
        blacklisted = self.request.query_params.get('blacklisted')
        if blacklisted is not None:
            qs = qs.filter(is_blacklisted=blacklisted.lower() == 'true')
        # IDOR: 按部门 scope + 创建人 二次过滤 (Fix 1)
        # Tier 3: scope_resolver 现为行级数据范围唯一真相源;
        # 直接由 resolve_scope 产出过滤 Q, 不再经 DataPermissionRule ROW 镜像.
        sq = scope_filter_q(
            self.request.user,
            app_code='recruit',
            scope_field=self.scope_field,
            creator_field=self.scope_creator_field,
            recruit_type=getattr(self.request, 'recruit_type', 'social'),
            entity='candidate',
        )
        qs = qs.filter(sq)
        return qs.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """创建候选人（含幂等查重）"""
        serializer = CandidateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.to_data()
        candidate = CandidateService.create_candidate(
            data, actor=request.user,
            recruit_type=getattr(self.request, 'recruit_type', 'social'),
        )
        out = CandidateDetailSerializer(
            candidate, context=self.get_serializer_context(),
        )
        return success_response(out.data, status_code=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新候选人基本信息"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = CandidateUpdateSerializer(
            instance, data=request.data, partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            CandidateDetailSerializer(instance, context=self.get_serializer_context()).data,
        )

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
        return Response(
            CandidateDetailSerializer(candidate, context=self.get_serializer_context()).data,
        )

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
        old_blacklisted = candidate.is_blacklisted
        candidate.is_blacklisted = True
        candidate.blacklist_reason = reason
        from .models import CandidateHistory
        # BUG-6: service 显式写 BLACKLIST_CHANGED + 设标志, signal 不会再补一条
        CandidateHistory.objects.create(
            candidate=candidate,
            action='BLACKLIST_CHANGED',
            detail={'from': old_blacklisted, 'to': True},
            created_by=request.user,
        )
        candidate._blacklist_change_recorded = True
        candidate.save()
        CandidateHistory.objects.create(
            candidate=candidate,
            action='BLACKLISTED',
            detail={'reason': reason},
            created_by=request.user,
        )
        return Response(
            CandidateDetailSerializer(candidate, context=self.get_serializer_context()).data,
        )

    @action(detail=True, methods=['post'], url_path='unblacklist')
    def unblacklist(self, request, id=None):
        """移出黑名单"""
        candidate = self.get_object()
        old_blacklisted = candidate.is_blacklisted
        candidate.is_blacklisted = False
        candidate.blacklist_reason = ''
        from .models import CandidateHistory
        # BUG-6: 同上, 显式写 BLACKLIST_CHANGED 并置标志
        CandidateHistory.objects.create(
            candidate=candidate,
            action='BLACKLIST_CHANGED',
            detail={'from': old_blacklisted, 'to': False},
            created_by=request.user,
        )
        candidate._blacklist_change_recorded = True
        candidate.save()
        CandidateHistory.objects.create(
            candidate=candidate,
            action='UNBLACKLISTED',
            detail={},
            created_by=request.user,
        )
        return Response(
            CandidateDetailSerializer(candidate, context=self.get_serializer_context()).data,
        )

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
        for idx, item in enumerate(serializer.validated_data['candidates']):
            try:
                data = item.to_data()
                c = CandidateService.create_candidate(data, actor=request.user)
                results.append({'success': True, 'id': c.id, 'name': c.name})
            except Exception as e:
                logger.warning('批量创建候选人单条失败 idx=%s err=%s', idx, e, exc_info=True)
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
        return Response(
            CandidateDetailSerializer(candidate, context=self.get_serializer_context()).data,
        )

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
            'results': CandidateListSerializer(
                results, many=True, context=self.get_serializer_context(),
            ).data,
        })

    # ----------------------------------------------------------
    # G44 状态详情 schema (FE 调 /candidates/status-details/schema 渲染 11 状态字段定义)
    # ----------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='status-details/schema')
    def status_details_schema(self, request):
        """返 11 个候选人状态对应的可编辑字段定义. 2026-07-01 stub."""
        schema = {
            'PENDING': [
                {'key': 'note', 'type': 'textarea', 'required': False, 'label': '备注'},
            ],
            'PASS': [
                {'key': 'feedback', 'type': 'textarea', 'required': True, 'label': '通过原因'},
            ],
            'FAIL': [
                {'key': 'reason', 'type': 'select', 'required': True, 'label': '失败原因',
                 'options': ['NOT_QUALIFIED', 'EXPERIENCE_INSUFFICIENT', 'SALARY_MISMATCH', 'OTHER']},
                {'key': 'detail', 'type': 'textarea', 'required': False, 'label': '详细说明'},
            ],
            'INVITED': [
                {'key': 'invitationId', 'type': 'text', 'required': True, 'label': '邀约 ID'},
            ],
            'INTERVIEWING': [
                {'key': 'interviewId', 'type': 'text', 'required': True, 'label': '面试 ID'},
            ],
            'OFFERED': [
                {'key': 'offerId', 'type': 'text', 'required': True, 'label': 'Offer ID'},
                {'key': 'salary', 'type': 'number', 'required': True, 'label': '薪资'},
            ],
            'ONBOARDED': [
                {'key': 'onboardDate', 'type': 'date', 'required': True, 'label': '入职日期'},
            ],
            'PROBATION_PASSED': [
                {'key': 'passDate', 'type': 'date', 'required': True, 'label': '通过日期'},
            ],
            'REJECTED': [
                {'key': 'reason', 'type': 'select', 'required': True, 'label': '拒绝原因',
                 'options': ['NOT_QUALIFIED', 'POSITION_FILLED', 'CANDIDATE_WITHDREW', 'OTHER']},
            ],
            'ARCHIVED': [
                {'key': 'archiveReason', 'type': 'textarea', 'required': True, 'label': '归档原因'},
            ],
            'BLACKLISTED': [
                {'key': 'reason', 'type': 'textarea', 'required': True, 'label': '拉黑原因'},
            ],
        }
        return Response({'success': True, 'data': schema})

    @action(detail=True, methods=['put', 'patch'], url_path='status-details')
    def status_details(self, request, id=None):
        """更新候选人状态详情字段. 2026-07-01 stub: 不实际存, 只返成功."""
        instance = self.get_object()
        return Response({
            'success': True,
            'data': {
                'id': str(instance.id),
                'status': instance.candidate_status,
                'details': request.data,
            }
        })


class CandidateTagViewSet(viewsets.ModelViewSet):
    """候选人标签字典"""
    queryset = CandidateTag.objects.all()
    serializer_class = CandidateTagSerializer
    permission_classes = [IsHROrAbove]
    pagination_class = StandardResultsSetPagination


class CandidateResumeFieldsView(APIView):
    """候选人扩展字段值 (简历) 读写端点

    GET  /api/v1/candidates/<pk>/resume-fields/  -> { success, data: {fieldKey: value} }
    PUT  /api/v1/candidates/<pk>/resume-fields/  body { values: {fieldKey: value} } -> upsert 每个 field_key
    用于「候选人详情 - 编辑简历」: 标准简历配置中无 Candidate 模型列的扩展字段值存取。
    """
    permission_classes = [IsAuthenticated]

    def _check_candidate(self, pk):
        # 候选人不存在时返回 404 (避免 FK 约束校验失败导致 500)
        if not Candidate.objects.filter(id=pk).exists():
            return Response(
                {'success': False, 'message': '候选人不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return None

    def get(self, request, pk=None):
        err = self._check_candidate(pk)
        if err is not None:
            return err
        values = CandidateFieldValue.objects.filter(candidate_id=pk)
        data = {v.field_key: v.value for v in values}
        return Response({'success': True, 'data': data})

    def put(self, request, pk=None):
        err = self._check_candidate(pk)
        if err is not None:
            return err
        payload = request.data or {}
        incoming = payload.get('values')
        if not isinstance(incoming, dict):
            return Response(
                {'success': False, 'message': 'values 必须为对象 {fieldKey: value}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        saved = {}
        for fk, val in incoming.items():
            if not fk:
                continue
            obj, _ = CandidateFieldValue.objects.update_or_create(
                candidate_id=pk, field_key=fk, defaults={'value': val},
            )
            saved[fk] = obj.value
        return Response({'success': True, 'data': saved})


# ============================================================
# G9 PRD: 候选人维度批量操作真实后端
# 替代 apps/referral/urls_stubs.py 中 candidate_batch_* 的 501 stub。
# 响应壳与 process 维度 batch 端点一致: {success, data:{results:[...]}}
# 注意: drf-camel-case 会把请求体转 snake_case, 故读 candidate_ids/position_id/recruiter_id;
#       响应经 CamelCaseJSONRenderer 转回 camelCase (candidateId/recommendationId/...)。
# ============================================================
def _current_recruit_type(request):
    """双系统硬分区: 取请求上的 recruit_type (RecruitTypeMiddleware 注入), 无则 None。"""
    return getattr(request, 'recruit_type', None)


class CandidateBatchRecommendView(APIView):
    """批量推荐候选人到职位 → 写入 CandidatePositionRecommendation。

    POST /api/v1/candidates/batch/recommend/
    body: {candidateIds: string[], positionId: string, comment?: string}
    """
    permission_classes = [IsHROrAbove]

    def post(self, request):
        candidate_ids = request.data.get('candidate_ids', [])
        position_id = request.data.get('position_id')
        comment = request.data.get('comment', '')
        if not candidate_ids:
            raise ValidationError('candidate_ids 不能为空')
        if not position_id:
            raise ValidationError('position_id 不能为空')

        from apps.position.models import Position
        try:
            position = Position.objects.get(pk=position_id)
        except Position.DoesNotExist:
            return Response(
                {'success': False, 'message': 'POSITION_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND,
            )

        results = []
        for cid in candidate_ids:
            try:
                cand = Candidate.objects.get(pk=cid)
                rec = CandidatePositionRecommendation.objects.create(
                    candidate=cand,
                    position=position,
                    reason=comment,
                    recommender=request.user,
                    recruit_type=cand.recruit_type,
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
        return Response({'success': True, 'data': {'results': results}})


class CandidateBatchArchiveView(APIView):
    """批量归档候选人 → 置 is_archived=True (软标志, 可逆)。

    POST /api/v1/candidates/batch/archive/
    body: {candidateIds: string[], reason?: string}
    """
    permission_classes = [IsHROrAbove]

    def post(self, request):
        candidate_ids = request.data.get('candidate_ids', [])
        if not candidate_ids:
            raise ValidationError('candidate_ids 不能为空')

        qs = Candidate.objects.filter(id__in=candidate_ids)
        rt = _current_recruit_type(request)
        if rt:
            qs = qs.filter(recruit_type=rt)
        updated = qs.update(is_archived=True, archived_at=timezone.now())
        results = [{'candidate_id': cid, 'success': True} for cid in candidate_ids]
        return Response({'success': True, 'data': {'results': results, 'updated': updated}})


class CandidateBatchAssignView(APIView):
    """批量分配招聘官 → 置 Candidate.recruiter。

    POST /api/v1/candidates/batch/assign/
    body: {candidateIds: string[], recruiterId: string}
    """
    permission_classes = [IsHROrAbove]

    def post(self, request):
        candidate_ids = request.data.get('candidate_ids', [])
        recruiter_id = request.data.get('recruiter_id')
        if not candidate_ids:
            raise ValidationError('candidate_ids 不能为空')
        if not recruiter_id:
            raise ValidationError('recruiter_id 不能为空')

        User = get_user_model()
        try:
            recruiter = User.objects.get(pk=recruiter_id)
        except User.DoesNotExist:
            return Response(
                {'success': False, 'message': 'RECRUITER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = Candidate.objects.filter(id__in=candidate_ids)
        rt = _current_recruit_type(request)
        if rt:
            qs = qs.filter(recruit_type=rt)
        updated = qs.update(recruiter=recruiter)
        results = [{'candidate_id': cid, 'success': True} for cid in candidate_ids]
        return Response({'success': True, 'data': {'results': results, 'updated': updated}})


class CandidateBatchScreenView(APIView):
    """批量初筛候选人 → 写入 CandidateScreening (候选人维度)。

    POST /api/v1/candidates/batch/screen/
    body: {candidateIds: string[], result: 'PASS'|'FAIL'|'KEEP', comment?: string}
    """
    permission_classes = [IsHROrAbove]

    def post(self, request):
        candidate_ids = request.data.get('candidate_ids', [])
        result = request.data.get('result')
        comment = request.data.get('comment', '')
        if not candidate_ids:
            raise ValidationError('candidate_ids 不能为空')
        if result not in ('PASS', 'FAIL', 'KEEP'):
            raise ValidationError("result 必须是 'PASS' / 'FAIL' / 'KEEP'")

        results = []
        for cid in candidate_ids:
            try:
                cand = Candidate.objects.get(pk=cid)
                rec = CandidateScreening.objects.create(
                    candidate=cand,
                    result=result,
                    comment=comment,
                    screener=request.user,
                    recruit_type=cand.recruit_type,
                )
                results.append({
                    'candidate_id': cid,
                    'success': True,
                    'screening_id': rec.id,
                    'result': result,
                })
            except Candidate.DoesNotExist:
                results.append({
                    'candidate_id': cid,
                    'success': False,
                    'screening_id': None,
                    'error': 'CANDIDATE_NOT_FOUND',
                })
        return Response({'success': True, 'data': {'results': results}})


class CandidateBatchExportView(APIView):
    """批量导出候选人 → CSV (utf-8-sig, Excel 兼容) blob。

    POST /api/v1/candidates/batch/export/
    body: {candidateIds?: string[], filter?: {state?, keyword?}}
    """
    permission_classes = [IsHROrAbove]

    def post(self, request):
        from django.db.models import Q
        import csv
        import io

        candidate_ids = request.data.get('candidate_ids') or []
        filter_ = request.data.get('filter') or {}

        qs = Candidate.objects.all()
        rt = _current_recruit_type(request)
        if rt:
            qs = qs.filter(recruit_type=rt)
        if candidate_ids:
            qs = qs.filter(id__in=candidate_ids)
        elif filter_:
            if filter_.get('state'):
                qs = qs.filter(current_state=filter_['state'])
            kw = filter_.get('keyword')
            if kw:
                qs = qs.filter(Q(name__icontains=kw) | Q(phone__icontains=kw))
        qs = qs.select_related('recruiter')[:2000]

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            '姓名', '手机号', '邮箱', '性别', '最高学历', '当前公司', '当前职位',
            '期望薪资', '当前城市', '招聘类型', '状态', '是否归档', '招聘官', '创建时间',
        ])
        for c in qs:
            writer.writerow([
                c.name, c.phone, c.email or '', c.gender or '',
                c.highest_education or '', c.current_company or '', c.current_position or '',
                c.expected_salary if c.expected_salary is not None else '',
                c.current_city or '', c.recruit_type,
                c.current_state, '是' if c.is_archived else '否',
                c.recruiter.real_name if c.recruiter else '',
                c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else '',
            ])
        content = buf.getvalue().encode('utf-8-sig')
        resp = HttpResponse(content, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="candidates_export.csv"'
        return resp
