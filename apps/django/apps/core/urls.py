"""Core 通用 URL"""
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, DepartmentViewSet, RoleViewSet, PermissionViewSet

# 2026-06-30 花无缺: 改回具名前缀 (之前误改成 r'' 致 user-detail 错吃 candidates/invitations 路径).
#   router r'users' + r'^$' 模式 在 v1 namespace 下编译为 '^api/v1/users/$' (有 users/ 前缀),
#   跟 candidate/urls.py (r'' + '^$' = '^api/v1/candidates/$') 路径独立, 不会误吃.
#   同时改 urlpatterns 直接挂 router.urls (不要 path('', include(router.urls)) 包裹,
#   包裹会引入 ^users/^$ 双 ^ 永不 match).
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')

urlpatterns = router.urls
