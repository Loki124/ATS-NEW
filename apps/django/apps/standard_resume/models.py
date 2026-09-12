"""标准简历 / 申请表 / 登记表 配置模型

两代设计并存：
1. StandardResumeConfig（单体 JSON 存储，沿用 demand 全局配置模式）：
   - key='standard_resume'  → 标准简历设置
   - key='candidate_info_table' → 候选人信息登记表设置（权限/使用范围/样式/场景联动）
   config 为自由 JSON dict，由各自 view 负责结构解析与校验。
2. RegistrationForm（结构化多表单）：
   - 取代原单套 application_form 单体配置，支持多套「申请表 / 登记表」。
   - 字段配置以 JSONField 存储，引用动态字段模块 resource='Candidate' 的 fieldKey。
"""
from django.db import models

from apps.common.models import FullAuditModel


class StandardResumeConfig(FullAuditModel):
    """标准简历 / 候选人信息登记表 全局配置（单体 JSON 存储）

    key 固定，config 为自由 JSON dict：
    - 'standard_resume'       → 标准简历配置
    - 'candidate_info_table'  → 候选人信息登记表配置：
        {
          permission_scope: 'global' | 'department',   # 登记表权限
          usage_scope:     'global' | 'department',     # 登记表使用范围
          resume_style:    'standard' | 'custom',      # 标准简历样式
          scenes: [                                         # 场景联动
            { key, label, formId, style }, ...
          ]
        }
    """

    key = models.CharField(
        max_length=64, unique=True, default='standard_resume', verbose_name='配置键',
    )
    config = models.JSONField(default=dict, blank=True, verbose_name='配置内容')

    class Meta:
        db_table = 'standard_resume_configs'
        verbose_name = '标准简历配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'StandardResumeConfig({self.key})'


class RegistrationForm(FullAuditModel):
    """登记 / 申请表（多套）

    截图「申请表和登记表设置」：
    - 左侧多表单列表（猎头更新简历登记表 / 性格测评结果回传 / 接受 offer 信息确认表 …）
    - 右侧预览 / 编辑（名称、适用部门、模式、分组字段显隐/必填）

    fields 结构（每项引用动态字段 resource='Candidate' 的 fieldKey）：
        [{"fieldKey": "...", "enabled": true, "required": false, "group": "上传"}, ...]
    departments 结构：['dept_id_1', 'dept_id_2', ...]
    """

    FORM_TYPE_CHOICES = [
        ('application', '申请表'),
        ('registration', '登记表'),
    ]

    name = models.CharField(max_length=128, verbose_name='表单名称')
    form_type = models.CharField(
        max_length=32, choices=FORM_TYPE_CHOICES,
        default='registration', verbose_name='表单类型',
    )
    departments = models.JSONField(default=list, blank=True, verbose_name='适用部门')
    mode = models.CharField(max_length=32, default='default', verbose_name='填写模式')
    fields = models.JSONField(default=list, blank=True, verbose_name='字段配置')
    order_index = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='启用')

    class Meta:
        db_table = 'sr_registration_forms'
        ordering = ['order_index', 'id']
        verbose_name = '登记/申请表'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'RegistrationForm({self.name})'
