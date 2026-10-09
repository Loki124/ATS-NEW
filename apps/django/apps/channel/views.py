
"""Channel Views (DRF) - PRD v4 §14.5"""
from django_filters.rest_framework import DjangoFilterBackend

from apps.common.pagination import StandardResultsSetPagination
from apps.common.viewsets import EnvelopeAuditModelViewSet
from apps.core.permissions import IsHROrAbove
from apps.core.permissions_v2 import V2Permission

from .models import Channel, ChannelCost
from .serializers import ChannelCostSerializer, ChannelSerializer


class ChannelViewSet(EnvelopeAuditModelViewSet):
    """招聘渠道 ViewSet"""
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:channel:list'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at', 'total_cost']
    ordering = ['name']


class ChannelCostViewSet(EnvelopeAuditModelViewSet):
    """渠道成本 ViewSet"""
    queryset = ChannelCost.objects.all()
    serializer_class = ChannelCostSerializer
    permission_classes = [IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['channel', 'cost_type']
    ordering_fields = ['incurred_at', 'amount']
    ordering = ['-incurred_at']
