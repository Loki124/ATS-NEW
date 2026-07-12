"""V2 权限系统 ViewSets + function views."""
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from rest_framework import status as http_status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets

from .models_permission_v2 import (
    PermissionResource, PermissionTemplate, RoleV2, RolePermissionV2,
    ManagementUnit, UserRoleV2,
)
from .permissions_v2 import V2Permission
from .scope_resolver import resolve_scope


class PermissionResourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PermissionResource.objects.filter(status=1)
    permission_classes = [V2Permission]
    pagination_class = None
    filterset_fields = ['module', 'resource_type']
    search_fields = ['resource_code', 'resource_name']

    def get_serializer_class(self):
        from .serializers_permission_v2 import PermissionResourceSerializer
        return PermissionResourceSerializer


class PermissionTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PermissionTemplate.objects.filter(status=1)
    permission_classes = [V2Permission]
    pagination_class = None
    filterset_fields = ['is_system']

    def get_serializer_class(self):
        from .serializers_permission_v2 import PermissionTemplateSerializer
        return PermissionTemplateSerializer


class RoleViewSet(viewsets.ModelViewSet):
    queryset = RoleV2.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:role:list'
    pagination_class = None
    search_fields = ['role_code', 'role_name']
    filterset_fields = ['status', 'is_system']

    def get_serializer_class(self):
        from .serializers_permission_v2 import RoleSerializer
        return RoleSerializer

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def clone_from_template(self, request):
        """POST /roles/clone-from-template/
        body: {template_code, role_code, role_name, custom_permissions?: {add:[], remove:[]}}
        """
        body = request.data
        template_code = body.get('template_code')
        new_role_code = body.get('role_code')
        new_role_name = body.get('role_name')
        if not all([template_code, new_role_code, new_role_name]):
            return Response(
                {'success': False, 'message': 'template_code/role_code/role_name 必填'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        template = PermissionTemplate.objects.filter(
            template_code=template_code, status=1
        ).first()
        if not template:
            return Response(
                {'success': False, 'message': f'Template {template_code} 不存在'},
                status=http_status.HTTP_404_NOT_FOUND,
            )
        if RoleV2.objects.filter(role_code=new_role_code, system_code='recruit').exists():
            return Response(
                {'success': False, 'message': f'角色 {new_role_code} 已存在'},
                status=http_status.HTTP_409_CONFLICT,
            )

        # 1. 新建 role
        role = RoleV2.objects.create(
            system_code='recruit',
            role_code=new_role_code,
            role_name=new_role_name,
            template_code=template_code,
            description=f'从 {template_code} 复制于 {request.user.username}',
        )
        # 2. permission_codes: 模板 + 加 - 删
        codes = list(template.permission_codes or [])
        custom = body.get('custom_permissions') or {}
        codes = [c for c in codes if c not in (custom.get('remove') or [])]
        codes = list(set(codes + (custom.get('add') or [])))
        # 3. 批量插 role_permission
        if codes:
            RolePermissionV2.objects.bulk_create([
                RolePermissionV2(role_code=new_role_code, resource_code=c, system_code='recruit')
                for c in codes
            ])
        return Response(
            self.get_serializer(role).data,
            status=http_status.HTTP_201_CREATED,
        )


class ManagementUnitViewSet(viewsets.ModelViewSet):
    queryset = ManagementUnit.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:mgmt_unit:list'
    pagination_class = None
    filterset_fields = ['unit_type', 'status']

    def get_serializer_class(self):
        from .serializers_permission_v2 import ManagementUnitSerializer
        return ManagementUnitSerializer


class UserRoleViewSet(viewsets.ModelViewSet):
    queryset = UserRoleV2.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:user_role:list'
    pagination_class = None
    filterset_fields = ['user_id', 'role_code', 'system_code']

    def get_serializer_class(self):
        from .serializers_permission_v2 import UserRoleSerializer
        return UserRoleSerializer

    @action(detail=False, methods=['get'])
    def suggest_scope(self, request):
        """GET /user-roles/suggest-scope/?user_id=X&role_code=Y"""
        user_id = request.query_params.get('user_id')
        role_code = request.query_params.get('role_code')
        if not (user_id and role_code):
            return Response({'success': False, 'message': 'user_id + role_code 必填'},
                            status=http_status.HTTP_400_BAD_REQUEST)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response({'success': False, 'message': 'user 不存在'},
                            status=http_status.HTTP_404_NOT_FOUND)
        try:
            scope = resolve_scope(user)
        except (OperationalError, ProgrammingError):
            scope = {}
        if scope.get('all'):
            return Response({
                'suggested_unit_ids': [],
                'derived_from': 'L2',
                'rationale': '角色 default=ALL, 不需要管理单元',
            })
        # 简化: 返回所有 unit 让 admin 选
        try:
            units = ManagementUnit.objects.filter(status=1).values('id', 'org_scope', 'unit_name')
        except (OperationalError, ProgrammingError):
            units = []
        return Response({
            'suggested_unit_ids': [u['id'] for u in units],
            'derived_from': 'L4',
            'rationale': '兜底: 返回所有可用管理单元',
        })