"""数据权限规则 (统一行级 + 列级, 按 角色/部门/用户 维度)

新增数据权限管理功能 (RBAC 复核 #9 核心缺口补全):
- 现有 FieldACL 仅覆盖「按角色」的列级;
- 现有 scope_resolver 仅覆盖「按角色默认 + 用户管理单元」的行级;
- 二者互相独立、无统一抽象、无按「部门/用户」维度的规则入口、无配置 UI。
本模型把行级 + 列级收敛到单一规则抽象, 维度覆盖 ROLE/DEPARTMENT/USER。

 enforcement 不在本模块内: scope_resolver / FieldAclService 后续按需消费本表;
 本模块只负责「规则的可视化配置与存储」(管理面)。

2026-10-11 新增 DataPermTemplate(权限模板):
- 解决「同一条可见范围规则要在多个角色/模块反复重配」的问题;
- 与 MetricTemplate(指标口径模板)的区别: MetricTemplate 描述「指标算成什么」,
  本模型描述「能看到哪些数据」, 二者通过 MetricTemplate.scope_template_refs 弱关联;
- 关键设计: 模板是**起草工具**而非运行时真相源 —— 引用时把模板体快照进
  scope_payload, 因此管理员改模板不会让在用规则静默语义漂移。
  详见 scope_templates.instantiate()。
"""
from django.db import models
from nanoid import generate as nanoid_generate

from apps.common.models import (
    FullAuditModel,
    SoftDeleteManager,
    TimestampedModel,
    UUIDModel,
)


def gen_id():
    return nanoid_generate(size=21)


def _next_template_code() -> str:
    """模板编号 DPT+4 位流水。取号含已软删(all_objects)，
    否则软删 DPT0003 后新建会复用该号, restore 时撞 unique。"""
    import re
    rows = DataPermTemplate.all_objects.values_list('code', flat=True)
    max_seq = 0
    for code in rows:
        m = re.fullmatch(r'DPT(\d{4})', code or '')
        if m:
            max_seq = max(max_seq, int(m.group(1)))
    return f'DPT{max_seq + 1:04d}'


class DimensionType(models.TextChoices):
    ROLE = 'ROLE', '角色'
    DEPARTMENT = 'DEPARTMENT', '部门'
    USER = 'USER', '用户'


class RuleLevel(models.TextChoices):
    ROW = 'ROW', '行级'
    COLUMN = 'COLUMN', '列级'


class RowScopeType(models.TextChoices):
    ALL = 'ALL', '全部数据'
    NONE = 'NONE', '无数据'
    DEPT = 'DEPT', '仅本部门'
    DEPT_AND_SUB = 'DEPT_AND_SUB', '本部门及下属'
    SELF = 'SELF', '仅自己创建'
    OWNER = 'OWNER', '仅负责人'  # M07 写范围: 仅记录负责人(referrer 等 owner 字段)可操作
    CUSTOM = 'CUSTOM', '自定义范围'


class RowScopeAccess(models.TextChoices):
    """行级范围访问类型（M07 读写分离）。

    - READ：读范围（既有行为；存量规则 row_access=NULL 也视为读范围，向后兼容）。
    - WRITE：写范围（仅作用于写入口守卫 ensure_writable / write_scope_q）。
    二者互不干扰：读路径不读此字段（NULL 即读），写路径只认 WRITE。
    """

    READ = 'READ', '读范围'
    WRITE = 'WRITE', '写范围'


class ColumnPermission(models.TextChoices):
    READ = 'READ', '可读'
    MASK = 'MASK', '脱敏'
    NONE = 'NONE', '不可见'


class DataPermissionRule(TimestampedModel):
    """统一数据权限规则。

    - 行级 (level=ROW): 用 scope_type + scope_payload 描述数据可见范围。
    - 列级 (level=COLUMN): 用 entity + field + permission 描述字段可见性。
    - 维度 (dimension_type + dimension_value): ROLE→role_code / DEPARTMENT→department_id / USER→user_id。
    - 叠加语义: 读范围=并集 / 列权限=从严(most_restrictive) / 写动作=从严(未列出即拒绝)。
      2026-10-14 起本模型**不再有 priority 字段** —— 旧字段"大者优先"从未被
      enforcement 读取（唯一写入点硬编码 0），属第二套叠加语义（会误导管理员以为
      能调冲突顺序）。裁决顺序现由 (dimension_type, dimension_value, entity) 唯一定位，
      不需要额外优先级轴。详见 docs/ARCH_数据权限P0止血_系统设计.md §1.1。
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
    # 2026-10-12 M07：读写分离。row_access 区分读/写范围；存量规则为 NULL（视为读范围）。
    # 写路径(write_scope_q/ensure_writable)只认 WRITE；读路径(role_entity_scope_q)忽略此字段，
    # 因此存量读规则行为完全不变（双读兼容的对称设计）。
    row_access = models.CharField(
        max_length=8, choices=RowScopeAccess.choices, null=True, blank=True,
        verbose_name='行级访问类型',
        help_text='NULL/READ=读范围(默认); WRITE=写范围(仅作用于写入口守卫)',
    )
    # 2026-10-13 权限 v2：动作粒度。仅 row_access=WRITE 时有意义：允许的写动作 key 集合
    # （key 见 DataPermissionAction 字典表）；NULL=全部动作放行（双读兼容，同 row_access 设计）。
    # 执行链按「动作级 fail-closed」判定：配置写范围后未列出的动作一律拒绝 ——
    # 见 enforcement.write_scope_q 与 docs/plan-read-write-action-permission.md §3.4。
    actions = models.JSONField(
        null=True, blank=True,
        verbose_name='允许的写动作集合',
        help_text="仅 row_access=WRITE 有效：['edit','transition']；NULL=全部动作放行",
    )

    # 列级字段
    entity = models.CharField(max_length=64, null=True, blank=True, db_index=True, verbose_name='实体')
    field = models.CharField(max_length=64, null=True, blank=True, db_index=True, verbose_name='字段')
    permission = models.CharField(
        max_length=8, choices=ColumnPermission.choices, null=True, blank=True, verbose_name='列级权限',
    )

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # 规则变更 → 清列级缓存 (行级不缓存, 无需处理)
        if self.entity:
            from .enforcement import clear_column_cache
            clear_column_cache(self.entity)

    def delete(self, *args, **kwargs):
        entity = self.entity
        super().delete(*args, **kwargs)
        if entity:
            from .enforcement import clear_column_cache
            clear_column_cache(entity)


class TemplateStatus(models.TextChoices):
    ENABLED = 'ENABLED', '启用'
    DISABLED = 'DISABLED', '停用'


class DataPermTemplate(FullAuditModel, UUIDModel):
    """数据权限模板 —— 可复用的条件组预设，供数据权限规则实例化引用。

    与 MetricTemplate 的边界:
      - MetricTemplate 描述「指标口径」(算成什么)，本模型描述「可见数据范围」(能看到什么);
      - 两者生命周期不同(复用度/版本/失效传播)，故独立建模，
        由 MetricTemplate.scope_template_refs 做「指标模板预置权限模板」的弱关联。

    groups 与 scope_payload.groups 同构: [{expr, conditions:[...]}]，
    条件里可用 ${paramKey} 占位符，实例化时按 params 声明替换。

    重要: 模板是**起草工具**，不是运行时真相源。引用方把模板体快照进自己的
    scope_payload 并记templateRef 标记，因此：
      - 管理员改模板 → 在用规则语义不变（无静默漂移风险）；
      - 模板软删 → 引用方仍按快照正常执行（不失效、不报错）。
    """

    # editable=False: 编号只由 save() 自动补，表单/序列化器写不进来
    code = models.CharField(
        max_length=32, unique=True, blank=True, default='', editable=False,
        verbose_name='模板编号', help_text='系统自动生成（DPT+4 位），不可修改',
    )
    name = models.CharField(max_length=64, verbose_name='模板名称')
    module_key = models.CharField(
        max_length=32, db_index=True, verbose_name='适用模块',
        help_text='业务模块 key：demand/process/position/candidate/talent',
    )
    description = models.CharField(max_length=255, blank=True, default='', verbose_name='说明')

    groups = models.JSONField(
        default=list, blank=True, verbose_name='模板条件组',
        help_text='与 scope_payload.groups 同构的 [{expr, conditions:[...]}]；'
                  '条件中可用 ${paramKey} 占位符',
    )
    params = models.JSONField(
        default=list, blank=True, verbose_name='参数声明',
        help_text='[{key,label,valueType,required,default,enum?}]；'
                  'valueType∈ dept/user/text/number',
    )

    status = models.CharField(
        max_length=16, choices=TemplateStatus.choices,
        default=TemplateStatus.ENABLED, db_index=True, verbose_name='状态',
    )
    version = models.PositiveIntegerField(
        default=1, verbose_name='当前版本号',
        help_text='模板语义变更后 +1；引用方记快照版本，不会自动升级',
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'data_perm_templates'
        verbose_name = '数据权限模板'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return f'{self.code}({self.name})'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = _next_template_code()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# 可配置动作字典（权限 v2，2026-10-13）
#
# 为什么从 ACTION_REGISTRY 代码常量升级为 DB 表：
#   兵哥需求「功能权限要在后续自定义配置，而不是一次性写死」——动作清单本身要可增删改
#   （如后续加「人工群发通知」），不该每加一个动作都改代码发版。
#   ACTION_REGISTRY 降级为「种子定义 + DB 读失败兜底」，见 action_map.sync_seed()。
#
# 护栏（防误操作破坏执行链）：
#   - is_system=True：不可删、key 不可改（业务代码 ensure_writable(action='xxx') 引用它），
#     仅可改 label / 停用；
#   - 自建动作 key 强制 custom_ 前缀（CUSTOM_KEY_PREFIX）；
#   - 被 WRITE 规则 actions 引用的动作不可删（保存时校验，见 action_registry）。
# ---------------------------------------------------------------------------
class ActionCategory(models.TextChoices):
    """动作归类：驱动预设包与 UI 分组。"""
    READ = 'read', '读'
    WRITE = 'write', '写'
    DESTRUCTIVE = 'destructive', '破坏性'


class DataPermissionAction(models.Model):
    """写动作字典条目。

    key 是稳定契约：业务代码 ensure_writable(user, entity, obj, action=key) 引用它，
    因此系统动作的 key 一经发布不可变更（只可改 label / enabled）。
    停用（enabled=False）= 执行时该动作一律拒绝（安全方向，见 write_scope_q）。
    """

    CUSTOM_KEY_PREFIX = 'custom_'

    key = models.CharField(max_length=32, primary_key=True, verbose_name='动作key')
    label = models.CharField(max_length=32, verbose_name='名称')
    category = models.CharField(
        max_length=16, choices=ActionCategory.choices,
        default=ActionCategory.WRITE, verbose_name='归类',
    )
    destructive = models.BooleanField(default=False, verbose_name='破坏性动作')
    enabled = models.BooleanField(default=True, verbose_name='启用')
    is_system = models.BooleanField(default=False, verbose_name='系统内置')
    sort_order = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'data_permission_actions'
        verbose_name = '数据权限动作'
        verbose_name_plural = '数据权限动作'
        ordering = ['sort_order', 'key']

    def __str__(self):
        return f'{self.key}({self.label})'


class DataPermissionActionPreset(models.Model):
    """动作预设包：一组动作 key 的命名组合（如 owner_restricted = 查看+编辑）。

    规则配置 UI 选预设包一键填充 actions，避免动作 × 维度笛卡尔积爆炸；
    预设包本身同样可配置（管理员自建组合）。
    """

    key = models.CharField(max_length=32, primary_key=True, verbose_name='预设key')
    label = models.CharField(max_length=32, verbose_name='名称')
    action_keys = models.JSONField(default=list, verbose_name='动作key集合')
    module = models.CharField(max_length=32, null=True, blank=True, verbose_name='功能模块')
    is_system = models.BooleanField(default=False, verbose_name='系统内置')
    sort_order = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'data_permission_action_presets'
        verbose_name = '数据权限动作预设包'
        verbose_name_plural = '数据权限动作预设包'
        ordering = ['sort_order', 'key']

    def __str__(self):
        return f'{self.key}({self.label})'
