"""Core 序列化器"""
import re
from rest_framework import serializers
from .models import User, Department, Role, Permission, UserRole


_camel_to_snake_re = re.compile(r'(?<!^)(?=[A-Z])')


def _camel_to_snake(name: str) -> str:
    return _camel_to_snake_re.sub('_', name).lower()


def _convert_keys_to_snake(data):
    if isinstance(data, list):
        return [_convert_keys_to_snake(item) for item in data]
    if not isinstance(data, dict):
        return data
    return {_camel_to_snake(k): _convert_keys_to_snake(v) for k, v in data.items()}


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器 - 脱敏字段由 Field ACL 处理

    2026-07-02: 暴露 FE 期望字段:
      realName (→ first_name+last_name), status (→ is_active), roleType (→ UserRole),
      permissionMode (派生, 暂固定 'MOU'),
      wechatWork* / mocha* (派生, 暂返空字符串, FE prompt 输入暂不入库等 V2)
    """
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    # 2026-07-02: FE 表单 input 字段, 写库时由 to_internal_value / update 处理
    username = serializers.CharField(required=False)
    real_name = serializers.CharField(required=False, write_only=True)
    role_type = serializers.CharField(required=False, write_only=True)
    permission_mode = serializers.CharField(required=False, write_only=True)
    wechat_work_user_id = serializers.CharField(required=False, write_only=True)
    wechat_work_dept_id = serializers.CharField(required=False, write_only=True)
    wechat_work_name = serializers.CharField(required=False, write_only=True)
    mocha_dept_id = serializers.CharField(required=False, write_only=True)
    mocha_name = serializers.CharField(required=False, write_only=True)
    status = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name',
            'employee_id', 'phone', 'avatar',
            'full_name', 'email',
            'department', 'department_name',
            'direct_manager',
            'position_title', 'level',
            'bu_president', 'solid_vp', 'dotted_vp',
            'moka_user_id',
            'is_active', 'last_login_at',
            'created_at', 'updated_at',
            # 2026-07-02: FE input 字段 (write_only, 但必须在 fields 中声明)
            'real_name', 'role_type', 'permission_mode',
            'wechat_work_user_id', 'wechat_work_dept_id', 'wechat_work_name',
            'mocha_dept_id', 'mocha_name', 'status',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login_at', 'full_name']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # 2026-07-02: 派生 FE 期望字段
        ret['realName'] = instance.full_name
        if instance.is_active:
            ret['status'] = 'ACTIVE'
        else:
            ret['status'] = 'LOCKED' if instance.is_superuser else 'INACTIVE'
        ur = instance.user_roles.select_related('role').first()
        ret['roleType'] = ur.role.code if ur else 'HR'
        ret['permissionMode'] = 'MOU'
        ret['wechatWorkUserId'] = ''
        ret['wechatWorkDeptId'] = ''
        ret['wechatWorkName'] = ''
        ret['mochaDeptId'] = ''
        ret['mochaName'] = ''
        return ret

    def to_internal_value(self, data):
        converted = _convert_keys_to_snake(data) if isinstance(data, dict) else data
        if not isinstance(converted, dict):
            return super().to_internal_value(converted)

        # 2026-07-02: 字段映射
        # realName (FE 字段) → 拆 first_name / last_name
        if 'real_name' in converted and ('first_name' not in converted and 'last_name' not in converted):
            full = (converted.pop('real_name') or '').strip()
            if full:
                parts = full.split(maxsplit=1)
                converted['first_name'] = parts[0]
                converted['last_name'] = parts[1] if len(parts) > 1 else ''

        # status (FE 字段) → is_active
        if 'status' in converted and 'is_active' not in converted:
            converted['is_active'] = converted.pop('status') == 'ACTIVE'

        # roleType / permissionMode / wechat* / mocha* → consume 即可, _apply_role_type 单独处理 roleType
        converted.pop('permission_mode', None)
        converted.pop('wechat_work_user_id', None)
        converted.pop('wechat_work_dept_id', None)
        converted.pop('wechat_work_name', None)
        converted.pop('mocha_dept_id', None)
        converted.pop('mocha_name', None)
        converted.pop('department_name', None)

        return super().to_internal_value(converted)

    def _apply_role_type(self, instance, validated_data):
        """roleType 写入 UserRole (覆盖式: 先删后建)."""
        new_role_code = validated_data.pop('role_type', None)
        if new_role_code is None:
            return
        try:
            new_role = Role.objects.get(code=new_role_code, is_active=True)
        except Role.DoesNotExist:
            return
        UserRole.objects.filter(user=instance).delete()
        UserRole.objects.create(user=instance, role=new_role, department=None)

    def create(self, validated_data):
        password = validated_data.pop('password', None) or 'Pass@1234'
        user = User.objects.create_user(
            username=validated_data['username'],
            password=password,
            **validated_data,
        )
        self._apply_role_type(user, validated_data)
        return user

    def update(self, instance, validated_data):
        self._apply_role_type(instance, validated_data)
        validated_data.pop('username', None)  # update 时不允许清空 username
        return super().update(instance, validated_data)


class UserMinimalSerializer(serializers.ModelSerializer):
    """精简用户序列化器（用于下拉/搜索）"""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'full_name', 'email', 'phone',
            'employee_id', 'department',
            'moka_user_id', 'is_active', 'created_at',
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # 2026-07-02: 派生 FE 期望字段 (UserManagement.vue 表格用)
        ret['realName'] = instance.full_name
        if instance.is_active:
            ret['status'] = 'ACTIVE'
        else:
            ret['status'] = 'LOCKED' if instance.is_superuser else 'INACTIVE'
        ur = instance.user_roles.select_related('role').first()
        ret['roleType'] = ur.role.code if ur else 'HR'
        ret['permissionMode'] = 'MOU'
        ret['wechatWorkUserId'] = ''
        ret['wechatWorkDeptId'] = ''
        ret['wechatWorkName'] = ''
        ret['mochaDeptId'] = ''
        ret['mochaName'] = ''
        return ret


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
