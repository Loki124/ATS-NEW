"""mou models - 2026-07-01 stub for permissions-v2/* (G36 任务待补真业务)"""
from django.db import models
from apps.core.models import User, Department


class MouAgreement(models.Model):
    """MOU 协议"""
    id = models.CharField(max_length=32, primary_key=True)
    code = models.CharField(max_length=50, unique=True, help_text='MOU 编码, 如 MOU-2026-001')
    name = models.CharField(max_length=200, blank=True, default='', help_text='MOU 名称 (FE 字段, 兼容)')  # 2026-07-01: 加给 FE
    company_name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    signed_at = models.DateField(null=True, blank=True)
    effective_at = models.DateField(null=True, blank=True)
    expire_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='DRAFT', help_text='DRAFT/ACTIVE/EXPIRED/TERMINATED')
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='mou_agreements')
    description = models.TextField(blank=True, default='', help_text='描述 (FE 字段, 兼容 terms)')  # 2026-07-01
    terms = models.TextField(blank=True, default='', help_text='MOU 条款')
    mou_type = models.CharField(max_length=50, blank=True, default='STANDARD', help_text='MOU 类型: STANDARD/EXCLUSIVE/PROJECT_BASED')  # 2026-07-01
    scopes = models.JSONField(default=list, blank=True, help_text='权限范围 list (FE 字段)')  # 2026-07-01
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mou_agreements'
        verbose_name = 'MOU 协议'

    def __str__(self):
        return f'{self.code} - {self.company_name}'


class MouContainer(models.Model):
    """MOU 容器 (招聘需求 + 配额)"""
    id = models.CharField(max_length=32, primary_key=True)
    mou = models.ForeignKey(MouAgreement, on_delete=models.CASCADE, related_name='containers')
    code = models.CharField(max_length=50)
    position_title = models.CharField(max_length=200)
    # 2026-07-02: 加 G36 stub model 缺的字段, 配合前端表单
    type = models.CharField(max_length=50, blank=True, default='', help_text='容器类型: PROJECT/DEPARTMENT/...')  # FE 字段
    description = models.TextField(blank=True, default='', help_text='容器描述')  # FE 字段
    resource_filter = models.JSONField(default=dict, blank=True, help_text='资源过滤条件 (JSON)')  # FE 字段
    quota_total = models.IntegerField(default=0)
    quota_used = models.IntegerField(default=0)
    quota_status = models.CharField(max_length=20, default='ACTIVE', help_text='ACTIVE/INACTIVE/EXHAUSTED')  # FE 字段 status
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mou_containers'
        verbose_name = 'MOU 配额容器'


class MutualExclusionGroup(models.Model):
    """互斥组 (同一候选人不能同时在某些流程)"""
    id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    members = models.JSONField(default=list, help_text='互斥的 stage id list')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mou_mutual_exclusion_groups'
        verbose_name = '互斥组'


class MouRule(models.Model):
    """MOU 自动化规则 (自动审批/自动推进)。

    Phase 4（2026-09-01）重命名自 ``AutomationRule``，消除与 ``automation.AutomationRule``
    的命名冲突（设计文档 §1.2 / §3.6）。仅改 Python 类名，``db_table`` 保持
    ``mou_automation_rules`` 不变，历史数据零迁移抖动。
    """

    id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=100)
    trigger_event = models.CharField(max_length=50, help_text='如 stage-entered/candidate-added')
    conditions = models.JSONField(default=dict)
    actions = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mou_automation_rules'
        verbose_name = 'MOU 自动化规则'
