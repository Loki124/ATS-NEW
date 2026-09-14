"""用户/部门/角色/权限 视图

T30.175 (V2 cutover follow-up):
- RoleViewSet.queryset 改用 RoleV2 (新表 'roles' 但 schema 是 V2 role_code/role_name)
- UserViewSet.get_queryset / PermissionViewSet.get_queryset 改用 role_v2_query 辅助
- PermissionViewSet 改用 V2 PermissionResource (V1 permissions 表已 DROP)
"""
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import User, Department
from .serializers import (
    UserSerializer, UserMinimalSerializer,
    DepartmentSerializer,
)
from .serializers_permission_v2 import (
    RoleSerializer as RoleV2Serializer,
    PermissionResourceSerializer,
)
from .permissions import IsAuthenticated, IsSuperAdmin, UserViewPermission
from .role_v2_query import user_has_any_role, is_super_admin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.mixins import SoftDeleteViewSetMixin
from apps.core.models_permission_v2 import (
    RoleV2, UserRoleV2, RolePermissionV2, PermissionResource,
)
from .permissions_v2 import V2Permission


class UserViewSet(viewsets.ModelViewSet):
    """用户 CRUD - 收紧权限: 列表/搜索仅 HRBP+, 详情本人或 HRBP+, 写仅超管 (Fix 1)"""
    queryset = User.objects.filter(deleted_at__isnull=True).select_related('department', 'direct_manager')
    serializer_class = UserSerializer
    permission_classes = [UserViewPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'level', 'is_active']
    search_fields = ['username', 'employee_id', 'phone', 'email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'username']
    ordering = ['username']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # HRBP+ 看所有在职; 其它角色仅看自己
        if is_super_admin(user) or user_has_any_role(user, HRBP_TIER):
            return qs
        return qs.filter(pk=user.pk)

    def list(self, request, *args, **kwargs):
        """list 默认按 UserMinimalSerializer 脱敏 phone/email, 防止 HR 拿到全员手机号"""
        self.serializer_class = UserMinimalSerializer
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """仅在职人员 - 强制脱敏字段 (Fix 1)"""
        qs = self.get_queryset().filter(is_active=True)
        page = self.paginate_queryset(qs)
        serializer = UserMinimalSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def soft_delete(self, request, pk=None):
        user = self.get_object()
        user.soft_delete()
        return Response({'success': True})


class DepartmentViewSet(viewsets.ModelViewSet):
    """部门 CRUD - HRBP+ 可写, 其它角色只读 (Fix 1)"""
    queryset = Department.objects.filter(is_active=True).select_related(
        'parent', 'leader', 'manager_2', 'manager_3', 'hrbp'
    )
    serializer_class = DepartmentSerializer
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'code']
    filterset_fields = ['parent', 'is_active']

    def _envelope(self, data):
        return Response({'success': True, 'data': data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self._envelope(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self._envelope(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return self._envelope(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return self._envelope({'id': instance.id})

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """部门成员 - 强制脱敏 (Fix 1)"""
        dept = self.get_object()
        users = User.objects.filter(
            department=dept, is_active=True, deleted_at__isnull=True
        ).select_related('department')
        page = self.paginate_queryset(users)
        serializer = UserMinimalSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        dept = self.get_object()
        return Response({
            'success': True,
            'data': self._build_tree(dept),
        })

    def _build_tree(self, dept):
        return {
            'id': dept.id,
            'name': dept.name,
            'code': dept.code,
            'children': [self._build_tree(child) for child in dept.children.filter(is_active=True)],
        }


class RoleViewSet(viewsets.ModelViewSet):
    """角色 CRUD (V2 RoleV2) - 仅超管 (Fix 1)

    T30.175: V1 Role 表已 DROP, 改读 RoleV2 (db_table='roles' 但 schema 是 V2).
    search_fields 改 role_code / role_name.
    """
    queryset = RoleV2.objects.filter(status=1)
    serializer_class = RoleV2Serializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['role_code', 'role_name']


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """权限列表（只读）- 收紧到 HRBP+ (Fix 1)

    T30.175: V1 Permission 表已 DROP, 改读 V2 PermissionResource.
    普通用户视角: 仅返回自己 V2 role_code 关联的 PermissionResource.
    """
    queryset = PermissionResource.objects.filter(status=1, system_code='recruit')
    serializer_class = PermissionResourceSerializer
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['module', 'resource_type']

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user) or user_has_any_role(user, HRBP_TIER):
            return PermissionResource.objects.filter(status=1, system_code='recruit')
        # 普通用户仅看自己 V2 角色关联的 PermissionResource
        role_codes = list(UserRoleV2.objects.filter(
            user_id=user.pk, system_code='recruit',
        ).values_list('role_code', flat=True))
        if not role_codes:
            return PermissionResource.objects.none()
        resource_codes = set(RolePermissionV2.objects.filter(
            role_code__in=role_codes, system_code='recruit',
        ).values_list('resource_code', flat=True))
        if not resource_codes:
            return PermissionResource.objects.none()
        return PermissionResource.objects.filter(
            resource_code__in=resource_codes, status=1, system_code='recruit',
        ).distinct()
