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