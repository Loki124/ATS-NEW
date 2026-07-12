"""V2 权限系统 URL 路由."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views_permission_v2

router = DefaultRouter()
router.register(r'permissions/resources', views_permission_v2.PermissionResourceViewSet, basename='v2-resource')
router.register(r'permissions/templates', views_permission_v2.PermissionTemplateViewSet, basename='v2-template')

urlpatterns = list(router.urls)