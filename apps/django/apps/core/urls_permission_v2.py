"""V2 权限系统 URL 路由."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views_permission_v2

router = DefaultRouter()
router.register(r'permissions/resources', views_permission_v2.PermissionResourceViewSet, basename='v2-resource')
router.register(r'permissions/templates', views_permission_v2.PermissionTemplateViewSet, basename='v2-template')
router.register(r'roles', views_permission_v2.RoleViewSet, basename='v2-role')

# 2026-07-12: ModelViewSet detail 路由 ^roles/<pk>/$ 会抢在 ^roles/clone-from-template/$ 之前 match
#   DRF @action(detail=False) 路由生成顺序晚于默认 detail pattern, 显式挂 clone_from_template_view
#   在 router.urls 之前确保优先 match.
clone_from_template_view = views_permission_v2.RoleViewSet.as_view({
    'post': 'clone_from_template',
})

urlpatterns = [
    path('roles/clone-from-template/', clone_from_template_view, name='v2-role-clone-from-template'),
] + list(router.urls)