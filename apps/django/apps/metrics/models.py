"""指标库 —— 规则引擎的「指标层」（2026-09-25 方案 A）。

定位：本 app 是 ATS-NEW 既有统一规则引擎（apps/rule_engine）的**指标元数据与取值层**，
不新建第三套规则系统。规则主体（Rule/Condition/Action）、运算符（UnifiedOperator）、
执行日志（RuleExecutionLog）全部复用 apps.rule_engine，本 app 只补齐它缺失的两块：

    1. 原子指标 AtomicMetric —— 字段级元数据 + 取值路径（source_path）
    2. 派生指标 DerivedMetric —— 计算结果型指标（遍历/聚合/时间窗），内置函数注册表

为什么必须分两层（设计要点）：
    现有 rule_engine.services._resolve_value 仅支持 flat key（getattr / extra.get），
    既无点路径也无数组索引；而业务上真正高频调整的恰恰是「最大空窗期」「近 N 年跳槽
    段数」「最高学历」这类**计算型**规则。若只做原子层，运营新增指标仍需开发介入，
    「无需频繁开发」无法成立。故本模型把指标显式分为取值型与计算型。

运算符白名单复用 rule_engine.UnifiedOperator（11 种，含 BETWEEN/IN/IS_EMPTY），
BETWEEN 的 min/max 借助 Condition.meta_json 承载（复用既有约定，不新增字段）。
"""
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import FullAuditModel, UUIDModel
from apps.rule_engine.models import UnifiedOperator

from .services.rule_validators import validate_metric_rule


class MetricDataType(models.TextChoices):
    """指标数据类型。在 PRD 的 number/string/boolean 之上补 date，
    否则「期望到岗日期早于 X」这类规则无法表达。"""
    NUMBER = 'number', '数值'
    STRING = 'string', '字符串'
    BOOLEAN = 'boolean', '布尔'
    DATE = 'date', '日期'


class MetricStatus(models.TextChoices):
    ENABLED = 'enabled', '启用'
    DISABLED = 'disabled', '停用'


class AtomicMetric(FullAuditModel, UUIDModel):
    """原子指标 —— 直接取值型（source_path 点路径，支持数组索引）。

    例：name=年龄, source_path=candidate.age, data_type=number, unit=岁
    例：name=最近公司, source_path=candidate.workExperience.0.company, data_type=string
    """
    name = models.CharField(max_length=64, unique=True, verbose_name='指标名称')
    source_path = models.CharField(
        max_length=255, verbose_name='字段路径',
        help_text='点路径，如 candidate.age；数组用数字下标，如 candidate.workExperience.0.company',
    )
    data_type = models.CharField(
        max_length=16, choices=MetricDataType.choices,
        default=MetricDataType.STRING, verbose_name='数据类型',
    )
    unit = models.CharField(max_length=16, blank=True, default='', verbose_name='单位')
    description = models.CharField(
        max_length=255, blank=True, default='', verbose_name='说明',
    )
    # 是否枚举型（下拉 / 列表 / 多选字段自动生成时置 True，运算符白名单走 enum 分支）
    is_enum = models.BooleanField(default=False, verbose_name='枚举型')
    status = models.CharField(
        max_length=16, choices=MetricStatus.choices,
        default=MetricStatus.ENABLED, verbose_name='状态',
    )
    # 自动生成标记：由动态字段新增触发（区别于人工录入），便于追溯与隔离
    auto_generated = models.BooleanField(default=False, verbose_name='自动生成')

    class Meta:
        db_table = 'metrics_atomic_metric'
        verbose_name = '原子指标'
        verbose_name_plural = '原子指标'
        ordering = ['name']

    def __str__(self):
        return f'{self.name}({self.source_path})'

    @property
    def templates_using(self):
        """引用本原子指标的模板查询集（删除引用检查用）。"""
        return self.templates.all()


class DerivedMetric(FullAuditModel, UUIDModel):
    """派生指标 —— 计算型（注册表函数 + 参数），零代码覆盖遍历/聚合/时间窗规则。

    这是「无需频繁开发」能否成立的关键层：
      - 新增一个派生指标 = 选已有函数 + 配参数  → 零代码
      - 新增一种计算范式   = 注册一个新函数      → 唯一需要开发的场景（有意为之的少数）

    calc_func 不在模型层限定 choices —— 白名单由 services.derived_registry 动态提供，
    新增函数时不产生迁移、不改已有代码（开闭原则）。
    """
    name = models.CharField(max_length=64, unique=True, verbose_name='指标名称')
    calc_func = models.CharField(
        max_length=64, verbose_name='计算函数',
        help_text='派生函数注册表中的函数名，如 MAX_GAP / COUNT_IN_WINDOW / HIGHEST_EDU',
    )
    base_path = models.CharField(
        max_length=255, verbose_name='数据来源路径',
        help_text='计算所基于的嵌套数据路径，如 candidate.workExperience / candidate.education',
    )
    params = models.JSONField(
        default=dict, blank=True, verbose_name='函数参数',
        help_text='如 {"window_years": 5} / {"unit": "month"}',
    )
    data_type = models.CharField(
        max_length=16, choices=MetricDataType.choices,
        default=MetricDataType.NUMBER, verbose_name='数据类型',
    )
    unit = models.CharField(max_length=16, blank=True, default='', verbose_name='单位')
    description = models.CharField(
        max_length=255, blank=True, default='', verbose_name='说明',
    )
    status = models.CharField(
        max_length=16, choices=MetricStatus.choices,
        default=MetricStatus.ENABLED, verbose_name='状态',
    )

    class Meta:
        db_table = 'metrics_derived_metric'
        verbose_name = '派生指标'
        verbose_name_plural = '派生指标'
        ordering = ['name']

    def __str__(self):
        return f'{self.name}({self.calc_func})'


class MetricTemplate(FullAuditModel, UUIDModel):
    """指标模板 —— 业务人员可选单位：引用一个指标（原子 **或** 派生）+ 运算符子集。

    二选一约束：atomic_metric 与 derived_metric 必须恰好一个非空（clean 校验）。
    operators 是 UnifiedOperator 的子集，规则配置时下拉按此过滤（PRD F-07）。
    """
    name = models.CharField(max_length=64, unique=True, verbose_name='模板名称')
    atomic_metric = models.ForeignKey(
        AtomicMetric, on_delete=models.PROTECT, null=True, blank=True,
        related_name='templates', verbose_name='引用原子指标',
    )
    derived_metric = models.ForeignKey(
        DerivedMetric, on_delete=models.PROTECT, null=True, blank=True,
        related_name='templates', verbose_name='引用派生指标',
    )
    operators = models.JSONField(
        default=list, verbose_name='支持的运算符',
        help_text='UnifiedOperator 取值子集（启用算子白名单），如 ["GT","LT","EQ","BETWEEN"]',
    )
    # ===== PRD 指标模板配置维度（参数范围/步长/显示/值域/允许空）=====
    # 统一收进 JSON 字段，非破坏性扩展；既有模板默认空值，前端按 schema 渲染。
    param_config = models.JSONField(
        default=dict, blank=True, verbose_name='参数配置',
        help_text='{min, max, step, prefix, suffix, allOption}；'
                  '离散型 step 必须为整数，连续型 step 可为任意正数',
    )
    value_domain = models.JSONField(
        default=dict, blank=True, verbose_name='值域配置',
        help_text='{segments:[{min, max, step, label}]}；分段值域，留空表示自由区间',
    )
    param_enums = models.JSONField(
        default=list, blank=True, verbose_name='参数枚举',
        help_text='枚举型指标的允许取值列表，如 ["本科","硕士","博士"]',
    )
    param_allow_null = models.BooleanField(default=False, verbose_name='允许为空')
    status = models.CharField(
        max_length=16, choices=MetricStatus.choices,
        default=MetricStatus.ENABLED, verbose_name='状态',
    )
    description = models.CharField(
        max_length=255, blank=True, default='', verbose_name='说明',
    )

    class Meta:
        db_table = 'metrics_metric_template'
        verbose_name = '指标模板'
        verbose_name_plural = '指标模板'
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        has_atomic = self.atomic_metric_id is not None
        has_derived = self.derived_metric_id is not None
        if has_atomic == has_derived:
            raise ValidationError('模板必须且只能引用一个指标（原子指标或派生指标）')
        invalid = [op for op in (self.operators or [])
                   if op not in UnifiedOperator.values]
        if invalid:
            raise ValidationError(f'不支持的运算符: {invalid}')

    @property
    def metric(self):
        """返回被引用的指标实例（原子优先，二者互斥）。"""
        return self.atomic_metric or self.derived_metric

    @property
    def metric_kind(self):
        return 'atomic' if self.atomic_metric_id else 'derived'

    @property
    def metric_path(self):
        """指标的数据路径（原子=source_path，派生=base_path），用于结果描述。"""
        m = self.metric
        if m is None:
            return ''
        return m.source_path if self.metric_kind == 'atomic' else m.base_path

    @property
    def data_type(self):
        m = self.metric
        return m.data_type if m else MetricDataType.STRING

    @property
    def unit(self):
        m = self.metric
        return m.unit if m else ''


class MetricRuleScene(models.TextChoices):
    """规则应用场景 —— 决定规则在哪个业务触发点被执行（T3 接入用）。"""
    TALENT_POOL = 'TALENT_POOL', '入池'
    FILTER = 'FILTER', '筛选'
    SCORING = 'SCORING', '评分'
    MANUAL = 'MANUAL', '手动执行'


class MetricActionType(models.TextChoices):
    """规则动作类型（T4，取代布尔 blocking）。

    语义对齐「智能筛选规则中台」规格书的 VETO/DEDUCT/BONUS 三级动作：
      - VETO  必须满足：不满足即拒绝业务动作（原 blocking=True 的等价语义）
      - DEDUCT 优先考虑：不满足时仅记录/降权，不阻断（原 blocking=False 的等价语义）
      - BONUS 加分项：满足条件给予正向加权，不满足不惩罚

    迁移 0004 将既有 blocking 值回填到本字段（True→VETO，False→DEDUCT）；
    0005 已删除遗留 blocking 字段，动作语义完全由本枚举承载。
    """
    VETO = 'VETO', '必须满足'
    DEDUCT = 'DEDUCT', '优先考虑'
    BONUS = 'BONUS', '加分项'


class MetricRule(FullAuditModel, UUIDModel):
    """指标规则 —— 一组条件 + 组合逻辑，可持久化并启用/停用。

    为什么独立建表而不是复用 rule_engine.Rule：
        rule_engine.Rule 语义是「触发-条件-动作」（trigger_type 必填、带 Action），
        而指标规则只有条件、没有触发器与动作，强塞会造成语义混乱并触发
        rule_engine 的一致性检查告警。本表**只存条件**，执行时仍然复用
        rule_engine.UnifiedOperator 与 apps.metrics 执行引擎 —— 因此不是第三套规则
        系统，只是规则载体按用途分离（与 Demand 动态字段配置独立建表同理）。

    scene 决定规则在哪个业务触发点被执行（入池 / 筛选 / 评分 / 仅手动）。
    """

    name = models.CharField(max_length=128, verbose_name='规则名称')
    description = models.CharField(
        max_length=255, blank=True, default='', verbose_name='说明',
    )
    scene = models.CharField(
        max_length=16, choices=MetricRuleScene.choices,
        default=MetricRuleScene.MANUAL, verbose_name='应用场景', db_index=True,
    )
    conditions = models.JSONField(
        default=list, verbose_name='条件列表',
        help_text='[{templateId, operator, value, meta?{min,max}}]',
    )
    logic = models.CharField(
        max_length=8, choices=[('AND', 'AND'), ('OR', 'OR')],
        default='AND', verbose_name='条件组合逻辑',
    )
    status = models.CharField(
        max_length=16, choices=MetricStatus.choices,
        default=MetricStatus.ENABLED, verbose_name='状态',
    )
    enabled = models.BooleanField(default=True, verbose_name='启用开关', db_index=True)
    action_type = models.CharField(
        max_length=16, choices=MetricActionType.choices,
        default=MetricActionType.DEDUCT, verbose_name='动作类型', db_index=True,
        help_text='VETO=必须满足(不满足即拒绝业务动作)；'
                  'DEDUCT=优先考虑(不满足仅记录/降权不阻断)；'
                  'BONUS=加分项(满足给正向加权)',
    )
    class Meta:
        db_table = 'metrics_metric_rule'
        verbose_name = '指标规则'
        verbose_name_plural = '指标规则'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['scene', 'enabled'], name='metrics_rule_scene_en'),
        ]

    def __str__(self):
        return f'{self.name}({self.scene})'

    @property
    def is_active(self) -> bool:
        """是否真正生效：状态启用 + 开关打开。"""
        return self.enabled and self.status == MetricStatus.ENABLED

    def to_engine_conditions(self) -> list:
        """转成执行引擎契约（兼容 templateId / template_id 两种拼写）。"""
        out = []
        for cond in self.conditions or []:
            if not isinstance(cond, dict):
                continue
            out.append({
                'templateId': cond.get('templateId') or cond.get('template_id'),
                'operator': cond.get('operator'),
                'value': cond.get('value'),
                'meta': cond.get('meta') or {},
            })
        return out

    def clean(self):
        """程序态校验钩子（admin / 表单直写路径）。

        请求态校验由 MetricRuleSerializer.validate() 完成；此处提供模型级钩子，
        由 Django admin 的 ModelForm.full_clean 触发，作为防御纵深第二层。
        未 override save() 主动调用 clean()，以避免破坏既有程序化写入
        （Celery 任务、迁移回填等），降低爆炸半径。
        """
        super().clean()
        errors = validate_metric_rule({
            'name': self.name,
            'scene': self.scene,
            'logic': self.logic,
            'conditions': self.conditions,
            'action_type': getattr(self, 'action_type', None),
            'id': self.pk,
        })
        if errors:
            raise ValidationError({'conditions': errors})
