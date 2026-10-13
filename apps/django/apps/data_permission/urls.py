"""数据权限规则 URL 路由 - /api/v1/data-permissions/...

模板 / 动作字典 / 预设包路由挂在其下的子路径。DefaultRouter 按注册顺序生成 url，
带前缀的注册**必须先于空前缀 `''`**，否则会被后者（'' 的 detail regex `^(?P<pk>...)/$`）
抢先匹配 —— 历史上 templates 踩过此坑，actions / action-presets 同理。
"""
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter

from .views import (
    DataPermissionActionPresetViewSet,
    DataPermissionActionViewSet,
    DataPermissionRuleViewSet,
    DataPermTemplateViewSet,
)

router = DefaultRouter()
router.register(r'templates', DataPermTemplateViewSet, basename='data-perm-template')
router.register(r'actions', DataPermissionActionViewSet, basename='data-perm-action')
router.register(r'action-presets', DataPermissionActionPresetViewSet, basename='data-perm-action-preset')
router.register(r'', DataPermissionRuleViewSet, basename='data-permission')

# DRF DefaultRouter 的 APIRootView 默认走全局 IsAuthenticatedDenyByDefault, 未登录会 403 阻断
# FE 路由发现. 根视图改成 AllowAny; 真实 /data-permissions/* 详情接口仍由 ViewSet 的
# permission_classes = [IsSuperAdmin] 守住 (与 field_acl 同款处理).
router.APIRootView.permission_classes = [AllowAny]

urlpatterns = router.urls
