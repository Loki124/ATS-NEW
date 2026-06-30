"""Core 通用 URL"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, DepartmentViewSet, RoleViewSet, PermissionViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'', DepartmentViewSet, basename='department')
router.register(r'', RoleViewSet, basename='role')
router.register(r'', PermissionViewSet, basename='permission')

urlpatterns = [
    path('', include(router.urls)),
]
