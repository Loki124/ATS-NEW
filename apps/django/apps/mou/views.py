
"""mou views - MOU 协议 / 容器 / 互斥组 / 自动化规则 CRUD.

信封化: 经 EnvelopeWriteMixin 统一 create/update/retrieve 为
{success, data, message, code}; list 由 StandardResultsSetPagination 信封.
scopes 动作 (apps/mou/urls.py 的 MouAgreementViewSetWithScopes) 自带 {success,data}
半信封, 含 success:False 失败分支, 按协调式信封 SOP 不迁移.
"""

from apps.common.pagination import StandardResultsSetPagination
from apps.common.viewsets import EnvelopeModelViewSet
from apps.core.permissions import MOUVIEWSetPermission  # noqa: F401

from .models import MouAgreement, MouContainer, MouRule, MutualExclusionGroup
from .serializers import (
    MouAgreementSerializer,
    MouContainerSerializer,
    MouRuleSerializer,
    MutualExclusionGroupSerializer,
)


class MouAgreementViewSet(EnvelopeModelViewSet):
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


class MouContainerViewSet(EnvelopeModelViewSet):
    """MOU 容器 (配额) CRUD - 仅 HRBP+ (Fix 1)"""
    queryset = MouContainer.objects.all().order_by('mou__code', 'code')
    serializer_class = MouContainerSerializer
    permission_classes = [MOUVIEWSetPermission]
    pagination_class = StandardResultsSetPagination


class MutualExclusionGroupViewSet(EnvelopeModelViewSet):
    """互斥组 CRUD - 仅 HRBP+ (Fix 1)"""
    queryset = MutualExclusionGroup.objects.all().order_by('-created_at')
    serializer_class = MutualExclusionGroupSerializer
    permission_classes = [MOUVIEWSetPermission]
    pagination_class = StandardResultsSetPagination


class MouRuleViewSet(EnvelopeModelViewSet):
    """自动化规则 CRUD - 仅 HRBP+ (Fix 1)"""
    queryset = MouRule.objects.all().order_by('-created_at')
    serializer_class = MouRuleSerializer
    permission_classes = [MOUVIEWSetPermission]
    pagination_class = StandardResultsSetPagination
