"""人员比例管控系统 v2.4 — 数据模型（管控人数直接承载于规则上）。

建模层次：
  ControlDimension  维度（院校标签/专业标签/性别），可单独配置。
  ControlIndicator  指标（关联维度，如 985 / 男 / 工学）。
  ControlRule       管控规则 + 人数目标（单一事实来源）：
                    适用范围(bu/position/level) + 维度 + 指标 + 年度
                    -> 目标占比 / 控制强度 / 年度目标人数 / 12 个月目标。
                    （取消原上下限 lo/hi 配置；取消独立的人数目标表 ControlHeadcount）

适用范围语义：bu / position / level 三者均空 = 「全局」（不限定）；否则按部门/职务/职级过滤。
Person 的 position（职务）/ level（职级）用于命中指定范围。

所有模型继承 FullAuditModel（审计）+ UUIDModel（nanoid 主键）；删除采用硬删。
"""
from django.db import models

from apps.common.models import FullAuditModel, UUIDModel
from .constants import (
    DEPTS, SCHOOLS, MAJORS, SEXES, DIMS, STRENGTH, STATUS,
    POSITIONS, LEVELS,
)


def _default_monthly():
    """12 个日历月目标，默认全 0。"""
    return [0] * 12


class ControlDimension(FullAuditModel, UUIDModel):
    """维度（如 院校标签/专业标签/性别），可自由新增，可单独配置。"""

    name = models.CharField(max_length=16, unique=True, verbose_name='维度')
    code = models.CharField(max_length=16, blank=True, default='', verbose_name='编码')
    is_active = models.BooleanField(default=True, verbose_name='启用')

    class Meta:
        verbose_name = '管控维度'
        verbose_name_plural = '管控维度'
        ordering = ['name']

    def __str__(self):
        return self.name


class ControlIndicator(FullAuditModel, UUIDModel):
    """指标（关联维度，可单独配置）。如 985 / 男 / 工学。"""

    dimension = models.ForeignKey(
        ControlDimension, on_delete=models.CASCADE, related_name='indicators',
        verbose_name='维度'
    )
    name = models.CharField(max_length=32, verbose_name='指标名称')
    is_active = models.BooleanField(default=True, verbose_name='启用')

    class Meta:
        verbose_name = '管控指标'
        verbose_name_plural = '管控指标'
        unique_together = [('dimension', 'name')]
        ordering = ['dimension', 'name']

    def __str__(self):
        return f'{self.dimension.name}·{self.name}'


class ControlRule(FullAuditModel, UUIDModel):
    """管控规则 + 人数目标（单一事实来源）。

    适用范围：bu / position / level 均空 = 全局；否则按部门/职务/职级过滤。
    同一 (bu, position, level, dimension, year) 下所有 indicator 的 target 之和必须 == 1.0（100%），
    由批量保存端点硬校验（见 views.batch / views.with_targets）。
    人数目标（年度 + 12 个月）直接承载于规则上（指标层），取消独立 ControlHeadcount 表。
    """

    # 适用范围（全空 = 全局）
    bu = models.CharField(
        max_length=16, blank=True, default='',
        choices=[(d, d) for d in DEPTS], verbose_name='部门'
    )
    position = models.CharField(
        max_length=32, blank=True, default='',
        choices=[(p, p) for p in POSITIONS], verbose_name='职务'
    )
    level = models.CharField(
        max_length=32, blank=True, default='',
        choices=[(l, l) for l in LEVELS], verbose_name='职级'
    )

    dimension = models.ForeignKey(
        ControlDimension, on_delete=models.CASCADE, related_name='rules', verbose_name='维度'
    )
    indicator = models.ForeignKey(
        ControlIndicator, on_delete=models.CASCADE, related_name='rules', verbose_name='指标'
    )
    # 规划年度（人数目标所属年）；同 (适用范围, 维度, 指标, 年度) 唯一
    year = models.IntegerField(default=2026, verbose_name='规划年度')
    # 占比以小数存储（0~1）；前端以百分比输入后 ÷100
    target = models.DecimalField(max_digits=6, decimal_places=4, verbose_name='目标占比')
    strength = models.CharField(
        max_length=16, choices=[(s, s) for s in STRENGTH],
        default='硬约束', verbose_name='控制强度'
    )
    # 人数目标（管控人数）：年度目标 + 12 个月目标（指标层）
    annual_target = models.IntegerField(default=0, verbose_name='年度目标人数')
    # 长度 12，下标 0=1月 .. 11=12月
    monthly_targets = models.JSONField(default=_default_monthly, verbose_name='12个月目标')

    class Meta:
        verbose_name = '管控规则'
        verbose_name_plural = '管控规则'
        unique_together = [('bu', 'position', 'level', 'dimension', 'indicator', 'year')]
        ordering = ['bu', 'position', 'level', 'dimension', 'indicator', 'year']

    def __str__(self):
        scope = self.bu or '全局'
        return f'[{scope}]·{self.dimension.name}·{self.indicator.name}·{self.year}'


class Person(FullAuditModel, UUIDModel):
    """人员主数据：一行一人。counted=True 才计入核算。

    position（职务）/ level（职级）用于命中指定适用范围。
    """

    code = models.CharField(max_length=32, unique=True, verbose_name='人员编码')
    name = models.CharField(max_length=64, verbose_name='姓名')
    bu = models.CharField(
        max_length=16, choices=[(d, d) for d in DEPTS], verbose_name='部门'
    )
    school = models.CharField(
        max_length=16, choices=[(s, s) for s in SCHOOLS], verbose_name='院校标签'
    )
    sex = models.CharField(
        max_length=4, choices=[(s, s) for s in SEXES], verbose_name='性别'
    )
    major = models.CharField(
        max_length=16, choices=[(m, m) for m in MAJORS], verbose_name='专业标签'
    )
    month = models.CharField(max_length=8, verbose_name='招聘月份')
    status = models.CharField(
        max_length=16, choices=[(s, s) for s in STATUS],
        default='在职', verbose_name='状态'
    )
    # 日期字段：用于按「预计入职日期 / 实际入职日期」计入核算月份
    expected_entry_date = models.DateField(
        null=True, blank=True, verbose_name='预计入职日期'
    )
    actual_entry_date = models.DateField(
        null=True, blank=True, verbose_name='实际入职日期'
    )
    position = models.CharField(
        max_length=32, blank=True, default='',
        choices=[(p, p) for p in POSITIONS], verbose_name='职务'
    )
    level = models.CharField(
        max_length=32, blank=True, default='',
        choices=[(l, l) for l in LEVELS], verbose_name='职级'
    )
    counted = models.BooleanField(default=True, verbose_name='计入核算')

    class Meta:
        verbose_name = '人员主数据'
        verbose_name_plural = '人员主数据'
        ordering = ['bu', 'code']

    def __str__(self):
        return f'{self.code}·{self.name}'


class PersonDimensionValue(FullAuditModel, UUIDModel):
    """人员动态维度取值（如 身份证籍贯=江苏）。

    与写死的 school/sex/major 三个 legacy 维度解耦：任何在「维度管理」中新增的维度，
    其人员取值都落到本表，计算引擎通过 __dim__<维度名> 读取，无需改代码。
    """

    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name='dimension_values', verbose_name='人员'
    )
    dimension = models.ForeignKey(
        ControlDimension, on_delete=models.CASCADE, related_name='person_values', verbose_name='维度'
    )
    value = models.CharField(max_length=64, verbose_name='取值')

    class Meta:
        verbose_name = '人员维度取值'
        verbose_name_plural = '人员维度取值'
        unique_together = [('person', 'dimension')]
        ordering = ['person', 'dimension']

    def __str__(self):
        return f'{self.person.code}·{self.dimension.name}={self.value}'
