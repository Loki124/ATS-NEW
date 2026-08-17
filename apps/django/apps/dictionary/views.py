"""数据字典视图。"""
from django.db import IntegrityError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.common.pagination import StandardResultsSetPagination

from .models import DictionaryItem, DictionaryType
from .serializers import DictionaryItemSerializer, DictionaryTypeSerializer


class DictionaryCRUDMixin:
    """写操作的统一兜底。

    软删除记录仍占着 ``unique_together`` 的坑位 (DB 约束不认 ``deleted_at``),
    因此"删了再建同名"在极端并发下可能落到 ``IntegrityError`` → 500。
    这里统一捕获并转成 400 友好错误, 避免 500。

    其余大多数重复场景会被 DRF 的 ``UniqueTogetherValidator`` /
    ``UniqueValidator`` 在校验阶段直接拦截 (也返回 400)。
    """

    # 冲突时返回给前端的字段名与中文提示 (由子类覆盖).
    _unique_field: str = 'key'
    _unique_message: str = '该 key 已存在（同一字典类型下不可重复）'

    def perform_create(self, serializer):
        """写入新记录; 唯一约束冲突 → 视作校验失败转 400。"""
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError({self._unique_field: [self._unique_message]})

    def perform_update(self, serializer):
        """更新记录; 唯一约束冲突 → 视作校验失败转 400。"""
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError({self._unique_field: [self._unique_message]})

    def perform_destroy(self, instance):
        """DELETE → 软删 (保留历史数据)。"""
        instance.soft_delete()


class DictionaryTypeViewSet(DictionaryCRUDMixin, viewsets.ModelViewSet):
    """字典类型 — 完整 CRUD (创建 / 列表 / 详情 / 更新 / 删除)。"""

    queryset = DictionaryType.objects.filter(deleted_at__isnull=True)
    serializer_class = DictionaryTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    lookup_field = 'code'

    _unique_field = 'code'
    _unique_message = '该字典类型 code 已存在'


class DictionaryItemViewSet(DictionaryCRUDMixin, viewsets.ModelViewSet):
    """字典项 — 完整 CRUD; 支持按 type_code 过滤。"""

    queryset = (
        DictionaryItem.objects
        .filter(deleted_at__isnull=True, is_active=True)
        .select_related('type')
    )
    serializer_class = DictionaryItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    _unique_field = 'key'
    _unique_message = '该字典项下 key 已存在（同一字典类型下不可重复）'

    def get_queryset(self):
        qs = super().get_queryset()
        type_code = self.request.query_params.get('type_code')
        if type_code:
            qs = qs.filter(type__code=type_code)
        return qs
