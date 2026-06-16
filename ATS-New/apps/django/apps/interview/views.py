"""Interview Views (DRF) - PRD v4 §14.5"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsHROrAbove

from .models import Interview, InterviewEvaluation
from .serializers import (
    InterviewCreateSerializer,
    InterviewDetailSerializer,
    InterviewEvaluationSerializer,
    InterviewListSerializer,
)


class InterviewViewSet(AuditMixin, viewsets.ModelViewSet):
    """面试 ViewSet"""
    queryset = Interview.objects.all()
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['application', 'status', 'format', 'round_number']
    search_fields = ['code', 'application__code']
    ordering_fields = ['scheduled_at', 'created_at']
    ordering = ['scheduled_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return InterviewListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return InterviewCreateSerializer
        return InterviewDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        return qs.prefetch_related('interviewers')

    def perform_destroy(self, instance):
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])


class InterviewEvaluationViewSet(AuditMixin, viewsets.ModelViewSet):
    """面试评价 ViewSet"""
    queryset = InterviewEvaluation.objects.all()
    serializer_class = InterviewEvaluationSerializer
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['interview', 'interviewer', 'recommendation']
    ordering_fields = ['submitted_at']
    ordering = ['-submitted_at']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        return qs.select_related('interview', 'interviewer')
