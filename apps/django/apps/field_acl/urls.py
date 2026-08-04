"""Field ACL URL Routes - /api/v1/field-acl/..."""
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter

from .views import FieldACLViewSet

router = DefaultRouter()
router.register(r'', FieldACLViewSet, basename='field-acl')

# T01.2 (2026-08-04 寇豆码): DRF DefaultRouter 自动生成的 APIRootView 默认走
#   全局 IsAuthenticatedDenyByDefault, 列出所有路由时无登录态会 403, 阻断 FE
#   路由发现. 这里把根视图权限改成 AllowAny —— 真正的 field-acl/* 详情接口仍由
#   FieldACLViewSet.permission_classes = [IsSuperAdmin] 守住.
router.APIRootView.permission_classes = [AllowAny]

urlpatterns = router.urls
