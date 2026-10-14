"""Field ACL Serializers (PRD v4 §4.4)"""
from rest_framework import serializers

from .models import FieldACL, FieldPermission


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
    # TODO(P0-4 过渡):下批删除 —— 旧前端仍消费 action 字段（前端读 permission 缺失时回落）。
    # 新代码一律只用 permission 代码枚举，禁止在前端自建映射表。
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
    # P2-1（2026-10-14）：补权威口径 `permission`（READ/MASK/NONE 代码枚举）。
    # 修复前本序列化器只回旧词汇 `action`（VIEW/MASK/HIDE），而 matrix 端点已回双字段，
    # 造成两处口径不一致：
    #   1. 前端 `FieldAclSettings.vue reload()` 读 `r.permission` 建基线快照恒为
    #      undefined —— 那段是死代码，实际靠 matrix 循环兜底；
    #   2. 往返断裂：GET 回 `action:'HIDE'`，PUT 却拒收 `permission:'HIDE'`
    #      （旧词汇不是合法代码枚举），客户端 GET→改→PUT 必 400。
    # 与 `action` 并存一个批次（action 为 TODO(P0-4 过渡) 字段，下批删）。
    # 注意不能写 `source='permission'`：字段名与模型字段同名时 DRF 的 bind()
    # 会直接 assert 报错（redundant source），路由一注册就 500。
    permission = serializers.CharField(read_only=True)
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
            'id', 'resource', 'field', 'action', 'permission',
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
        """模型无is_active 字段 —— 存在即生效, 故恒为 True。

        前端 matrix 渲染不依赖该字段, 返回常数 True 即可满足契约。
        """
        return True


class FieldACLWriteSerializer(serializers.Serializer):
    """字段 ACL 写入校验（PUT /field-acl/rules）。

    与只读的 FieldAclRuleSerializer **刻意分开**（设计文档 §0.2 D4）：
      - 只读那个为兼容旧前端保留 VIEW/MASK/HIDE 词汇（PERMISSION_TO_ACTION）；
      - 写入这个**只用代码枚举 READ/MASK/NONE**，与 field_acl/models.py 的
        FieldPermission.choices 严格一一对应。
    这样任何时候都不存在「两套词汇同时可选」—— 混用是 P2-7 同款病灶：
    管理员能选出一个后端根本不认的词，保存静默失败或被降级解释。

    ACL 的唯一键是 (entity, field, role_code) 三元组（模型 unique_together），
    没有单条 pk 语义，故不用 ModelSerializer 的默认 create/update，
    存在性判定与 upsert 都在 view 里用 update_or_create 完成。
    """

    permission = serializers.ChoiceField(
        choices=FieldPermission.choices,
        help_text='READ=可读 / MASK=脱敏可见 / NONE=不可见（从严顺序 NONE>MASK>READ）',
    )
    entity = serializers.CharField(max_length=64)
    field = serializers.CharField(max_length=64)
    role_code = serializers.CharField(max_length=50)

    def validate_permission(self, value: str) -> str:
        """三态之外一律拒收，且错误文案要说人话（AGENTS.md R-203 第一段）。"""
        if value not in FieldPermission.values:
            raise serializers.ValidationError('字段可见性只能是「可读 / 脱敏可见 / 不可见」之一')
        return value

    def validate_field(self, value: str) -> str:
        """field 必须与序列化器**输出**的键名一致（apply_acl 只遍历输出键）。

        这里不做实体白名单校验：字段名随各序列化器演进，硬白名单会在新增字段时
        静默拒掉合法配置（这正是 DEFAULT_SENSITIVE_FIELDS 踩过的坑的镜像）。
        真正的兜底是 DEFAULT_SENSITIVE_FIELDS —— 未配规则时按默认脱敏执行。
        """
        return value.strip()

    def validate_role_code(self, value: str) -> str:
        """角色必须真实存在 —— 防止再产生孤儿 ACL 规则。

        FieldACL.role_code 是裸CharField（跨系统串，与 RoleV2 的
        (system_code, role_code) 复合唯一键同款约束，无法建 FK），
        故校验失败必须**响亮**：返回明确 400，禁止静默写入孤儿规则
        （设计文档 §0.3 DR-02 / §6.2「失败必须响亮」）。
        """
        from apps.core.models_permission_v2 import RoleV2
        value = value.strip()
        if not RoleV2.objects.filter(role_code=value).exists():
            raise serializers.ValidationError(f'角色「{value}」不存在，请重新选择')
        return value
