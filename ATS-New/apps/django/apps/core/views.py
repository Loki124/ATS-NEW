"""用户/部门/角色/权限 视图"""
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import User, Department, Role, Permission, UserRole
from .serializers import (
    UserSerializer, UserMinimalSerializer,
    DepartmentSerializer, RoleSerializer, PermissionSerializer,
)
from .permissions import IsAuthenticated, IsSuperAdmin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.mixins import SoftDeleteViewSetMixin


class UserViewSet(viewsets.ModelViewSet):
    """用户 CRUD"""
    queryset = User.objects.filter(deleted_at__isnull=True).select_related('department', 'direct_manager')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'level', 'is_active']
    search_fields = ['username', 'employee_id', 'phone', 'email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'username']
    ordering = ['username']

    @action(detail=False, methods=['get'])
    def active(self, request):
        """仅在职人员（过滤离职）"""
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
    """部门 CRUD"""
    queryset = Department.objects.filter(is_active=True).select_related('parent', 'leader')
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'code']
    filterset_fields = ['parent', 'is_active']

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """部门成员"""
        dept = self.get_object()
        users = User.objects.filter(
            department=dept, is_active=True, deleted_at__isnull=True
        ).select_related('department')
        page = self.paginate_queryset(users)
        serializer = UserMinimalSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        """部门树"""
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
    """角色 CRUD"""
    queryset = Role.objects.filter(is_active=True)
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['code', 'name']


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """权限列表（只读）"""
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['module']
