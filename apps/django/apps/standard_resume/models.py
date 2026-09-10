"""标准简历配置模型

单体 JSON 存储，与前端 StandardResumeConfig 同构：
{ fields: [{fieldKey, enabled, required}], requiredStages: [stageKey, ...] }。

参考 apps.demand.models.DemandSetting（招聘需求全局配置）的同款模式：
key 固定 + config 自由 JSON dict，camel-case 解析器入参 snake 化、渲染器出参 camel 化，
整份 round-trip 安全。
"""
from django.db import models

from apps.common.models import FullAuditModel


class StandardResumeConfig(FullAuditModel):
    """标准简历全局配置（单体 JSON 存储）—— FE StandardResumeSettings.vue 调用

    key 固定 'standard_resume'，config 为自由 JSON dict：
    { fields: [{fieldKey, enabled, required}], requiredStages: [stageKey, ...] }。
    fields 引用动态字段模块 resource='Candidate' 的 fieldKey；requiredStages 为命中
    必填校验的招聘阶段 key 列表（与前端 STANDARD_RESUME_STAGES 对齐）。
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
