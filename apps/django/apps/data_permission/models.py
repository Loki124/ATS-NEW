"""数据权限规则 (统一行级 + 列级, 按 角色/部门/用户 维度)

新增数据权限管理功能 (RBAC 复核 #9 核心缺口补全):
- 现有 FieldACL 仅覆盖「按角色」的列级;
- 现有 scope_resolver 仅覆盖「按角色默认 + 用户管理单元」的行级;
- 二者互相独立、无统一抽象、无按「部门/用户」维度的规则入口、无配置 UI。
本模型把行级 + 列级收敛到单一规则抽象, 维度覆盖 ROLE/DEPARTMENT/USER。

 enforcement 不在本模块内: scope_resolver / FieldAclService 后续按需消费本表;
 本模块只负责「规则的可视化配置与存储」(管理面)。
"""
from django.db import models
from apps.common.models import TimestampedModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class DimensionType(models.TextChoices):
    ROLE = 'ROLE', '角色'
    DEPARTMENT = 'DEPARTMENT', '部门'
    USER = 'USER', '用户'


class RuleLevel(models.TextChoices):
    ROW = 'ROW', '行级'
    COLUMN = 'COLUMN', '列级'


class RowScopeType(models.TextChoices):
    ALL = 'ALL', '全部数据'
    DEPT = 'DEPT', '仅本部门'
    DEPT_AND_SUB = 'DEPT_AND_SUB', '本部门及下属'
    SELF = 'SELF', '仅自己创建'
    CUSTOM = 'CUSTOM', '自定义范围'


class ColumnPermission(models.TextChoices):
    READ = 'READ', '可读'
    MASK = 'MASK', '脱敏'
    NONE = 'NONE', '不可见'


class DataPermissionRule(TimestampedModel):
    """统一数据权限规则。

    - 行级 (level=ROW): 用 scope_type + scope_payload 描述数据可见范围。
    - 列级 (level=COLUMN): 用 entity + field + permission 描述字段可见性。
    - 维度 (dimension_type + dimension_value): ROLE→role_code / DEPARTMENT→department_id / USER→user_id。
    - priority: 同一 (维度, 层级) 多条规则冲突时, 大者优先。
    """

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    dimension_type = models.CharField(max_length=16, choices=DimensionType.choices, verbose_name='维度类型')
    dimension_value = models.CharField(
        max_length=64, verbose_name='维度值',
        help_text='ROLE→role_code / DEPARTMENT→department_id / USER→user_id',
    )

    level = models.CharField(max_length=8, choices=RuleLevel.choices, verbose_name='规则层级')

    # 行级字段
    scope_type = models.CharField(
        max_length=16, choices=RowScopeType.choices, null=True, blank=True, verbose_name='行级范围类型',
    )
    scope_payload = models.JSONField(
        null=True, blank=True, verbose_name='行级自定义范围',
        help_text='scope_type=CUSTOM 时生效: {"department_ids":[...]} 或 {"management_unit_ids":[...]}',
    )

    # 列级字段
    entity = models.CharField(max_length=64, null=True, blank=True, db_index=True, verbose_name='实体')
    field = models.CharField(max_length=64, null=True, blank=True, db_index=True, verbose_name='字段')
    permission = models.CharField(
        max_length=8, choices=ColumnPermission.choices, null=True, blank=True, verbose_name='列级权限',
    )

    priority = models.IntegerField(default=0, verbose_name='优先级(大者优先)')
    status = models.SmallIntegerField(default=1, verbose_name='状态(1启用 0停用)')
    remark = models.CharField(max_length=255, null=True, blank=True, verbose_name='备注')
    created_by = models.BigIntegerField(null=True, blank=True, verbose_name='创建人ID')

    class Meta:
        db_table = 'data_permission_rules'
        verbose_name = '数据权限规则'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['dimension_type', 'dimension_value'], name='idx_dp_dim'),
            models.Index(fields=['level'], name='idx_dp_level'),
        ]

    def __str__(self):
        return f'DP[{self.dimension_type}:{self.dimension_value}] {self.level}'
