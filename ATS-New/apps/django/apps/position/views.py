"""Position Views (DRF) - PRD v4 §14.2"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import ValidationError
from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsHROrAbove

from .models import Position
from .serializers import (
    PositionCreateSerializer,
    PositionDetailSerializer,
    PositionListSerializer,
    PositionTransitionSerializer,
)


class PositionViewSet(AuditMixin, viewsets.ModelViewSet):
    """职位 ViewSet - 含状态机流转"""
    queryset = Position.objects.all()
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['state', 'department', 'hiring_manager', 'owner', 'level', 'process']
    search_fields = ['code', 'title', 'description']
    ordering_fields = ['code', 'created_at', 'published_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PositionListSerializer
        if self.action == 'retrieve':
            return PositionDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return PositionCreateSerializer
        if self.action == 'transition':
            return PositionTransitionSerializer
        return PositionDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        return qs.select_related('department', 'hiring_manager', 'owner', 'process')

    def perform_destroy(self, instance):
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        """状态机流转：submit_publish/publish/start_recruiting/pause/resume/close"""
        instance = self.get_object()
        serializer = PositionTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']
        method = getattr(instance, action_name, None)
        if not method:
            raise ValidationError(f'不支持的操作：{action_name}')
        method()
        instance.save()
        out = PositionDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})

    @action(detail=False, methods=['get'], url_path='open')
    def open_positions(self, request):
        """开放中的职位列表"""
        qs = self.get_queryset().filter(state='RECRUITING')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = PositionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PositionListSerializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})
