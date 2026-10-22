"""Permission V2 Models (T2)

V2 权限系统 7 张新表 (spec §3.2):
- PermissionResource: 资源表(替代 V1 Permission)
- PermissionTemplate: 权限模板
- RoleV2: V2 角色(替代 V1 Role,**无 parent_role_id**)
- RolePermissionV2: 角色-资源关联
- ManagementUnit: 管理单元(数据权限范围)
- UserRoleV2: V2 用户-角色关联(用 code 串替代 FK,以支持跨系统)
- TenantConfig: 租户级配置

注意:
- 本文件与 apps.core.models(V1)并存,V1 模型在 T17 drop_old 阶段前不删除
- RoleV2/RolePermissionV2/UserRoleV2 加 V2 后缀,因为 Django 按 (app_label, model_name)
  注册,V1 已有 Role/RolePermission/UserRole 同名类,会注册冲突
- 序列化器/视图必须从 `apps.core.models_permission_v2` 显式 import V2 类
- 表名严格遵循 spec DDL,不重命名
"""
from django.db import models
from nanoid import generate as nanoid_generate


def gen_id():
    """生成 nanoid 主键 (size=21), 与 data_permission.models.gen_id 口径一致."""
    return nanoid_generate(size=21)


class PermissionResource(models.Model):
    """资源表 — 菜单/按钮/字段/API 的统一注册(MENU | BUTTON | FIELD | API)"""
    system_code = models.CharField(max_length=32, default='recruit', verbose_name='系统编码')
    resource_code = models.CharField(max_length=128, unique=True, verbose_name='资源编码')
    resource_name = models.CharField(max_length=64, verbose_name='资源名称')
    RESOURCE_TYPE_CHOICES = [
        ('MENU', '菜单'),
        ('BUTTON', '按钮'),
        ('FIELD', '字段'),
        ('API', 'API'),
    ]
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES, verbose_name='资源类型')
    parent_code = models.CharField(max_length=128, null=True, blank=True, verbose_name='父资源编码')
    module = models.CharField(max_length=32, null=True, blank=True, verbose_name='模块')
    # 子模块展示名（2026-10-21）：settings 等模块的子模块可由资源码结构推导
    # （五段码第 4 段为 menu，前端 buildSubModuleIndex），但 candidate 这类四段码
    # （recruit:candidate:create）无子模块段亦无 menu 锚点，推导恒为「—」。
    # 本字段显式登记展示名（如「基础功能 / offer管理」），前端优先显示、空则回退推导。
    # 置位同 strategy_governed 双路径模式：数据迁移（core.0046）+ seed 兜底
    # （RESOURCE_SUB_MODULES），不进 RESOURCES 四元组（护栏测试按 4 元解包，改结构会连带破坏）。
    sub_module = models.CharField(max_length=64, null=True, blank=True, verbose_name='子模块')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    status = models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')
    # 受策略管控(2026-10-20): 标记为「是」的资源才会出现在动态策略的「受限功能」候选区。
    # 缺省 False —— 未登记的资源不进入策略管辖面, 保证「不配置 = 不受限」的安全默认。
    # 置位走数据迁移(见 core.0040), 不进 seed_v2_init.RESOURCES 四元组:
    #   seed 无条件 update_or_create 会覆盖, 且护栏测试按 4 元解包, 改结构会连带破坏。
    strategy_governed = models.BooleanField(default=False, verbose_name='受策略管控')
    ext_fields = models.JSONField(null=True, blank=True, verbose_name='扩展字段')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'permission_resources'
        verbose_name = '权限资源'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['system_code', 'module'], name='idx_system_module'),
        ]

    def __str__(self):
        return f'{self.resource_code}({self.resource_name})'


class PermissionTemplate(models.Model):
    """权限模板 — 一组权限码的集合(用于快速复制到角色)"""
    system_code = models.CharField(max_length=32, default='recruit', verbose_name='系统编码')
    template_code = models.CharField(max_length=64, unique=True, verbose_name='模板编码')
    template_name = models.CharField(max_length=64, verbose_name='模板名称')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='描述')
    is_system = models.SmallIntegerField(default=1, verbose_name='是否系统预置(1是 0否)')
    permission_codes = models.JSONField(default=list, verbose_name='权限码列表(JSON 数组)')
    status = models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'permission_templates'
        verbose_name = '权限模板'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.template_code}({self.template_name})'


class RoleV2(models.Model):
    """V2 角色表 — 替代 V1 roles 表

    spec §3.2 明确:
    - 无 parent_role_id(扁平结构,通过 template_code 复用模板)
    - template_code 是模板的逻辑引用,运行时校验
    - default_data_scope_type 用于数据权限默认范围
    """
    system_code = models.CharField(max_length=32, default='recruit', verbose_name='系统编码')
    role_code = models.CharField(max_length=64, verbose_name='角色编码')
    role_name = models.CharField(max_length=64, verbose_name='角色名称')
    template_code = models.CharField(max_length=64, null=True, blank=True, verbose_name='模板编码')
    default_data_scope_type = models.CharField(max_length=32, null=True, blank=True, verbose_name='默认数据权限范围类型')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='描述')
    is_system = models.SmallIntegerField(default=0, verbose_name='是否系统预置(1是 0否)')
    status = models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'roles'
        verbose_name = '角色(V2)'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=['system_code', 'role_code'], name='uk_system_role'),
        ]

    def __str__(self):
        return f'{self.role_code}({self.role_name})'


class RolePermissionV2(models.Model):
    """V2 角色-资源关联 — 替代 V1 role_permissions

    使用 resource_code 字符串而非 FK(spec §3.2 跨系统复用)
    """
    role_code = models.CharField(max_length=64, verbose_name='角色编码', db_index=True)
    resource_code = models.CharField(max_length=128, verbose_name='资源编码', db_index=True)
    system_code = models.CharField(max_length=32, verbose_name='系统编码')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'role_permission'
        verbose_name = '角色资源关联(V2)'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=['role_code', 'resource_code'], name='uk_role_resource'),
        ]

    def __str__(self):
        return f'{self.role_code} -> {self.resource_code}'


class ManagementUnit(models.Model):
    """管理单元 — 数据权限范围的载体(组织维度)

    方案 A(2026-09-15) 增强:
    - parent_id: 树形层级(集团/子公司/部门), 北森「上级管理单元」对齐
    """
    system_code = models.CharField(max_length=32, default='recruit', verbose_name='系统编码')
    unit_name = models.CharField(max_length=64, verbose_name='管理单元名称')
    unit_type = models.CharField(max_length=20, default='org', verbose_name='单元类型')
    parent_id = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name='上级管理单元ID')
    code = models.CharField(max_length=64, null=True, blank=True, db_index=True, verbose_name='编码')
    description = models.TextField(null=True, blank=True, verbose_name='说明')
    display_order = models.IntegerField(default=0, db_index=True, verbose_name='显示顺序')
    org_scope = models.JSONField(null=True, blank=True, verbose_name='组织范围(JSON)')
    include_children = models.SmallIntegerField(default=1, verbose_name='是否包含子级(1是 0否)')
    data_range = models.JSONField(null=True, blank=True, verbose_name='数据范围(JSON)')
    org_scopes = models.JSONField(null=True, blank=True, verbose_name='按应用组织范围(JSON){app_code: OrgScopeNode[]}')
    data_ranges = models.JSONField(null=True, blank=True, verbose_name='按应用数据范围(JSON){app_code: DataRange}')
    person_data_range = models.JSONField(null=True, blank=True, verbose_name='人员数据范围(JSON)')
    person_data_ranges = models.JSONField(null=True, blank=True, verbose_name='按应用人员数据范围(JSON){app_code: DataRange}')
    org_scope_enabled = models.JSONField(null=True, blank=True, verbose_name='按应用组织范围启用(JSON){app_code: bool}')
    person_scope_enabled = models.JSONField(null=True, blank=True, verbose_name='按应用人员范围启用(JSON){app_code: bool}')
    status = models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'management_units'
        verbose_name = '管理单元'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['parent_id'], name='idx_mgmt_unit_parent'),
        ]

    def __str__(self):
        return self.unit_name


class ManagementUnitMember(models.Model):
    """管理单元成员 — 虚拟容器的真实关系 (2026-09-16 重构).

    成员类型: DEPT=实体组织架构节点(Department.id) / USER=系统用户(User.id) /
    PERSON=HR台账人员(Person.id).
    支持矩阵管理: 同一部门多负责人各管不同人员 / 跨单元交叉管理.
    PERSON 本迭代仅存储展示, 执行面生效待补 Person->User 映射.
    """
    MEMBER_TYPE_CHOICES = [
        ('DEPT', '组织节点'),
        ('USER', '系统用户'),
        ('PERSON', 'HR台账人员'),
    ]
    id = models.CharField(max_length=32, primary_key=True, default=gen_id, editable=False)
    unit = models.ForeignKey(ManagementUnit, on_delete=models.CASCADE, related_name='members', verbose_name='管理单元')
    member_type = models.CharField(max_length=12, choices=MEMBER_TYPE_CHOICES, verbose_name='成员类型')
    department_id = models.CharField(max_length=32, null=True, blank=True, db_index=True, verbose_name='组织节点ID')
    user_id = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name='用户ID')
    person_id = models.CharField(max_length=36, null=True, blank=True, db_index=True, verbose_name='HR台账人员ID')
    app_code = models.CharField(max_length=32, null=True, blank=True, db_index=True, verbose_name='应用编码(成员所属应用 Tab, null=公共)')
    include_children = models.SmallIntegerField(default=1, verbose_name='含子级(1是 0否)')
    remark = models.CharField(max_length=128, null=True, blank=True, verbose_name='备注')
    status = models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'management_unit_members'
        verbose_name = '管理单元成员'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['unit'], name='idx_mum_unit'),
            models.Index(fields=['department_id'], name='idx_mum_dept'),
            models.Index(fields=['user_id'], name='idx_mum_user'),
        ]

    def __str__(self):
        return f'{self.unit_id}:{self.member_type}:{self.department_id or self.user_id or self.person_id}'


class UserRoleV2(models.Model):
    """V2 用户-角色关联 — 替代 V1 user_roles

    2026-10-14 P0-3 (R3 / C5) 变更:
    - `user_id` 从裸 BigIntegerField 改为真 ForeignKey(core.User, CASCADE)。
      列名保持 `user_id` 不变(db_column='user_id'),Django FK 属性名为 `user`、
      查询列名仍为 `user_id` → 现有 `filter(user_id=...)` / `values_list('user_id')`
      / 序列化器 `'user_id'` 字段 **零改动**。删用户 → 其角色授权自动 CASCADE 清除
      (PRD P0-3 验收②前半句)。
    - `role_code` 仍是字符串:它是**跨系统业务串**(同 role_code 可存在于多 system_code
      角色库),建 FK 会摧毁跨系统能力且 RoleV2 唯一键是复合键、单列不唯一 → 技术上不可建
      FK(ARCH D3 / DR-02 已确认)。孤儿角色防护改由 RoleV2 生命周期钩子
      (signals.py purge_role_grants_on_delete) + serializers.validate_role_code 承担。

    其余字段:
    - management_unit_ids JSON(数据权限范围)
    - valid_from / valid_to(角色有效期)
    - granted_by_id + granted_at(审计字段)
    """
    user = models.ForeignKey(
        'core.User', on_delete=models.CASCADE, db_index=False,
        related_name='user_roles_v2', db_column='user_id', verbose_name='用户',
    )
    role_code = models.CharField(max_length=64, verbose_name='角色编码')
    system_code = models.CharField(max_length=32, default='recruit', verbose_name='系统编码')
    management_unit_ids = models.JSONField(null=True, blank=True, verbose_name='管理单元ID列表(JSON)')
    app_data_scopes = models.JSONField(null=True, blank=True, default=dict, verbose_name='按应用的数据范围')
    valid_from = models.DateField(null=True, blank=True, verbose_name='生效日期')
    valid_to = models.DateField(null=True, blank=True, verbose_name='失效日期')
    granted_by_id = models.BigIntegerField(null=True, blank=True, verbose_name='授权人ID')
    granted_at = models.DateTimeField(auto_now_add=True, verbose_name='授权时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'user_roles'
        verbose_name = '用户角色(V2)'
        verbose_name_plural = verbose_name
        constraints = [
            # 2026-10-14 P0-3 (R3): 字段改名 user_id→user(FK, db_column 仍是 user_id),
            # 约束字段名同步改 user; 物理列仍是 user_id, 约束/索引名不变。
            models.UniqueConstraint(fields=['user', 'role_code'], name='uk_user_role'),
        ]
        indexes = [
            models.Index(fields=['user'], name='idx_user_id'),
        ]

    def __str__(self):
        return f'user={self.user_id} role={self.role_code}'


class TenantConfig(models.Model):
    """租户级配置 — 键值对存储,按 system_code 隔离"""
    system_code = models.CharField(max_length=32, verbose_name='系统编码')
    config_key = models.CharField(max_length=64, verbose_name='配置键')
    config_value = models.JSONField(default=dict, verbose_name='配置值(JSON)')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='描述')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'tenant_configs'
        verbose_name = '租户配置'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=['system_code', 'config_key'], name='uk_system_key'),
        ]

    def __str__(self):
        return f'{self.system_code}.{self.config_key}'


class DynamicStrategy(models.Model):
    """动态策略 — 从「操作权限」(原按 ROLE 配置) 抽离出的可复用策略实体.

    全局生效(2026-10-19 起不绑定角色): 启用中的策略对所有用户生效(超管除外),
    并作用于「受限制的功能」(业务模块).
    - governed_functions: 该策略管辖的业务模块 key 列表
      (demand/process/position/candidate/talent)
    - granted_resource_codes: 该策略授予的功能资源码列表(在管辖模块内选择)
    - module_config: {module_key: {mode, actions, groups, expr}} 各模块写范围配置

    注: 资源码不单独建表(v1 够用), 全部以 JSON 存于本模型.
    """

    VALID_MODULE_KEYS = ['demand', 'process', 'position', 'candidate', 'talent']
    VALID_MODES = ['none', 'all', 'owner', 'scope']

    system_code = models.CharField(max_length=32, default='recruit', verbose_name='系统编码')
    strategy_code = models.CharField(max_length=64, unique=True, verbose_name='策略编码')
    strategy_name = models.CharField(max_length=64, verbose_name='策略名称')
    status = models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='描述')
    governed_functions = models.JSONField(default=list, verbose_name='管辖功能(JSON 数组)')
    granted_resource_codes = models.JSONField(default=list, verbose_name='授予资源码(JSON 数组)')
    module_config = models.JSONField(default=dict, verbose_name='模块配置(JSON)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'dynamic_strategies'
        verbose_name = '动态策略'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.strategy_code}({self.strategy_name})'
