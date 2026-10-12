"""数据权限规则 URL 路由 - /api/v1/data-permissions/...

模板路由挂在其下的 `templates/` 子路径。DefaultRouter 按注册顺序生成 url，
`templates` 必须先于空前缀 `''` 注册，否则会被后者抢先匹配。
"""
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter

from .views import DataPermissionRuleViewSet, DataPermTemplateViewSet

router = DefaultRouter()
router.register(r'templates', DataPermTemplateViewSet, basename='data-perm-template')
router.register(r'', DataPermissionRuleViewSet, basename='data-permission')

# DRF DefaultRouter 的 APIRootView 默认走全局 IsAuthenticatedDenyByDefault, 未登录会 403 阻断
# FE 路由发现. 根视图改成 AllowAny; 真实 /data-permissions/* 详情接口仍由 ViewSet 的
# permission_classes = [IsSuperAdmin] 守住 (与 field_acl 同款处理).
router.APIRootView.permission_classes = [AllowAny]

urlpatterns = router.urls
