"""Field ACL Serializers (PRD v4 §4.4)"""
from rest_framework import serializers

from .models import FieldACL


class FieldACLSerializer(serializers.ModelSerializer):
    permission_display = serializers.CharField(source='get_permission_display', read_only=True)

    class Meta:
        model = FieldACL
        fields = [
            'id', 'entity', 'field', 'role_code',
            'permission', 'permission_display',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


#: 模型 permission (READ/MASK/NONE) → 前端 FieldAclAction (VIEW/MASK/HIDE) 的翻译表。
#: 只在 API 序列化层做映射, 模型与 FieldAclService 的脱敏语义保持不变。
PERMISSION_TO_ACTION = {
    'READ': 'VIEW',
    'MASK': 'MASK',
    'NONE': 'HIDE',
}


def permission_to_action(permission: str) -> str:
    """把模型 permission 值翻译为前端 FieldAclAction。

    Args:
        permission: FieldPermission 取值之一 (READ / MASK / NONE)。

    Returns:
        前端契约的 action 字符串; 未知取值降级为最严格的 'HIDE'。
    """
    return PERMISSION_TO_ACTION.get(permission, 'HIDE')


class FieldAclRuleSerializer(serializers.ModelSerializer):
    """只读序列化器: 把 FieldACL 翻译为前端 `FieldAclRule` 契约。

    前端 (web/app/src/api/field-acl.ts) 使用 resource / action / roleCode 命名,
    后端模型使用 entity / permission / role_code。此处只做 API 层翻译,
    不改动模型字段, 避免影响生产脱敏引擎 FieldAclService。
    """

    resource = serializers.CharField(source='entity', read_only=True)
    field = serializers.CharField(read_only=True)
    action = serializers.SerializerMethodField()
    roleCode = serializers.CharField(source='role_code', read_only=True)
    roleId = serializers.SerializerMethodField()
    maskPattern = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    isActive = serializers.SerializerMethodField()
    # 显式指定 iso-8601: 项目全局 DATETIME_FORMAT 被改成了 '%Y-%m-%d %H:%M:%S'(无时区),
    # 而前端契约要求 ISO 字符串(可直接喂给 new Date()), 故在此覆盖。
    createdAt = serializers.DateTimeField(source='created_at', format='iso-8601', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', format='iso-8601', read_only=True)

    class Meta:
        model = FieldACL
        fields = [
            'id', 'resource', 'field', 'action',
            'roleId', 'roleCode', 'maskPattern',
            'priority', 'description', 'isActive',
            'createdAt', 'updatedAt',
        ]
        read_only_fields = fields

    def get_action(self, obj: FieldACL) -> str:
        """READ→VIEW / MASK→MASK / NONE→HIDE。"""
        return permission_to_action(obj.permission)

    def get_roleId(self, obj: FieldACL) -> None:
        """模型只存 role_code 字符串, 没有角色外键, 故恒为 None (前端该字段可选)。"""
        return None

    def get_maskPattern(self, obj: FieldACL) -> None:
        """模型未存储脱敏模板, 脱敏规则由 FieldAclService 内置, 故恒为 None。"""
        return None

    def get_priority(self, obj: FieldACL) -> int:
        """模型无优先级字段 (unique_together 保证唯一规则), 前端未使用, 恒为 0。"""
        return 0

    def get_description(self, obj: FieldACL) -> None:
        """模型无描述字段, 恒为 None。"""
        return None

    def get_isActive(self, obj: FieldACL) -> bool:
        """模型无 is_active 字段 —— 存在即生效, 故恒为 True。

        前端 matrix 渲染不依赖该字段, 返回常数 True 即可满足契约。
        """
        return True
