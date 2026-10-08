"""Core 序列化器

T30.175 (V2 cutover follow-up):
- V1 Role/UserRole 表已 DROP.
- UserSerializer.to_representation / UserMinimalSerializer.to_representation 改读 UserRoleV2.role_code.
- UserSerializer._apply_role_type 改写 UserRoleV2 (用 role_code 字符串 + system_code).
"""
import re

from django.db import transaction
from rest_framework import serializers

from .models import Department, User
from .models_permission_v2 import PermissionResource, RoleV2, UserRoleV2  # noqa: F401

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
            'user_type',
            'uuid',
            'is_active', 'last_login_at',
            'created_at', 'updated_at',
            # 2026-07-02: FE input 字段 (write_only, 但必须在 fields 中声明)
            'real_name', 'role_type', 'permission_mode',
            'wechat_work_user_id', 'wechat_work_dept_id', 'wechat_work_name',
            'mocha_dept_id', 'mocha_name', 'status',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login_at', 'full_name', 'uuid']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # 2026-07-02: 派生 FE 期望字段
        ret['realName'] = instance.full_name
        if instance.is_active:
            ret['status'] = 'ACTIVE'
        else:
            ret['status'] = 'LOCKED' if instance.is_superuser else 'INACTIVE'
        ret['roleType'] = (
            UserRoleV2.objects.filter(
                user_id=instance.pk, system_code='recruit',
            ).values_list('role_code', flat=True).first() or 'HR'
        )
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
        """roleType 写入 UserRoleV2 (覆盖式: 先删后建).

        2026-07-13: 整段包 transaction.atomic() 修复 TOCTOU race —
        delete + create 之间并发请求可能让用户出现 0 角色或重复角色.
        V2 表无 FK, 单行 delete/create 也用 atomic 保证 all-or-nothing.
        """
        new_role_code = validated_data.pop('role_type', None)
        if new_role_code is None:
            return
        # V2 schema: 校验 role_code 存在于 RoleV2 且启用
        if not RoleV2.objects.filter(role_code=new_role_code, status=1).exists():
            return
        with transaction.atomic():
            UserRoleV2.objects.filter(
                user_id=instance.pk, system_code='recruit',
            ).delete()
            UserRoleV2.objects.create(
                user_id=instance.pk,
                role_code=new_role_code,
                system_code='recruit',
                granted_by_id=self.context['request'].user.id,
            )

    def create(self, validated_data):
        password = validated_data.pop('password', None) or 'Pass@1234'
        # 2026-09-19: username 已在 fields 中, 必须从 validated_data 取出再显式传入,
        # 否则 **validated_data 重复传入 username -> create_user() 报 multiple values
        username = validated_data.pop('username')
        role_type = validated_data.pop('role_type', None)
        status = validated_data.pop('status', None)
        # 2026-09-19: 剥离 FE 写入辅助字段(非 User 模型字段), 否则 create_user 报 unexpected keyword
        for _h in ('real_name', 'permission_mode',
                   'wechat_work_user_id', 'wechat_work_dept_id', 'wechat_work_name',
                   'mocha_dept_id', 'mocha_name'):
            validated_data.pop(_h, None)
        if status is not None:
            validated_data['is_active'] = (status == 'ACTIVE')
        user = User.objects.create_user(
            username=username,
            password=password,
            **validated_data,
        )
        if role_type is not None:
            self._apply_role_type(user, {'role_type': role_type})
        return user

    def update(self, instance, validated_data):
        role_type = validated_data.pop('role_type', None)
        status = validated_data.pop('status', None)
        for _h in ('real_name', 'permission_mode',
                   'wechat_work_user_id', 'wechat_work_dept_id', 'wechat_work_name',
                   'mocha_dept_id', 'mocha_name'):
            validated_data.pop(_h, None)
        if status is not None:
            validated_data['is_active'] = (status == 'ACTIVE')
        if role_type is not None:
            self._apply_role_type(instance, {'role_type': role_type})
        # 2026-09-20: 放开用户名编辑（用户管理页要求「用户名开放编辑」）。
        # username 已在 fields 中且非 read_only，super().update 会直接写入；
        # 唯一性由模型 unique=True 约束保证，重复时报 400 由 DRF 透出。
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
        role_map = self.context.get('role_map')
        if role_map is not None:
            # #9 (2026-10-09): 列表场景由 get_serializer_context 批量注入, 免逐行查询
            ret['roleType'] = role_map.get(instance.pk, 'HR')
        else:
            ret['roleType'] = (
                UserRoleV2.objects.filter(
                    user_id=instance.pk, system_code='recruit',
                ).values_list('role_code', flat=True).first() or 'HR'
            )
        # 2026-09-19: 用户类型字段接入列表 (前端「用户类型」列 + 客户端筛选依赖此字段)
        ret['userType'] = instance.user_type
        # 用户唯一标识（对外稳定 ID，新建自动生成、存量已回填）
        ret['uuid'] = str(instance.uuid) if instance.uuid else ''
        ret['permissionMode'] = 'MOU'
        ret['wechatWorkUserId'] = ''
        ret['wechatWorkDeptId'] = ''
        ret['wechatWorkName'] = ''
        ret['mochaDeptId'] = ''
        ret['mochaName'] = ''
        return ret


class DepartmentSerializer(serializers.ModelSerializer):
    # 显式声明 parent_id（source=parent）：camel-case 包对无下划线的 'parent'
    # 不做转换（输出仍是 'parent'，FE 读 parentId 恒空 -> 树形失效）；
    # FE 发 parentId 经 parser 转 parent_id，只有显式声明才能写入（此前被静默忽略）。
    parent_id = serializers.PrimaryKeyRelatedField(
        source='parent', queryset=Department.objects.all(), required=False, allow_null=True,
    )
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    # 与 FE 字段名对齐: managerId / manager2Id / manager3Id / hrbpId
    # djangorestframework-camel-case 将 camelCase 中的数字边界也视为分词点：
    # manager2Id -> manager_2_id, manager3Id -> manager_3_id
    manager_id = serializers.PrimaryKeyRelatedField(
        source='leader', queryset=User.objects.all(), required=False, allow_null=True,
    )
    manager_2_id = serializers.PrimaryKeyRelatedField(
        source='manager_2', queryset=User.objects.all(), required=False, allow_null=True,
    )
    manager_3_id = serializers.PrimaryKeyRelatedField(
        source='manager_3', queryset=User.objects.all(), required=False, allow_null=True,
    )
    hrbp_id = serializers.PrimaryKeyRelatedField(
        source='hrbp', queryset=User.objects.all(), required=False, allow_null=True,
    )
    children_count = serializers.SerializerMethodField()

    # FE 习惯字段名：status 字符串 <-> is_active
    # 用 SerializerMethodField 在读取时由 is_active 反推 'ACTIVE'/'INACTIVE' 输出，
    # 写入时由 to_internal_value 从原始 data 读 status 映射到 is_active。
    # （此前 status 为 write_only，GET 永不回传 -> 前端状态列恒空/恒启用，已修复）
    status = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'parent_id', 'parent_name', 'path', 'sort_order',
            'manager_id', 'manager_2_id', 'manager_3_id', 'hrbp_id',
            'is_active', 'status', 'children_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'code', 'path', 'created_at', 'updated_at', 'children_count']

    def get_status(self, obj):
        return 'ACTIVE' if obj.is_active else 'INACTIVE'

    def get_children_count(self, obj):
        return obj.children.count()

    def to_internal_value(self, data):
        # SerializerMethodField 不在 super().to_internal_value 处理范围内，
        # 故从原始 data 读取 FE 发来的 status='ACTIVE'/'INACTIVE' -> is_active
        raw_status = data.get('status') if isinstance(data, dict) else None
        converted = super().to_internal_value(data)
        if raw_status is not None:
            converted['is_active'] = raw_status == 'ACTIVE'
        return converted


class RoleSerializer(serializers.ModelSerializer):
    """V2 RoleSerializer — 替代 V1 Role 模型.

    T30.175: V1 Role 表已 DROP. 输出 V2 role_code/role_name. 兼容老字段名 'code'/'name'
    让前端老字段名 (RoleManagement.vue 等) 仍可读.
    """
    code = serializers.CharField(source='role_code', read_only=True)
    name = serializers.CharField(source='role_name', read_only=True)
    is_builtin = serializers.BooleanField(source='is_system', read_only=True)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = RoleV2
        fields = ['id', 'code', 'name', 'description', 'is_builtin', 'is_active', 'created_at']

    def get_is_active(self, obj):
        return obj.status == 1


class PermissionSerializer(serializers.ModelSerializer):
    """V2 PermissionSerializer — 替代 V1 Permission 模型.

    T30.175: V1 permissions 表已 DROP. 改读 V2 PermissionResource.
    """
    code = serializers.CharField(source='resource_code', read_only=True)
    name = serializers.CharField(source='resource_name', read_only=True)

    class Meta:
        model = PermissionResource
        fields = ['id', 'code', 'name', 'module', 'description']
