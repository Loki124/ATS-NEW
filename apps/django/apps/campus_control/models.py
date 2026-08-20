"""人员比例管控系统 — 数据模型。

ControlRule: 管控规则（唯一数据源），按 (dim, group) 唯一。
Person:      人员主数据（一行一人），counted=True 才参与核算。
两者均继承 FullAuditModel（审计）+ UUIDModel（nanoid 主键）；
删除采用硬删（instance.delete()），不软删，避免 unique_together 占位冲突，
且契合 PRD §4.1 的 deleteRule/deletePerson 语义。
"""
from django.db import models

from apps.common.models import FullAuditModel, UUIDModel
from .constants import (
    DEPTS, SCHOOLS, MAJORS, SEXES, MONTHS, DIMS, STRENGTH, STATUS,
)


class ControlRule(FullAuditModel, UUIDModel):
    """管控规则：四维度（部门/院校标签/性别/专业标签）的比例 + 人数规划。"""

    dim = models.CharField(
        max_length=16, choices=[(d, d) for d in DIMS], verbose_name='维度'
    )
    group = models.CharField(max_length=32, verbose_name='分组')
    # 占比以小数存储（0~1）；前端以百分比输入后 ÷100
    target = models.DecimalField(max_digits=6, decimal_places=4, verbose_name='目标占比')
    lo = models.DecimalField(max_digits=6, decimal_places=4, verbose_name='下限占比')
    hi = models.DecimalField(max_digits=6, decimal_places=4, verbose_name='上限占比')
    strength = models.CharField(
        max_length=16, choices=[(s, s) for s in STRENGTH],
        default='硬约束', verbose_name='控制强度'
    )
    whole = models.IntegerField(default=0, verbose_name='整体目标人数')
    month_target = models.IntegerField(default=0, verbose_name='本月目标人数')

    class Meta:
        verbose_name = '管控规则'
        verbose_name_plural = '管控规则'
        unique_together = [('dim', 'group')]
        ordering = ['dim', 'group']

    def __str__(self):
        return f'{self.dim}·{self.group}'


class Person(FullAuditModel, UUIDModel):
    """人员主数据：一行一人。counted=True 才计入核算。"""

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
        default='已入职', verbose_name='状态'
    )
    counted = models.BooleanField(default=True, verbose_name='计入核算')

    class Meta:
        verbose_name = '人员主数据'
        verbose_name_plural = '人员主数据'
        ordering = ['bu', 'code']

    def __str__(self):
        return f'{self.code}·{self.name}'
