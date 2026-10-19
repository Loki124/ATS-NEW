"""V2 权限系统 serializers."""
from django.db.utils import OperationalError, ProgrammingError
from rest_framework import serializers

from .models_permission_v2 import (
    DynamicStrategy,
    ManagementUnit,
    ManagementUnitMember,
    PermissionResource,
    PermissionTemplate,
    RolePermissionV2,
    RoleV2,
    UserRoleV2,
)


class PermissionResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermissionResource
        fields = ['id', 'system_code', 'resource_code', 'resource_name', 'resource_type',
                  'parent_code', 'module', 'sort_order', 'status', 'strategy_governed']


class PermissionResourceStrategyGovernedSerializer(serializers.ModelSerializer):
    """「受策略管控」开关的最小更新序列化器（2026-10-20）。

    PermissionResourceViewSet 只为这个开关放开 partial_update，其余字段
    （resource_code / resource_name / resource_type / module / status …）
    一律不可写 —— 资源是代码注册的目录，改码即「五处不同步 → 静默失权」
    （见 docs/06-runbook/资源出入规则.md §1 铁律），绝不能开通用 update 口子。
    """

    class Meta:
        model = PermissionResource
        fields = ['id', 'resource_code', 'strategy_governed']
        read_only_fields = ['id', 'resource_code']


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
    """方案 A(2026-09-15): 新增 parent_id(树形层级)."""

    class Meta:
        model = ManagementUnit
        fields = ['id', 'system_code', 'unit_name', 'unit_type', 'parent_id',
                  'code', 'description', 'display_order',
                  'org_scope', 'include_children', 'data_range',
                  'org_scopes', 'data_ranges', 'person_data_range', 'person_data_ranges',
                  'org_scope_enabled', 'person_scope_enabled', 'status',
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


class ManagementUnitMemberSerializer(serializers.ModelSerializer):
    """管理单元成员序列化器 — 含 DEPT/USER/PERSON 名称回填(便于前端展示)."""

    department_name = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = ManagementUnitMember
        fields = ['id', 'unit', 'member_type', 'department_id', 'user_id', 'person_id',
                  'app_code', 'include_children', 'remark', 'status', 'created_at', 'updated_at',
                  'department_name', 'user_name', 'person_name']
        extra_kwargs = {
            'id': {'read_only': True},
            'unit': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }

    def get_department_name(self, obj):
        if obj.member_type == 'DEPT' and obj.department_id:
            from apps.core.models import Department
            return Department.objects.filter(id=obj.department_id).values_list('name', flat=True).first() or ''
        return ''

    def get_user_name(self, obj):
        if obj.member_type == 'USER' and obj.user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            # 注意: values_list 多字段时不能用 flat=True (会抛 TypeError);
            # 取 (username, first_name) 元组, 优先返回 first_name.
            u = User.objects.filter(pk=obj.user_id).values_list('username', 'first_name').first()
            return (u[1] or u[0]) if u else ''
        return ''

    def get_person_name(self, obj):
        if obj.member_type == 'PERSON' and obj.person_id:
            try:
                from apps.campus_control.models import Person
                return Person.objects.filter(pk=obj.person_id).values_list('name', flat=True).first() or ''
            except (OperationalError, ProgrammingError, ValueError):  # V2 Person 字段缺失/person_id 无效返空串, 序列化不应 500
                return ''
        return ''


class UserRoleSerializer(serializers.ModelSerializer):
    # 2026-10-14 P0-3 (R3): 模型 user_id 已改为 FK(core.User, db_column='user_id')。
    # DRF 会把 `user_id` 自动识别为只读(因它不是模型字段名, 只是 FK 的 db_column)，
    # 导致客户端传的 user_id 被丢弃、validated_data 里拿不到、授权落到「用户不存在」。
    # 显式声明为可写 IntegerField：写入时走 FK 的 user_id attname 落到 DB，
    # 读取时输出 user_id 值，维持原 API 契约不变。
    user_id = serializers.IntegerField()
    management_unit_ids = serializers.JSONField(required=False)

    class Meta:
        model = UserRoleV2
        fields = ['id', 'user_id', 'role_code', 'system_code', 'management_unit_ids',
                  'valid_from', 'valid_to', 'granted_by_id', 'granted_at', 'updated_at']

    # 2026-10-08: 特权角色只能由「真正的」Django 超级管理员授予。
    #   不能用 role_v2_query.is_super_admin() 判断 —— 它对持 SUPER_ADMIN **角色**的人
    #   也返回 True, 那正是要防止扩散的对象: 否则任一 SUPER_ADMIN 角色持有者都能
    #   再授一个出去, 特权无限复制且无从收敛。这里只认 Django is_superuser 标志。
    PRIVILEGED_ROLE_CODES = frozenset({'SUPER_ADMIN'})

    def validate_role_code(self, value):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        # 防线 B（既有）：SUPER_ADMIN 只能由真正的 Django 超级管理员授予
        if value in self.PRIVILEGED_ROLE_CODES and not getattr(user, 'is_superuser', False):
            raise serializers.ValidationError(
                f'只有 Django 超级管理员可以授予 {value} 角色。'
            )
        # DR-02 强制（P0-3 验收③）：role_code 必须真实存在于 RoleV2，否则响亮 400。
        # 禁止静默写脏 / 降级 warning / 写入后补占位角色 —— 这正是 P0-3 要消灭的病灶形态。
        # role_code 侧因技术限制只有应用层校验（登记为残余风险 RK-13）。
        from apps.core.models_permission_v2 import RoleV2
        system_code = (
            self.instance.system_code
            if self.instance
            else self.initial_data.get('system_code', 'recruit')
        )
        if not RoleV2.objects.filter(
            role_code=value, system_code=system_code
        ).exists():
            raise serializers.ValidationError(
                {'role_code': f'角色「{value}」不存在，请先创建角色或从下拉中重新选择'}
            )
        return value

    def validate(self, attrs):
        """P0-3 验收③：新建/更新授权时校验 user 真实存在且未停用（不静默成功）。

        刻意与应用层 role_code 校验组成「双层防护」：user 侧最终由 0024 的 FK 兜底，
        role_code 侧因技术限制只有应用层（登记为残余风险 RK-13）。
        """
        from django.contrib.auth import get_user_model

        user_id = attrs.get('user_id')
        # 更新且未改 user_id：保持原关联，跳过 user 存在性校验
        if user_id is None and self.instance is not None:
            return attrs

        User = get_user_model()
        user_obj = User.objects.filter(pk=user_id).first()
        if user_obj is None:
            raise serializers.ValidationError(
                {'user_id': '所选用户不存在，请刷新后重试'}
            )
        if not user_obj.is_active:
            raise serializers.ValidationError(
                {'user_id': f'用户「{user_obj.username}」已停用，无法授予角色'}
            )
        return attrs

    def create(self, validated_data):
        validated_data['granted_by_id'] = self.context['request'].user.id
        return super().create(validated_data)


class DynamicStrategySerializer(serializers.ModelSerializer):
    """动态策略序列化器 (2026-10-19 起不绑定角色, 策略全局生效)."""

    class Meta:
        model = DynamicStrategy
        fields = [
            'id', 'system_code', 'strategy_code', 'strategy_name', 'status',
            'description', 'governed_functions', 'granted_resource_codes',
            'module_config', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        gf = attrs.get('governed_functions') or []
        invalid_modules = [m for m in gf if m not in DynamicStrategy.VALID_MODULE_KEYS]
        if invalid_modules:
            raise serializers.ValidationError({
                'governed_functions': f'非法模块: {invalid_modules}',
            })
        mc = attrs.get('module_config') or {}
        for module_key, cfg in mc.items():
            if module_key not in DynamicStrategy.VALID_MODULE_KEYS:
                raise serializers.ValidationError({
                    'module_config': f'非法模块键: {module_key}',
                })
            mode = (cfg or {}).get('mode')
            if mode is not None and mode not in DynamicStrategy.VALID_MODES:
                raise serializers.ValidationError({
                    'module_config': f'模块 {module_key} 非法 mode: {mode}',
                })
        return attrs


class UserAppDataScopeSerializer(serializers.Serializer):
    """合成序列化器: 原 UserAppDataScope 表已合并进 UserRoleV2.app_data_scopes(JSON).

    此处仅用于保持 /api/v1/user-app-data-scopes/ 的响应契约(字段名沿用旧表),
    序列化输入为合成的 dict(由 views_permission_v2._build_app_scope_rows 组装),
    CamelCase 渲染层会将其转为前端消费的 camelCase 键.
    """

    id = serializers.CharField(read_only=True)
    user_id = serializers.IntegerField()
    role_code = serializers.CharField()
    system_code = serializers.CharField(default='recruit')
    app_code = serializers.CharField()
    management_unit_ids = serializers.JSONField(required=False, allow_null=True)
    granted_by_id = serializers.IntegerField(required=False, allow_null=True)
    granted_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)