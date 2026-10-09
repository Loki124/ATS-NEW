"""core 层 ViewSet 基类（#37）：含 core 的 ``ScopeQuerysetMixin`` 的 4 元组收口。

``ScopeQuerysetMixin`` 定义在 ``apps/core/permissions_v2``，故该基类放 core 层，
避免 ``apps/common`` 反向依赖 ``apps/core``。替换后 MRO 与原来完全一致，行为零变化。
"""
from rest_framework import viewsets

from apps.common.mixins import AuditMixin
from apps.common.views import EnvelopeWriteMixin
from apps.core.permissions_v2 import ScopeQuerysetMixin


class BaseModelViewSet(EnvelopeWriteMixin, ScopeQuerysetMixin, AuditMixin, viewsets.ModelViewSet):
    """写操作包信封 + 作用域过滤 + 自动审计的 ModelViewSet（各业务 app 标准写视图基类）。"""
