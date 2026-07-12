"""V2 权限系统 URL 路由."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views_permission_v2
from .permission_check_view import permission_check_view

router = DefaultRouter()
router.register(r'permissions/resources', views_permission_v2.PermissionResourceViewSet, basename='v2-resource')
router.register(r'permissions/templates', views_permission_v2.PermissionTemplateViewSet, basename='v2-template')
router.register(r'roles', views_permission_v2.RoleViewSet, basename='v2-role')
router.register(r'management-units', views_permission_v2.ManagementUnitViewSet, basename='v2-mgmt-unit')
router.register(r'user-roles', views_permission_v2.UserRoleViewSet, basename='v2-user-role')

# 2026-07-12: ModelViewSet detail 路由 ^<res>/<pk>/$ 会抢在 ^<res>/<action>/$ 之前 match
#   DRF @action(detail=False) 路由生成顺序晚于默认 detail pattern, 显式挂 collection action views
#   在 router.urls 之前确保优先 match.
clone_from_template_view = views_permission_v2.RoleViewSet.as_view({
    'post': 'clone_from_template',
})
suggest_scope_view = views_permission_v2.UserRoleViewSet.as_view({
    'get': 'suggest_scope',
})

urlpatterns = [
    path('roles/clone-from-template/', clone_from_template_view, name='v2-role-clone-from-template'),
    path('user-roles/suggest-scope/', suggest_scope_view, name='v2-user-role-suggest-scope'),
    path('permission/check/', permission_check_view, name='v2-permission-check'),
] + list(router.urls)