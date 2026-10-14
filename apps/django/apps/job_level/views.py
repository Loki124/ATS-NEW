"""职级管理视图。"""
from django.db import IntegrityError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS

from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.common.views import EnvelopeWriteMixin
from apps.core.permission_check import has_perm
from apps.core.permissions_v2 import V2Permission
from apps.core.role_v2_query import is_super_admin

from .models import (
    JobLevel,
    JobLevelCategory,
    JobLevelGradeSetting,
    JobLevelSequence,
)
from .serializers import (
    JobLevelCategorySerializer,
    JobLevelGradeSettingSerializer,
    JobLevelSequenceSerializer,
    JobLevelSerializer,
)


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


class SingletonWritePermission(V2Permission):
    """单例配置写权限 — 固定校验专用 edit 码。

    ``V2Permission`` 按 action 派生只认 ``:edit`` 后缀, 而单例配置写码是
    ``grade:edit`` / ``sequence:edit`` (与职级本身的 ``:edit`` 语义不同),
    无法由读码派生得到; 故单例端点用本类显式声明写码,
    读操作仍走 ``V2Permission`` 的 ``job_level:list`` 读码。
    """

    #: 写操作权限码, 由使用方 (ViewSet.get_permissions) 赋值
    write_code = ''

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if is_super_admin(user):
            return True
        return has_perm(user, self.write_code)


class JobLevelViewSet(EnvelopeWriteMixin, SoftDeleteCRUDMixin, viewsets.ModelViewSet):
    """职级 — 完整 CRUD + 搜索/启停/类别筛选 + 分页。

    权限: 读 ``recruit:settings:job_level:list``, 写码见
    ``permission_required_map`` (create/edit/delete)。
    """

    queryset = JobLevel.objects.filter(deleted_at__isnull=True).select_related('category')
    serializer_class = JobLevelSerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:settings:job_level:list'
    permission_required_map = {
        'create': 'recruit:settings:job_level:create',
        'update': 'recruit:settings:job_level:edit',
        'partial_update': 'recruit:settings:job_level:edit',
        'destroy': 'recruit:settings:job_level:delete',
    }
    pagination_class = StandardResultsSetPagination

    _unique_field = 'name'
    _unique_message = '该职级名称已存在'

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
        # 按类别筛选 (前端职级页类别下拉联动)
        category_id = params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs


class JobLevelCategoryViewSet(EnvelopeWriteMixin, SoftDeleteCRUDMixin, viewsets.ModelViewSet):
    """职级类别 — 完整 CRUD (列表含 ``job_level_count``) + 搜索/启停筛选 + 分页。

    权限: 读 ``recruit:settings:job_level:category:list``, 写码见
    ``permission_required_map`` (category:create/edit/delete)。
    """

    queryset = JobLevelCategory.objects.filter(deleted_at__isnull=True)
    serializer_class = JobLevelCategorySerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:settings:job_level:category:list'
    permission_required_map = {
        'create': 'recruit:settings:job_level:category:create',
        'update': 'recruit:settings:job_level:category:edit',
        'partial_update': 'recruit:settings:job_level:category:edit',
        'destroy': 'recruit:settings:job_level:category:delete',
    }
    pagination_class = StandardResultsSetPagination

    _unique_field = 'name'
    _unique_message = '该类别名称已存在'

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


class JobLevelGradeSettingViewSet(EnvelopeWriteMixin, SoftDeleteCRUDMixin, viewsets.ModelViewSet):
    """职等上限 — 全局单例, ``GET/PUT /current/`` 读写 (无需传 PK)。"""

    queryset = JobLevelGradeSetting.objects.all()
    serializer_class = JobLevelGradeSettingSerializer
    permission_classes = [V2Permission]
    # 读操作 (含 GET /current/) 按职级列表读码; 写操作见 get_permissions
    permission_required = 'recruit:settings:job_level:list'

    _unique_field = 'max_grade'
    _unique_message = '职等上限配置已存在（全局仅一条）'

    def get_permissions(self):
        # PUT/PATCH /current/ 按 grade:edit 校验; 读操作按 job_level:list
        if self.action == 'current' and self.request.method not in SAFE_METHODS:
            perm = SingletonWritePermission()
            perm.write_code = 'recruit:settings:job_level:grade:edit'
            return [perm]
        return super().get_permissions()

    def get_object(self):
        """单例行: 忽略 URL pk, 恒返回全局唯一行。"""
        return JobLevelGradeSetting.get_solo()

    def perform_destroy(self, instance):
        """全局配置不支持删除。"""
        raise ValidationError({'detail': ['全局配置不支持删除']})

    @action(detail=False, methods=['get', 'put'], url_path='current')
    def current(self, request, *args, **kwargs):
        """GET 读 / PUT 写 — 全局职等上限单例。"""
        instance = self.get_object()
        if request.method == 'PUT':
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)
            return success_response(serializer.data)
        return success_response(self.get_serializer(instance).data)


class JobLevelSequenceViewSet(EnvelopeWriteMixin, SoftDeleteCRUDMixin, viewsets.ModelViewSet):
    """职级序列开关 — 全局单例, ``GET/PUT /current/`` 读写 (无需传 PK)。"""

    queryset = JobLevelSequence.objects.all()
    serializer_class = JobLevelSequenceSerializer
    permission_classes = [V2Permission]
    # 读操作 (含 GET /current/) 按职级列表读码; 写操作见 get_permissions
    permission_required = 'recruit:settings:job_level:list'

    _unique_field = 'management_enabled'
    _unique_message = '职级序列配置已存在（全局仅一条）'

    def get_permissions(self):
        # PUT/PATCH /current/ 按 sequence:edit 校验; 读操作按 job_level:list
        if self.action == 'current' and self.request.method not in SAFE_METHODS:
            perm = SingletonWritePermission()
            perm.write_code = 'recruit:settings:job_level:sequence:edit'
            return [perm]
        return super().get_permissions()

    def get_object(self):
        """单例行: 忽略 URL pk, 恒返回全局唯一行。"""
        return JobLevelSequence.get_solo()

    def perform_destroy(self, instance):
        """全局配置不支持删除。"""
        raise ValidationError({'detail': ['全局配置不支持删除']})

    @action(detail=False, methods=['get', 'put'], url_path='current')
    def current(self, request, *args, **kwargs):
        """GET 读 / PUT 写 — 全局职级序列开关单例。"""
        instance = self.get_object()
        if request.method == 'PUT':
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)
            return success_response(serializer.data)
        return success_response(self.get_serializer(instance).data)
