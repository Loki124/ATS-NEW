"""V2 权限系统 serializers."""
from django.db.utils import OperationalError, ProgrammingError
from rest_framework import serializers

from .models_permission_v2 import (
    PermissionResource, PermissionTemplate, RoleV2, RolePermissionV2,
    ManagementUnit, UserRoleV2, UserAppDataScope,
)


class PermissionResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermissionResource
        fields = ['id', 'system_code', 'resource_code', 'resource_name', 'resource_type',
                  'parent_code', 'module', 'sort_order', 'status']


class PermissionTemplateSerializer(serializers.ModelSerializer):
    permission_codes = serializers.JSONField()

    class Meta:
        model = PermissionTemplate
        fields = ['id', 'system_code', 'template_code', 'template_name', 'description',
                  'is_system', 'permission_codes', 'status']


class RoleSerializer(serializers.ModelSerializer):
    permission_codes = serializers.SerializerMethodField()

    class Meta:
        model = RoleV2
        fields = ['id', 'system_code', 'role_code', 'role_name', 'template_code',
                  'default_data_scope_type', 'description', 'is_system', 'status',
                  'permission_codes', 'created_at', 'updated_at']

    def get_permission_codes(self, obj):
        try:
            return list(RolePermissionV2.objects.filter(
                role_code=obj.role_code, system_code=obj.system_code
            ).values_list('resource_code', flat=True))
        except (OperationalError, ProgrammingError):
            return []


class ManagementUnitSerializer(serializers.ModelSerializer):
    """方案 A(2026-09-15): 新增 parent_id(树形层级) + personnel_scope(人员范围谓词)."""

    class Meta:
        model = ManagementUnit
        fields = ['id', 'system_code', 'unit_name', 'unit_type', 'parent_id',
                  'org_scope', 'personnel_scope', 'include_children', 'status',
                  'created_at', 'updated_at']

    def validate(self, attrs):
        """方案 A: 校验 parent_id 不指向自身或其后代(防环)."""
        parent_id = attrs.get('parent_id')
        if parent_id is None:
            return attrs
        instance = self.instance
        if instance and parent_id == instance.id:
            raise serializers.ValidationError({'parent_id': '上级管理单元不能指向自身'})
        # 防环: 沿 parent 链向上, 若回到自身 id 则形成环
        if instance:
            seen = set()
            cur = ManagementUnit.objects.filter(id=parent_id).first()
            while cur and cur.id not in seen:
                if cur.id == instance.id:
                    raise serializers.ValidationError(
                        {'parent_id': '上级管理单元不能指向自己的下级节点(会形成环)'})
                seen.add(cur.id)
                cur = ManagementUnit.objects.filter(id=cur.parent_id).first() if cur.parent_id else None
        return attrs


class UserRoleSerializer(serializers.ModelSerializer):
    management_unit_ids = serializers.JSONField(required=False)

    class Meta:
        model = UserRoleV2
        fields = ['id', 'user_id', 'role_code', 'system_code', 'management_unit_ids',
                  'valid_from', 'valid_to', 'granted_by_id', 'granted_at', 'updated_at']

    def create(self, validated_data):
        validated_data['granted_by_id'] = self.context['request'].user.id
        return super().create(validated_data)


class UserAppDataScopeSerializer(serializers.ModelSerializer):
    """方案 A(2026-09-15): 用户-角色-应用 的数据范围(管理单元)绑定.

    对齐北森图12「按应用管理单元」: 同一用户对同一角色, 在不同应用/模块
    (recruit/social/campus/referral...) 可见不同的管理单元集合.
    """

    class Meta:
        model = UserAppDataScope
        fields = ['id', 'user_id', 'role_code', 'system_code', 'app_code',
                  'management_unit_ids', 'granted_by_id', 'granted_at', 'updated_at']
        read_only_fields = ['id', 'granted_at', 'updated_at']