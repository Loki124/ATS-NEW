"""mou views - 2026-07-01 stub (G36 待补真业务)"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import MOUVIEWSetPermission  # noqa: F401
from .models import MouAgreement, MouContainer, MutualExclusionGroup, AutomationRule
from .serializers import (
    MouAgreementSerializer, MouContainerSerializer,
    MutualExclusionGroupSerializer, AutomationRuleSerializer,
)


def _wrap_envelope(serializer):
    """包 {success: true, data: <serializer_data>} 信封, 与 list 端点一致.
    前端 MouManagement.vue:1076 检查 data.success — 没包就误判失败.
    """
    return Response({'success': True, 'data': serializer.data})


class MouAgreementViewSet(viewsets.ModelViewSet):
    """MOU 协议 CRUD - 仅 HRBP+ (Fix 1)"""
    queryset = MouAgreement.objects.all().order_by('-created_at')
    serializer_class = MouAgreementSerializer
    permission_classes = [MOUVIEWSetPermission]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return _wrap_envelope(serializer)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return _wrap_envelope(serializer)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class MouContainerViewSet(viewsets.ModelViewSet):
    """MOU 容器 (配额) CRUD - 仅 HRBP+ (Fix 1)"""
    queryset = MouContainer.objects.all().order_by('mou__code', 'code')
    serializer_class = MouContainerSerializer
    permission_classes = [MOUVIEWSetPermission]
    pagination_class = StandardResultsSetPagination

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return _wrap_envelope(serializer)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return _wrap_envelope(serializer)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class MutualExclusionGroupViewSet(viewsets.ModelViewSet):
    """互斥组 CRUD - 仅 HRBP+ (Fix 1)"""
    queryset = MutualExclusionGroup.objects.all().order_by('-created_at')
    serializer_class = MutualExclusionGroupSerializer
    permission_classes = [MOUVIEWSetPermission]
    pagination_class = StandardResultsSetPagination

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return _wrap_envelope(serializer)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return _wrap_envelope(serializer)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class AutomationRuleViewSet(viewsets.ModelViewSet):
    """自动化规则 CRUD - 仅 HRBP+ (Fix 1)"""
    queryset = AutomationRule.objects.all().order_by('-created_at')
    serializer_class = AutomationRuleSerializer
    permission_classes = [MOUVIEWSetPermission]
    pagination_class = StandardResultsSetPagination

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return _wrap_envelope(serializer)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return _wrap_envelope(serializer)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
