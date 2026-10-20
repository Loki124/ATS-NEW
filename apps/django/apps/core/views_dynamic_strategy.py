"""动态策略 (Dynamic Strategy) ViewSet.

从「操作权限」(原按 ROLE 配置于身份管理角色编辑弹窗) 抽离出的可复用策略实体:
全局生效(2026-10-19 起不绑定角色), 作用于「受限制的功能」(业务模块).

端点 (basename='dynamic-strategies', prefix=/api/v1/dynamic-strategies/):
- GET    /                             列表(按 status 过滤, 按 strategy_name/strategy_code 搜索, 服务端分页)
- POST   /                             创建
- GET    /{strategy_code}/            详情
- PUT    /{strategy_code}/            整体更新
- PATCH  /{strategy_code}/            部分更新
- DELETE /{strategy_code}/            删除
- GET    /options/                    模块×动作字典 + 预设包 选项

守卫复用与现有权限管理 V2 视图一致的 V2Permission (superuser / SUPER_ADMIN bypass).
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.data_permission.models import (
    DataPermissionAction,
    DataPermissionActionPreset,
)
# 动态策略的「配置写范围」弹窗（RuleConfigModal）按模块取维度/属性字段下拉，
# 与角色数据权限同源、角色无关 —— 直接复用 role_scope_api.options_payload 的
# 「模块 × 维度 × 属性字段」矩阵，避免两处各算一份（维度隐藏/文案/属性场景易漂移）。
from apps.data_permission.role_scope_api import options_payload as _dp_options_payload

from .models_permission_v2 import DynamicStrategy, PermissionResource
from .permissions_v2 import V2Permission
from .serializers_permission_v2 import DynamicStrategySerializer

SYSTEM_CODE = 'recruit'

# ---------------------------------------------------------------------------
# 策略模块 → 资源 module 映射（1:N，2026-10-20）
#
# 只服务于「受限功能」候选区（本文件 _governed_resources）。
#
# 🔴 为什么不复用 apps.data_permission.role_scope_api.DATA_PERM_MODULE_RESOURCE_MODULES：
#    那张表被卡 1.3 的 featureGranted 复用（role_scope_api.py:271-273），用于判定
#    「该角色在角色数据权限页的某模块卡片是否可用」。把它扩成 1:N（candidate 并入
#    interview / application）会让**只持有面试资源**的角色在「候选人管理」卡片也
#    变成 featureGranted=true —— 那是波及全量角色的、与本需求无关的行为变更。
#    两张表语义不同：那边是「角色有没有这个功能」，这边是「这个功能归哪个策略模块管」。
#
# 🔴 改这里必须同步前端：web/app/src/pages/settings/DynamicStrategy.vue 的
#    STRATEGY_MODULE_RESOURCE_MODULES（用于从 grantedResourceCodes 按模块切分，
#    已是 Record<string, string[]> 的 1:N 形态，与下方常量互为镜像，两侧必须一致）。
#
# 两个反直觉点，硬编码必错：
#   - talent(人才库数据) → 资源 module `talent_pool`(人才库功能)；但**不**把 talent_pool
#     归入 talent 策略模块 —— 兵哥清单把「放入人才库」(recruit:talent_pool:create) 列在
#     「候选人管理」下，故 talent_pool 并进 candidate 的策略模块集合（见下方 candidate）。
#   - process(招聘流程数据) → 资源 module `settings`(recruitment_process:*)，
#     settings 下有 123 条启用 BUTTON，不过滤会灌爆候选区。
# candidate 扩到 interview / application / talent_pool 是兵哥清单把「安排面试 / 推进流程 /
# 放入人才库」都归在候选人管理下的结果（见 core.0041 docstring）。
# ---------------------------------------------------------------------------
STRATEGY_MODULE_RESOURCE_MODULES: dict[str, set] = {
    'demand': {'demand'},
    'process': {'settings'},
    'position': {'position'},
    'candidate': {'candidate', 'interview', 'application', 'talent_pool'},
    # talent 策略模块当前无受管控资源（talent_pool:create 已并入 candidate）；
    # 保留 key 占位，_governed_resources 里 .get('talent') or set() 自然得到空候选区。
    'talent': set(),
}

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
        return success_response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return success_response(None)

    @action(detail=False, methods=['get'], url_path='options')
    def options(self, request):
        """GET /api/v1/dynamic-strategies/options/ — 模块×维度×属性字段矩阵 + 动作字典 + 预设包 + 受管控资源.

        驱动器(策略编辑弹窗)下拉: 可选模块、每模块的维度/属性字段(供「配置写范围」弹窗)、
        动作字典、动作预设包、每模块的受管控资源(供「受限功能」勾选).
        维度/属性字段与角色数据权限同源(角色无关).
        """
        actions = list(DataPermissionAction.objects.values(
            'key', 'label', 'category', 'destructive', 'enabled',
        ))
        presets = list(DataPermissionActionPreset.objects.values(
            'key', 'label', 'action_keys', 'module',
        ))
        # 模块 × 维度 × 属性字段矩阵(角色无关)；dimensions/attributeFields 下发给
        # RuleConfigModal 作为条件组编辑器的值域与选项来源。
        dp = _dp_options_payload()
        return success_response({
            'modules': dp['modules'],
            'actions': actions,
            'presets': presets,
            'governedResources': self._governed_resources(),
        })

    @staticmethod
    def _governed_resources():
        """按策略模块分组下发「受策略管控」的按钮资源（2026-10-20）。

        返回 {策略模块key: [{resourceCode, resourceName, subModule}, ...]}。

        三道过滤缺一不可：
        1. `strategy_governed=True` —— 资源目录里显式登记的管控开关（core.0040 置位）；
        2. `resource_type='BUTTON'` —— 「受限功能」是按钮级功能，菜单不是功能；
        3. `status=1` —— 停用资源已被 has_perm 永拒，放进候选即「勾了也不生效」。

        🔴 策略模块 → 资源 module 的映射**必须**使用本文件顶部定义的独立 1:N 常量
        STRATEGY_MODULE_RESOURCE_MODULES，**不可**复用 role_scope_api 的
        DATA_PERM_MODULE_RESOURCE_MODULES（那是 1:1 且被 featureGranted 复用，
        改它会波及全量角色）。两个反直觉点，硬编码必错：
          - talent(人才库数据) 对应资源 module `talent_pool`(人才库功能)；
          - process(招聘流程数据) 对应资源 module `settings`(recruitment_process:*)，
            settings 下有 200+ 资源，不过滤会直接把整个系统设置灌进候选区。
        """
        out = {}
        for module_key in DynamicStrategy.VALID_MODULE_KEYS:
            res_modules = STRATEGY_MODULE_RESOURCE_MODULES.get(module_key) or set()
            rows = PermissionResource.objects.filter(
                system_code=SYSTEM_CODE,
                module__in=res_modules,
                resource_type='BUTTON',
                status=1,
                strategy_governed=True,
            ).order_by('module', 'resource_code').values_list(
                'resource_code', 'resource_name',
            )
            out[module_key] = [
                {
                    'resourceCode': code,
                    'resourceName': name,
                    # 子模块不是独立字段，是资源码第 3 段（与前端 ResourcesTab.vue 同口径）；
                    # 3 段码（recruit:demand:list）没有子模块层，留空串。
                    'subModule': code.split(':')[2] if len(code.split(':')) >= 4 else '',
                }
                for code, name in rows
            ]
        return out
