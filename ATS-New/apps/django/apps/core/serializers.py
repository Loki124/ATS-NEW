"""Core 序列化器"""
from rest_framework import serializers
from .models import User, Department, Role, Permission


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器 - 脱敏字段由 Field ACL 处理"""
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'employee_id', 'phone', 'avatar',
            'full_name', 'email',
            'department', 'department_name',
            'direct_manager',
            'position_title', 'level',
            'bu_president', 'solid_vp', 'dotted_vp',
            'moka_user_id',
            'is_active', 'last_login_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login_at', 'full_name']


class UserMinimalSerializer(serializers.ModelSerializer):
    """精简用户序列化器（用于下拉/搜索）"""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'employee_id', 'department']


class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    leader_name = serializers.CharField(source='leader.full_name', read_only=True)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'parent', 'parent_name', 'path', 'sort_order',
            'leader', 'leader_name', 'is_active', 'children_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'path', 'created_at', 'updated_at', 'children_count']

    def get_children_count(self, obj):
        return obj.children.count()


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'description', 'is_builtin', 'is_active', 'created_at']


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'code', 'name', 'module', 'description']
