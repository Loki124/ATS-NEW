"""Interview Views (DRF) - PRD v4 §14.5

T30.175 (V2 cutover follow-up): user.user_roles.filter(role__code=...) 替换为
apps.core.role_v2_query.user_has_any_role (直接走 UserRoleV2).
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.views import EnvelopeWriteMixin
from apps.core.permissions import IsHROrAbove
from apps.core.permissions_v2 import V2Permission, ScopeQuerysetMixin
from apps.core.role_v2_query import user_has_any_role, is_super_admin

from .models import Interview, InterviewEvaluation
from .serializers import (
    InterviewCreateSerializer,
    InterviewDetailSerializer,
    InterviewEvaluationSerializer,
    InterviewListSerializer,
)


class InterviewViewSet(EnvelopeWriteMixin, ScopeQuerysetMixin, AuditMixin, viewsets.ModelViewSet):
    """面试 ViewSet - 按 application.position.department scope 过滤"""
    queryset = Interview.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:interview:list'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['application', 'status', 'format', 'round_number']
    search_fields = ['code', 'application__code']
    ordering_fields = ['scheduled_at', 'created_at']
    ordering = ['scheduled_at']
    scope_field = 'application__position__department'
    scope_creator_field = 'created_by'

    def get_serializer_class(self):
        if self.action == 'list':
            return InterviewListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return InterviewCreateSerializer
        return InterviewDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        qs = self.scope_queryset(qs)
        return qs.prefetch_related('interviewers')

    def perform_destroy(self, instance):
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])


class InterviewEvaluationViewSet(EnvelopeWriteMixin, AuditMixin, viewsets.ModelViewSet):
    """面试评价 ViewSet"""
    queryset = InterviewEvaluation.objects.all()
    serializer_class = InterviewEvaluationSerializer
    permission_classes = [IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['interview', 'interviewer', 'recommendation']
    ordering_fields = ['submitted_at']
    ordering = ['-submitted_at']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        # 评价默认走 interviewer 字段 scope
        qs = qs.filter(
            interviewer=self.request.user
        ) if not (is_super_admin(self.request.user) or user_has_any_role(
            self.request.user, ['SUPER_ADMIN', 'HRBP']
        )) else qs
        return qs.select_related('interview', 'interviewer')

    def perform_create(self, serializer):
        instance = serializer.save()
        self._maybe_notify_bg_suggestion(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._maybe_notify_bg_suggestion(instance)

    @staticmethod
    def _maybe_notify_bg_suggestion(instance):
        """背调建议非空时，best-effort 向招聘专家发送高优先级提醒。"""
        suggestion = (getattr(instance, 'bg_suggestion', '') or '').strip()
        if not suggestion:
            return
        try:
            from .services import notify_recruiters_bg_suggestion
            interview = getattr(instance, 'interview', None)
            application = getattr(interview, 'application', None)
            candidate = getattr(application, 'candidate', None)
            candidate_id = candidate.id if candidate else ''
            candidate_name = getattr(candidate, 'name', '') or ''
            interviewer_name = getattr(instance.interviewer, 'username', '') or ''
            notify_recruiters_bg_suggestion(
                candidate_id, candidate_name, interviewer_name, suggestion,
            )
        except (OperationalError, ValueError, TypeError, AttributeError) as e:
            # 通知为 best-effort：不阻断评价落库主流程（编程错误仍抛出以便排查）。
            logger = __import__('logging').getLogger(__name__)
            logger.warning('背调建议通知触发失败 evaluation=%s err=%s', getattr(instance, 'id', ''), e)
