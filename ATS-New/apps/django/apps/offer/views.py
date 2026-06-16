"""Offer Views (DRF) - PRD v4 §14.5"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import ValidationError
from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsHROrAbove

from .models import Offer
from .serializers import (
    OfferCreateSerializer,
    OfferDetailSerializer,
    OfferListSerializer,
    OfferTransitionSerializer,
)


class OfferViewSet(AuditMixin, viewsets.ModelViewSet):
    """Offer ViewSet - 含 8 个状态流转"""
    queryset = Offer.objects.all()
    permission_classes = [IsAuthenticated, IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['state', 'candidate', 'position', 'level']
    search_fields = ['code', 'candidate__name', 'position__title']
    ordering_fields = ['created_at', 'sent_at', 'responded_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return OfferListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return OfferCreateSerializer
        if self.action == 'transition':
            return OfferTransitionSerializer
        return OfferDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        return qs.select_related('candidate', 'position', 'application')

    def perform_destroy(self, instance):
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        instance = self.get_object()
        serializer = OfferTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']
        kwargs = {}
        if action_name == 'candidate_reject':
            kwargs['reason'] = serializer.validated_data.get('reason', '')
        method = getattr(instance, action_name, None)
        if not method:
            raise ValidationError(f'不支持的操作：{action_name}')
        method(**kwargs)
        instance.save()
        out = OfferDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})
