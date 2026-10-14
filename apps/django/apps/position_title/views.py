"""职务管理视图。"""
from django.db import IntegrityError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from apps.common.pagination import StandardResultsSetPagination
from apps.common.views import EnvelopeWriteMixin
from apps.core.permissions_v2 import V2Permission

from .models import JobTitle
from .serializers import JobTitleSerializer


class SoftDeleteCRUDMixin:
    """写操作统一兜底。

    软删行仍占着 unique 约束的坑位 (DB 约束不认 ``deleted_at``),
    "删了再建同名" 在极端并发下可能落到 ``IntegrityError`` → 500;
    这里统一捕获并转成 400 友好错误, 避免 500。
    """

    #: 冲突时返回给前端的字段名与中文提示 (由子类覆盖)
    _unique_field: str = 'name'
    _unique_message: str = '该名称已存在'

    def perform_create(self, serializer):
        """写入新记录; 自动带入当前用户, 唯一约束冲突 → 视作校验失败转 400。"""
        try:
            serializer.save(
                created_by=self.request.user,
                updated_by=self.request.user,
            )
        except IntegrityError:
            raise ValidationError({self._unique_field: [self._unique_message]})

    def perform_update(self, serializer):
        """更新记录; 自动带入当前用户, 唯一约束冲突 → 视作校验失败转 400。"""
        try:
            serializer.save(updated_by=self.request.user)
        except IntegrityError:
            raise ValidationError({self._unique_field: [self._unique_message]})

    def perform_destroy(self, instance):
        """DELETE → 软删 (保留历史数据)。"""
        instance.soft_delete()


class JobTitleViewSet(EnvelopeWriteMixin, SoftDeleteCRUDMixin, viewsets.ModelViewSet):
    """职务 — 完整 CRUD + 列表搜索/启停筛选 + 分页。

    权限: 读 ``recruit:settings:job_title:list``, 写码见
    ``permission_required_map`` (create/edit/delete)。
    """

    queryset = (
        JobTitle.objects
        .filter(deleted_at__isnull=True)
        .select_related('job_family', 'job_category', 'job_subcategory')
    )
    serializer_class = JobTitleSerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:settings:job_title:list'
    permission_required_map = {
        'create': 'recruit:settings:job_title:create',
        'update': 'recruit:settings:job_title:edit',
        'partial_update': 'recruit:settings:job_title:edit',
        'destroy': 'recruit:settings:job_title:delete',
    }
    pagination_class = StandardResultsSetPagination

    _unique_field = 'name'
    _unique_message = '该职务名称已存在'

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        q = params.get('q') or params.get('search')
        if q:
            qs = qs.filter(name__icontains=q)
        # 启用状态筛选: is_enabled=true|false; 缺省/all 不过滤
        enabled = params.get('is_enabled')
        if enabled in ('true', 'false'):
            qs = qs.filter(is_enabled=(enabled == 'true'))
        return qs
