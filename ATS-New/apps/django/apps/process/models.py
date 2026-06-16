"""Process Models

按 PRD v4 重新设计，与现有 Prisma schema 字段兼容但更规范化：
- RecruitmentStage: 阶段（库）
- RecruitmentProcess: 招聘流程
- ProcessStageLink: 流程-阶段关联（含阶段规则）
- ProcessTemplate: 流程模板
- StageRule: 阶段规则（自动流转/默认处理人/限时）
"""
from django.db import models
from django_fsm import FSMField, transition
from apps.common.models import TimestampedModel, SoftDeleteModel, FullAuditModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


# ============================================================
# 阶段类型常量
# ============================================================
class StageType(models.TextChoices):
    SCREEN = 'SCREEN', '筛选型'
    INVITATION = 'INVITATION', '邀约型'
    INTERVIEW = 'INTERVIEW', '面试型'
    OFFER = 'OFFER', 'Offer型'


class StageStatus(models.TextChoices):
    ENABLED = 'ENABLED', '启用'
    DISABLED = 'DISABLED', '停用'


class ProcessingRule(models.TextChoices):
    """默认处理人处理规则（PRD v4 §11.4）"""
    DIRECT = 'DIRECT', '直接分配（默认）'
    SEQUENTIAL = 'SEQUENTIAL', '按页面展示顺序执行'
    ROUND_ROBIN = 'ROUND_ROBIN', '邀约阶段轮流邀约制'
    NONE = 'NONE', '无特定规则'


class EffectiveScope(models.TextChoices):
    """阶段限时生效方式"""
    ALL = 'ALL', '对全部候选人生效'
    NEW_ONLY = 'NEW_ONLY', '对新进入候选人生效'


class TimeLimitRuleStatus(models.TextChoices):
    ENABLED = 'ENABLED', '启用'
    DISABLED = 'DISABLED', '停用'


# ============================================================
# 阶段库
# ============================================================
class RecruitmentStage(FullAuditModel):
    """阶段（阶段库，全局共享）

    业务规则（PRD §8.2）：
    - BR-001: 系统预置起止阶段【初评】【正式录用】，可编辑、不可停用、不可删除
    - BR-002: 阶段被任一流程引用时，不可停用
    - BR-003: 阶段被任一流程引用时，不可删除
    - BR-004: 停用阶段编号不复用，新阶段递增
    - BR-007: 面试型阶段支持"待安排"中间态
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    code = models.CharField(max_length=20, unique=True, verbose_name='阶段编号', help_text='P+三位流水号')
    name = models.CharField(max_length=20, unique=True, verbose_name='阶段名称', help_text='限 20 字，不可重复')
    stage_type = models.CharField(max_length=20, choices=StageType.choices, verbose_name='阶段类型')
    status = models.CharField(
        max_length=16, choices=StageStatus.choices,
        default=StageStatus.ENABLED, db_index=True, verbose_name='状态',
    )

    # 预置阶段标志
    is_builtin = models.BooleanField(default=False, db_index=True, verbose_name='预置阶段')

    # 默认功能（根据类型自动带出）
    default_features = models.JSONField(default=list, verbose_name='默认功能')
    # 可选功能
    optional_features = models.JSONField(default=list, verbose_name='可选功能')

    description = models.TextField(blank=True, max_length=200, verbose_name='描述')

    class Meta:
        db_table = 'recruitment_stages'
        verbose_name = '阶段'
        verbose_name_plural = verbose_name
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'

    @property
    def reference_count(self):
        return self.process_stage_links.filter(
            process__status__in=['ENABLED', 'ARCHIVED']
        ).count()

    @property
    def is_referenced(self):
        return self.reference_count > 0

    @property
    def supports_to_be_scheduled(self):
        """仅面试型阶段支持"待安排"中间态"""
        return self.stage_type == StageType.INTERVIEW


# ============================================================
# 招聘流程
# ============================================================
class RecruitmentProcess(FullAuditModel):
    """招聘流程

    业务规则（PRD §9.2）：
    - BR-101: 流程被至少一个职位需求引用后，配置修改将生成新版本
    - BR-102: 已在跑的候选人走创建时的版本
    - BR-103: 历史版本只读
    - BR-104: 支持历史候选人"升版本"
    - BR-105: 流程无草稿态，配置即时生效
    - BR-106: 流程无停用态，只能归档
    """
    STATUS_CHOICES = [
        ('ENABLED', '启用'),
        ('ARCHIVED', '已归档'),
    ]

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    code = models.CharField(max_length=20, unique=True, verbose_name='流程编号', help_text='W+三位流水号')
    name = models.CharField(max_length=30, verbose_name='流程名称', help_text='限 30 字，不可重复')
    current_version = models.CharField(max_length=20, default='1.0', verbose_name='当前版本', help_text='如 V1.2')

    # 适用范围条件表达式（PRD v4 §9.4）
    applicable_scope = models.JSONField(
        default=dict, blank=True,
        verbose_name='适用范围',
        help_text='{"items": [...conditions], "expression": "(1 AND 2) OR 3"}',
    )

    is_template = models.BooleanField(default=False, db_index=True, verbose_name='是否模板')
    template_code = models.CharField(
        max_length=50, null=True, blank=True, db_index=True,
        verbose_name='模板编码',
        help_text='SOCIAL_TECH / CAMPUS_GENERAL / HEADHUNTER_SENIOR / INTERNAL_TRANSFER',
    )

    # 配置
    is_enabled = models.BooleanField(default=True, verbose_name='启用')
    validate_resume_score = models.BooleanField(default=True, verbose_name='校验简历评分')
    description = models.CharField(max_length=100, blank=True, verbose_name='描述')

    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default='ENABLED',
        db_index=True, verbose_name='状态',
    )
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name='归档时间')

    class Meta:
        db_table = 'recruitment_processes'
        verbose_name = '招聘流程'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.code} {self.name} ({self.current_version})'

    @property
    def reference_count(self):
        return self.demands.count()


# ============================================================
# 流程-阶段关联
# ============================================================
class ProcessStageLink(FullAuditModel):
    """流程-阶段关联

    包含阶段在特定流程中的：
    - 排序（order）
    - 阶段规则（StageRule 一对一）
    - 进入条件规则（EntryCondition 一对多）
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    process = models.ForeignKey(
        RecruitmentProcess, on_delete=models.CASCADE,
        related_name='stage_links', verbose_name='所属流程',
    )
    stage = models.ForeignKey(
        RecruitmentStage, on_delete=models.PROTECT,
        related_name='process_stage_links', verbose_name='阶段',
    )

    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name='顺序')
    is_required = models.BooleanField(default=True, verbose_name='是否必经')

    # V4 新增：进入条件规则列表（保留为 JSON 缓存以提速）
    entry_rule_expression = models.CharField(
        max_length=500, blank=True,
        verbose_name='全局规则表达式',
        help_text='如 (1 AND 2) OR (3 AND 4)',
    )

    class Meta:
        db_table = 'process_stage_links'
        verbose_name = '流程-阶段关联'
        verbose_name_plural = verbose_name
        unique_together = [('process', 'stage')]
        ordering = ['process', 'order']

    def __str__(self):
        return f'{self.process.name} → {self.stage.name} (#{self.order})'


# ============================================================
# 阶段规则
# ============================================================
class StageRule(FullAuditModel):
    """阶段规则

    字段说明（PRD v4 §11）：
    - processing_rule: 处理规则（DIRECT/SEQUENTIAL/ROUND_ROBIN/NONE）
    - processor_order: 处理人顺序列表（仅 SEQUENTIAL 模式）
    - current_processor_index: 当前处理人索引
    - auto_skip_n_plus_two: N+2 推荐免筛选
    - inherit_prior_consensus: 引用前序双 A 的一致意见
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    link = models.OneToOneField(
        ProcessStageLink, on_delete=models.CASCADE,
        related_name='stage_rule', verbose_name='流程-阶段关联',
    )

    # 默认处理人
    data_source = models.CharField(
        max_length=32, blank=True, verbose_name='数据来源',
        help_text='DEMAND / POSITION / NONE',
    )
    data_field = models.CharField(
        max_length=64, blank=True, verbose_name='取值字段',
        help_text='如 hiring_manager / position_owner',
    )

    processing_rule = models.CharField(
        max_length=32, choices=ProcessingRule.choices,
        default=ProcessingRule.DIRECT, verbose_name='处理规则',
    )
    processor_order = models.JSONField(
        default=list, blank=True, verbose_name='处理人顺序列表',
        help_text='SEQUENTIAL 模式下使用，array of userId',
    )
    current_processor_index = models.IntegerField(default=0, verbose_name='当前处理人索引')

    # 自动处理规则
    auto_skip_n_plus_two = models.BooleanField(default=False, verbose_name='N+2 推荐免筛选')
    inherit_prior_consensus = models.BooleanField(default=False, verbose_name='引用前序双 A 意见')

    # 阶段限时（兼容旧字段 - 已废弃，请使用 TimeLimitRule）
    legacy_time_limit_days = models.IntegerField(
        null=True, blank=True, verbose_name='(已废弃)阶段限时天数',
    )
    legacy_grab_threshold = models.IntegerField(
        null=True, blank=True, verbose_name='(已废弃)抢单阈值',
    )

    # 抢单配置
    is_grab_mode = models.BooleanField(default=False, verbose_name='抢单模式')
    grab_threshold = models.IntegerField(default=30, verbose_name='抢单阈值')

    # 面试相关
    interview_rounds = models.IntegerField(default=1, verbose_name='面试轮次')
    interview_format = models.CharField(
        max_length=32, blank=True, verbose_name='面试形式',
        help_text='SINGLE/JOINT/COMPREHENSIVE',
    )

    class Meta:
        db_table = 'stage_rules'
        verbose_name = '阶段规则'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'StageRule[{self.link.stage.name} / {self.processing_rule}]'


# ============================================================
# 流程模板（V4.0 预置 4 套）
# ============================================================
class ProcessTemplate(FullAuditModel):
    """流程模板 - 预置/用户保存"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    code = models.CharField(max_length=50, unique=True, verbose_name='模板编码')
    name = models.CharField(max_length=100, verbose_name='模板名称')
    description = models.TextField(blank=True, verbose_name='描述')
    category = models.CharField(max_length=50, verbose_name='分类', help_text='SOCIAL/CAMPUS/HEADHUNTER/INTERNAL/CUSTOM')

    # 模板快照 - 完整流程定义
    snapshot = models.JSONField(default=dict, verbose_name='流程快照', help_text='包含 stages + rules + scope')

    is_builtin = models.BooleanField(default=False, db_index=True, verbose_name='预置')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='启用')

    class Meta:
        db_table = 'process_templates'
        verbose_name = '流程模板'
        verbose_name_plural = verbose_name
        ordering = ['-is_builtin', 'name']

    def __str__(self):
        return f'[{self.code}] {self.name}'
