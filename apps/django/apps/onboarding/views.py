"""Onboarding Views (DRF) - PRD v4 §6.7"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.exceptions import ValidationError
from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.views import EnvelopeWriteMixin
from apps.core.permissions_v2 import ScopeQuerysetMixin, V2Permission

from .models import Onboarding
from .serializers import (
    OnboardingCreateSerializer,
    OnboardingDetailSerializer,
    OnboardingListSerializer,
    OnboardingTransitionSerializer,
)


class OnboardingViewSet(EnvelopeWriteMixin, ScopeQuerysetMixin, AuditMixin, viewsets.ModelViewSet):
    """入职流程 ViewSet - 按职位部门 scope 过滤 (Fix 1)"""
    queryset = Onboarding.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:onboarding:list'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['state', 'candidate', 'position']
    ordering_fields = ['start_date', 'created_at']
    ordering = ['-created_at']
    scope_field = 'position__department'
    scope_creator_field = 'created_by'

    def get_serializer_class(self):
        if self.action == 'list':
            return OnboardingListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return OnboardingCreateSerializer
        if self.action == 'transition':
            return OnboardingTransitionSerializer
        return OnboardingDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        qs = qs.select_related('candidate', 'position', 'offer')
        qs = self.scope_queryset(qs)
        return qs

    def perform_destroy(self, instance):
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        instance = self.get_object()
        serializer = OnboardingTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']
        kwargs = {}
        if action_name == 'delay':
            new_date = serializer.validated_data.get('new_date')
            if not new_date:
                raise ValidationError('delay 操作必须提供 new_date')
            kwargs['new_date'] = new_date
        if action_name == 'regularize':
            kwargs['result'] = serializer.validated_data.get('result', 'PASS')
        method = getattr(instance, action_name, None)
        if not method:
            raise ValidationError(f'不支持的操作：{action_name}')
        method(**kwargs)
        instance.save()
        out = OnboardingDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})
