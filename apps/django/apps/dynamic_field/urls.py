from django.urls import path

from .views import (
    DynamicFieldViewSet,
    FieldGroupViewSet,
    FieldLinkageRuleViewSet,
    FieldModuleViewSet,
)

_detail = {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}

urlpatterns = [
    # --- 字段定义 (DynamicField) ---
    path(
        '<str:resource>/fields/export/',
        DynamicFieldViewSet.as_view({'get': 'export'}),
        name='dynamicfield-export',
    ),
    path(
        '<str:resource>/fields/template/',
        DynamicFieldViewSet.as_view({'get': 'template'}),
        name='dynamicfield-template',
    ),
    path(
        '<str:resource>/fields/import/',
        DynamicFieldViewSet.as_view({'post': 'import_fields'}),
        name='dynamicfield-import',
    ),
    path(
        '<str:resource>/fields/reorder/',
        DynamicFieldViewSet.as_view({'post': 'reorder'}),
        name='dynamicfield-reorder',
    ),
    # 2026-09-24 兵哥: 限制条件校验 + 录入落库端点 (须排在 <str:pk> 之前, 否则被 detail 路由截走)
    path(
        '<str:resource>/fields/validate-values/',
        DynamicFieldViewSet.as_view({'post': 'validate_values'}),
        name='dynamicfield-validate-values',
    ),
    path(
        '<str:resource>/fields/values/',
        DynamicFieldViewSet.as_view({'get': 'save_values', 'post': 'save_values'}),
        name='dynamicfield-values',
    ),
    path(
        '<str:resource>/fields/<str:pk>/validate/',
        DynamicFieldViewSet.as_view({'post': 'validate_field'}),
        name='dynamicfield-validate',
    ),
    path(
        '<str:resource>/fields/',
        DynamicFieldViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='dynamicfield-list',
    ),
    path(
        '<str:resource>/fields/<str:pk>/',
        DynamicFieldViewSet.as_view(_detail),
        name='dynamicfield-detail',
    ),

    # --- 模块配置 (FieldModule, 父级) ---
    path(
        '<str:resource>/modules/',
        FieldModuleViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='fieldmodule-list',
    ),
    # 2026-09-14 动态字段拆分: 必须排在 <str:pk> 之前, 否则 'ensure-default' 会被 pk 路由截走
    path(
        '<str:resource>/modules/ensure-default/',
        FieldModuleViewSet.as_view({'post': 'ensure_default'}),
        name='fieldmodule-ensure-default',
    ),
    path(
        '<str:resource>/modules/<str:pk>/',
        FieldModuleViewSet.as_view(_detail),
        name='fieldmodule-detail',
    ),

    # --- 分组配置 (FieldGroup, 子级) ---
    path(
        '<str:resource>/groups/',
        FieldGroupViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='fieldgroup-list',
    ),
    path(
        '<str:resource>/groups/<str:pk>/',
        FieldGroupViewSet.as_view(_detail),
        name='fieldgroup-detail',
    ),

    # --- 联动规则 (FieldLinkageRule, 同模块) ---
    path(
        '<str:resource>/linkage-rules/',
        FieldLinkageRuleViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='fieldlinkagerule-list',
    ),
    path(
        '<str:resource>/linkage-rules/<str:pk>/',
        FieldLinkageRuleViewSet.as_view(_detail),
        name='fieldlinkagerule-detail',
    ),
]
