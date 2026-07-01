"""mou views - 2026-07-01 stub (G36 待补真业务)"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from .models import MouAgreement, MouContainer, MutualExclusionGroup, AutomationRule
from .serializers import (
    MouAgreementSerializer, MouContainerSerializer,
    MutualExclusionGroupSerializer, AutomationRuleSerializer,
)


class MouAgreementViewSet(viewsets.ModelViewSet):
    """MOU 协议 CRUD"""
    queryset = MouAgreement.objects.all().order_by('-created_at')
    serializer_class = MouAgreementSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs


class MouContainerViewSet(viewsets.ModelViewSet):
    """MOU 容器 (配额) CRUD"""
    queryset = MouContainer.objects.all().order_by('mou__code', 'code')
    serializer_class = MouContainerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination


class MutualExclusionGroupViewSet(viewsets.ModelViewSet):
    """互斥组 CRUD"""
    queryset = MutualExclusionGroup.objects.all().order_by('-created_at')
    serializer_class = MutualExclusionGroupSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination


class AutomationRuleViewSet(viewsets.ModelViewSet):
    """自动化规则 CRUD"""
    queryset = AutomationRule.objects.all().order_by('-created_at')
    serializer_class = AutomationRuleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
