"""Talent Pool Views (DRF) - PRD v4 §14.7"""
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination

from .models import TalentPoolEntry, TalentPoolTag
from .serializers import (
    TalentPoolEntryCreateSerializer,
    TalentPoolEntryDetailSerializer,
    TalentPoolEntryListSerializer,
    TalentPoolTagSerializer,
)


class TalentPoolEntryViewSet(AuditMixin, viewsets.ModelViewSet):
    """人才库条目 ViewSet"""
    queryset = TalentPoolEntry.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['source', 'is_active', 'candidate']
    search_fields = ['candidate__name', 'source_detail']
    ordering_fields = ['created_at', 'last_activated_at', 'activated_count']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return TalentPoolEntryListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return TalentPoolEntryCreateSerializer
        return TalentPoolEntryDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        return qs.select_related('candidate', 'last_position', 'last_stage')

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """激活人才库候选人"""
        instance = self.get_object()
        instance.activated_count = (instance.activated_count or 0) + 1
        instance.last_activated_at = timezone.now()
        instance.is_active = True
        instance.save()
        out = TalentPoolEntryDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """停用"""
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        out = TalentPoolEntryDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})


class TalentPoolTagViewSet(AuditMixin, viewsets.ModelViewSet):
    """人才库标签 ViewSet"""
    queryset = TalentPoolTag.objects.all()
    serializer_class = TalentPoolTagSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['category', 'name']
