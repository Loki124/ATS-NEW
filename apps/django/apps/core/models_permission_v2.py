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
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    status = models.SmallIntegerField(default=1, verbose_name='状态(1启用 0禁用)')
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
    role_code = models.CharField(max_length=64, verbose_name='角色编码')
    resource_code = models.CharField(max_length=128, verbose_name='资源编码')
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

    字段差异:
    - role_code 字符串(替代 FK,跨系统灵活)
    - management_unit_ids JSON(数据权限范围)
    - valid_from / valid_to(角色有效期)
    - granted_by_id + granted_at(审计字段)
    """
    user_id = models.BigIntegerField(verbose_name='用户ID')
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
            models.UniqueConstraint(fields=['user_id', 'role_code'], name='uk_user_role'),
        ]
        indexes = [
            models.Index(fields=['user_id'], name='idx_user_id'),
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