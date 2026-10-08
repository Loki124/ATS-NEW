"""Core 通用 URL - 2026-07-01: 加 /users/departments/ alias (FE 期望 path)"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DepartmentViewSet, PermissionViewSet, RoleViewSet, UserViewSet

# 2026-06-30 花无缺: 改回具名前缀 (之前误改成 r'' 致 user-detail 错吃 candidates/invitations 路径).
#   router r'users' + r'^$' 模式 在 v1 namespace 下编译为 '^api/v1/users/$' (有 users/ 前缀),
#   跟 candidate/urls.py (r'' + '^$' = '^api/v1/candidates/$') 路径独立, 不会误吃.
#   同时改 urlpatterns 直接挂 router.urls (不要 path('', include(router.urls)) 包裹,
#   包裹会引入 ^users/^$ 双 ^ 永不 match).
#
# 2026-07-01: FE 调 /users/departments/ (错路径), 实际 /departments/ 是 list endpoint.
#   加 alias path 让 /users/departments/ 返 DepartmentViewSet list.
department_list = DepartmentViewSet.as_view({'get': 'list'})

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')

urlpatterns = [
    # FE 兼容 alias: /users/departments/ 也返部门列表
    path('users/departments/', department_list, name='user-departments-alias'),
] + list(router.urls)
