"""Referral Views (DRF) - PRD v4 §6.4"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination

from .models import Referral
from .serializers import (
    ReferralCreateSerializer,
    ReferralDetailSerializer,
    ReferralListSerializer,
)


class ReferralViewSet(AuditMixin, viewsets.ModelViewSet):
    """内推记录 ViewSet"""
    queryset = Referral.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['referrer', 'referral_type', 'status', 'detected_type']
    search_fields = ['candidate__name', 'position__title']
    ordering_fields = ['created_at', 'bonus_paid_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ReferralListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return ReferralCreateSerializer
        return ReferralDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        return qs.select_related('referrer', 'candidate', 'position')

    def perform_destroy(self, instance):
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    @action(detail=False, methods=['get'], url_path='my-referrals')
    def my_referrals(self, request):
        """我的推荐"""
        qs = self.get_queryset().filter(referrer=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ReferralListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReferralListSerializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=True, methods=['post'], url_path='detect-type')
    def detect_type(self, request, pk=None):
        """自动检测 N+1/N+2 类型"""
        instance = self.get_object()
        # 简化的检测逻辑：基于 referrer 与 candidate 部门关系
        from apps.core.models import User
        try:
            referrer_dept = instance.referrer.department
            candidate_dept = instance.candidate.latest_application_position.position.department if hasattr(instance.candidate, 'latest_application_position') else None
            if referrer_dept and candidate_dept and referrer_dept.id == candidate_dept.id:
                detected = 'N+1'
            elif referrer_dept and candidate_dept and referrer_dept.parent_id == candidate_dept.id:
                detected = 'N+2'
            else:
                detected = instance.referral_type
        except Exception:
            detected = instance.referral_type
        instance.detected_type = detected
        instance.save(update_fields=['detected_type', 'updated_at'])
        out = ReferralDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})
