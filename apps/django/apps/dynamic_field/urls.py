from django.urls import path

from .views import (
    DynamicFieldViewSet,
    FieldModuleViewSet,
    FieldGroupViewSet,
    FieldLinkageRuleViewSet,
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
        '<str:resource>/fields/import/',
        DynamicFieldViewSet.as_view({'post': 'import_fields'}),
        name='dynamicfield-import',
    ),
    path(
        '<str:resource>/fields/reorder/',
        DynamicFieldViewSet.as_view({'post': 'reorder'}),
        name='dynamicfield-reorder',
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
