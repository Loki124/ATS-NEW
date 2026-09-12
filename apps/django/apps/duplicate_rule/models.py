"""重复候选人规则模型

两张表：
1. DuplicateConfig —— 单例 JSON 配置（沿用 standard_resume / brand 的单体配置模式）
   - key='merge'       重复候选人合并规则（全局）
   - key='application' 重复申请管理（社招）
2. DuplicateRule —— 候选人查重规则（多套，含系统内置 + 用户自定义）

查重项以 JSON 存储（引用 catalog.DUPLICATE_FIELD_CATALOG 的 key + strength），
与 RegistrationForm.fields 的存储策略一致：结构化程度不高，避免多一层关联表。
"""
from django.db import models

from apps.common.models import FullAuditModel

from .catalog import LOGIC_ALL, LOGIC_CHOICES, SCOPE_ALL, SCOPE_CHOICES


class DuplicateConfig(FullAuditModel):
    """重复候选人管理 —— 单例 JSON 配置

    key 固定，config 为自由 JSON dict：
    - 'merge'（重复候选人合并规则，全局）：
        {
          enabled: bool,                       # 自动合并重复候选人
          cancel_unaccepted_headhunter: bool,  # 取消自动合并未接收的猎头申请
          strategies: [{key, label, value, options: [{value, label}]}, ...]
        }
    - 'application'（重复申请管理，社招）：
        {
          enabled: bool,
          window_months: 6 | 12 | 24,
          window_options: [{value, label}, ...]
        }
    """

    key = models.CharField(
        max_length=64, unique=True, default='merge', verbose_name='配置键',
    )
    config = models.JSONField(default=dict, blank=True, verbose_name='配置内容')

    class Meta:
        db_table = 'dup_configs'
        verbose_name = '重复候选人配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'DuplicateConfig({self.key})'


class DuplicateRule(FullAuditModel):
    """候选人查重规则

    对应截图「候选人查重规则」列表与「新建候选人查重规则」抽屉：
    - name             规则名称（如 基于联系方式）
    - scope            适用范围：ALL 全局 / SOCIAL 社招 / CAMPUS 校招
    - is_system        True 为系统内置规则（可停用、可否改项，但不可删除）
    - condition_logic  ALL=勾选项全部一致；ANY=勾选项任意 any_count 项一致
    - any_count        condition_logic=ANY 时的 N（1 ≤ N ≤ 勾选项数量）
    - items            查重项列表：[{'key': 'phone', 'strength': 'MEDIUM'}, ...]
    - is_enabled       启用状态（列表页「启用 / 停用」）
    - order_index      排序
    """

    name = models.CharField(max_length=128, verbose_name='规则名称')
    scope = models.CharField(
        max_length=16, choices=SCOPE_CHOICES, default=SCOPE_ALL, verbose_name='适用范围',
    )
    is_system = models.BooleanField(default=False, verbose_name='系统内置')
    condition_logic = models.CharField(
        max_length=8, choices=LOGIC_CHOICES, default=LOGIC_ALL, verbose_name='查重条件',
    )
    any_count = models.PositiveSmallIntegerField(default=1, verbose_name='任意一致项数')
    items = models.JSONField(default=list, blank=True, verbose_name='查重项')
    is_enabled = models.BooleanField(default=True, verbose_name='启用')
    order_index = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'dup_rules'
        ordering = ['order_index', 'id']
        verbose_name = '候选人查重规则'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'DuplicateRule({self.name})'
