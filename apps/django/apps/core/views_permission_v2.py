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