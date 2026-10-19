"""动态策略 (Dynamic Strategy) ViewSet.

从「操作权限」(原按 ROLE 配置于身份管理角色编辑弹窗) 抽离出的可复用策略实体:
绑定到 ROLE(经 DynamicStrategyAssignment), 作用于「受限制的功能」(业务模块).

端点 (basename='dynamic-strategies', prefix=/api/v1/dynamic-strategies/):
- GET    /                             列表(按 status 过滤, 按 strategy_name/strategy_code 搜索, 服务端分页)
- POST   /                             创建
- GET    /{strategy_code}/            详情
- PUT    /{strategy_code}/            整体更新(同步角色绑定)
- PATCH  /{strategy_code}/            部分更新(同步角色绑定)
- DELETE /{strategy_code}/            删除
- GET    /options/                    模块×动作字典 + 预设包 选项

守卫复用与现有权限管理 V2 视图一致的 V2Permission (superuser / SUPER_ADMIN bypass).
"""
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.data_permission.models import (
    DataPermissionAction,
    DataPermissionActionPreset,
)

from .models_permission_v2 import (
    DynamicStrategy,
    DynamicStrategyAssignment,
    RoleV2,
)
from .permissions_v2 import V2Permission
from .serializers_permission_v2 import DynamicStrategySerializer


STRATEGY_MODULES = [
    {'key': 'demand', 'label': '招聘需求'},
    {'key': 'process', 'label': '招聘流程'},
    {'key': 'position', 'label': '招聘职位'},
    {'key': 'candidate', 'label': '候选人管理'},
    {'key': 'talent', 'label': '人才库'},
]


class DynamicStrategyViewSet(viewsets.ModelViewSet):
    queryset = DynamicStrategy.objects.all()
    serializer_class = DynamicStrategySerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:settings:dynamic_strategy:list'
    pagination_class = StandardResultsSetPagination  # 服务端分页, 对齐其它 V2 端点
    lookup_field = 'strategy_code'
    search_fields = ['strategy_code', 'strategy_name']
    filterset_fields = ['status']

    def get_queryset(self):
        return DynamicStrategy.objects.all().order_by('strategy_code')

    def list(self, request, *args, **kwargs):
        """服务端分页 + {success, data} 信封, 对齐其它 V2 endpoint."""
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(self.get_serializer(instance).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # 仅当客户端显式传入 role_codes 时才同步绑定(避免缺失即清空)
        raw = request.data.get('role_codes', None)
        if raw is not None:
            self._sync_assignments(serializer.instance, raw)
        return success_response(
            self.get_serializer(serializer.instance).data,
            status_code=201,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        raw = request.data.get('role_codes', None)
        if raw is not None:
            self._sync_assignments(instance, raw)
        return success_response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return success_response(None)

    @transaction.atomic
    def _sync_assignments(self, strategy, role_codes):
        """删除该策略全部现有绑定, 再为存在于 RoleV2 的 role_code 重建绑定.

        幂等 + 仅绑定真实存在的角色(防御性, 序列化器已校验一次).
        """
        strategy_code = strategy.strategy_code
        DynamicStrategyAssignment.objects.filter(strategy_code=strategy_code).delete()
        valid = set(RoleV2.objects.filter(
            role_code__in=role_codes or [], system_code=strategy.system_code,
        ).values_list('role_code', flat=True))
        if valid:
            DynamicStrategyAssignment.objects.bulk_create([
                DynamicStrategyAssignment(
                    system_code=strategy.system_code,
                    strategy_code=strategy_code,
                    role_code=rc,
                )
                for rc in valid
            ])

    @action(detail=False, methods=['get'], url_path='options')
    def options(self, request):
        """GET /api/v1/dynamic-strategies/options/ — 模块×动作字典 + 预设包.

        驱动器(策略编辑弹窗)下拉: 可选模块、动作字典、动作预设包.
        """
        actions = list(DataPermissionAction.objects.values(
            'key', 'label', 'category', 'destructive', 'enabled',
        ))
        presets = list(DataPermissionActionPreset.objects.values(
            'key', 'label', 'action_keys', 'module',
        ))
        return success_response({
            'modules': STRATEGY_MODULES,
            'actions': actions,
            'presets': presets,
        })
