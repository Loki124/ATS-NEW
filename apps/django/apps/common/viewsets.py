"""公共 ViewSet 基类（#37：合并重复的 EnvelopeWriteMixin 等基类堆叠）。

各 app 的 ModelViewSet 大量重复 `(EnvelopeWriteMixin, ... viewsets.ModelViewSet)` 的手工堆叠。
收口为以下基类——替换后 MRO 与原来**完全一致**，行为零变化：

- ``EnvelopeModelViewSet``: ``EnvelopeWriteMixin + viewsets.ModelViewSet``
- ``EnvelopeAuditModelViewSet``: ``EnvelopeWriteMixin + AuditMixin + viewsets.ModelViewSet``

含 core 层 ``ScopeQuerysetMixin`` 的 4 元组基类见 ``apps/core/viewsets.py:BaseModelViewSet``
（``ScopeQuerysetMixin`` 定义在 core，故放 core 层，避免 common 反向依赖 core）。
"""
from rest_framework import viewsets

from apps.common.mixins import AuditMixin
from apps.common.views import EnvelopeWriteMixin


class EnvelopeModelViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    """写操作统一包 {success, data} 信封的 ModelViewSet（无审计/作用域过滤）。"""


class EnvelopeAuditModelViewSet(EnvelopeWriteMixin, AuditMixin, viewsets.ModelViewSet):
    """写操作包信封 + 自动记录 created_by/updated_by 的 ModelViewSet（无作用域过滤）。"""
