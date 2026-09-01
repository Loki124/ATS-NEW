"""Process Models

按 PRD v4 重新设计，与现有 Prisma schema 字段兼容但更规范化：
- RecruitmentStage: 阶段（库）
- RecruitmentProcess: 招聘流程
- ProcessStageLink: 流程-阶段关联（含阶段规则）
- ProcessTemplate: 流程模板
- StageRule: 阶段规则（自动流转/默认处理人/限时）
"""
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django_fsm import FSMField, transition
from apps.common.models import TimestampedModel, SoftDeleteModel, FullAuditModel, SoftDeleteManager
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


# ============================================================
# 阶段类型常量
# ============================================================
class StageType(models.TextChoices):
    SCREEN = 'SCREEN', '筛选'
    INVITATION = 'INVITATION', '邀约'
    INTERVIEW = 'INTERVIEW', '面试'
    OFFER = 'OFFER', 'Offer'


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
    - BR-001: 系统预置起止阶段【初评】【正式录用】，可编辑、不可停用、不可删除；is_start/is_end 全局各只允许 1 个，由 seed 设置且通过序列化器/clean() 强制
    - BR-002: 阶段被任一流程引用时，不可停用
    - BR-003: 阶段被任一流程引用时，不可删除
    - BR-004: 停用阶段编号不复用，新阶段递增
    - BR-007: 面试型阶段支持"待安排"中间态
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    code = models.CharField(max_length=20, unique=True, verbose_name='阶段编号', help_text='P+三位流水号')
    name = models.CharField(max_length=20, unique=True, verbose_name='阶段名称', help_text='限 20 字，不可重复')
    stage_type = models.CharField(max_length=20, verbose_name='阶段类型')
    status = models.CharField(
        max_length=16, choices=StageStatus.choices,
        default=StageStatus.ENABLED, db_index=True, verbose_name='状态',
    )

    # 预置阶段标志
    is_builtin = models.BooleanField(default=False, db_index=True, verbose_name='预置阶段')

    # 起止阶段标记 (BR-001 强化: 全局有且仅有 1 个起始 = 初评, 1 个结束 = 正式录用)
    is_start = models.BooleanField(default=False, db_index=True, verbose_name='起始阶段')
    is_end = models.BooleanField(default=False, db_index=True, verbose_name='结束阶段')

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
        constraints = [
            # BR-001: 全局仅 1 个起始阶段, 1 个结束阶段
            # partial UniqueConstraint: MySQL 8.0.13+ / PostgreSQL 12+ 支持 (SQLite 早期版本会抛 NotSupportedError).
            # serializer validate 锁 select_for_update 是性能优化 + 友好错误信息,
            # DB constraint 是终极防线. 项目用 MySQL, 部署前确认 ≥ 8.0.13.
            models.UniqueConstraint(
                fields=['is_start'],
                condition=Q(is_start=True),
                name='uniq_only_one_start_stage',
            ),
            models.UniqueConstraint(
                fields=['is_end'],
                condition=Q(is_end=True),
                name='uniq_only_one_end_stage',
            ),
        ]

    def __str__(self):
        return f'{self.code} {self.name}'

    def clean(self):
        super().clean()
        # 阶段类型必须从数据字典中读取且已启用
        if self.stage_type:
            from apps.dictionary.models import DictionaryItem
            exists = DictionaryItem.objects.filter(
                type__code='recruitment_stage_type',
                key=self.stage_type,
                is_active=True,
                deleted_at__isnull=True,
            ).exists()
            if not exists:
                raise ValidationError({'stage_type': f'无效的阶段类型: {self.stage_type}'})

        # 互斥: 同一阶段不可同时为起始和结束
        if self.is_start and self.is_end:
            raise ValidationError({'is_start': '同一阶段不可同时为起始和结束阶段'})

        # 全局唯一性兜底 (model 层; serializer 层会先验, DB constraint 是最终防线)
        qs = RecruitmentStage.objects.filter(is_start=True)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if self.is_start and qs.exists():
            raise ValidationError({'is_start': '全局只能有 1 个起始阶段'})

        qs = RecruitmentStage.objects.filter(is_end=True)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if self.is_end and qs.exists():
            raise ValidationError({'is_end': '全局只能有 1 个结束阶段'})

    @property
    def reference_count(self):
        """被启用中流程引用的次数（已归档流程不计入）"""
        return self.process_stage_links.filter(
            process__status='ENABLED'
        ).count()

    @property
    def is_referenced(self):
        return self.reference_count > 0

    @property
    def supports_to_be_scheduled(self):
        """仅面试型阶段支持"待安排"中间态"""
        return self.stage_type == 'INTERVIEW'


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
    # code 刻意**不加** unique：同一条流程线（code）可有多行，每行是一个版本（T1 版本化）。
    # 唯一性改由 Meta.constraints 的 (code, version_seq) / (code, current_version) / C3' 三条约束承担。
    code = models.CharField(max_length=20, verbose_name='流程编号', help_text='W+三位流水号')
    name = models.CharField(max_length=30, verbose_name='流程名称', help_text='限 30 字，不可重复')
    # default 与解析逻辑必须对同一格式达成一致：serializers.py / template_apply.py 均写 'V1.0'，
    # 此处若留 '1.0' 会形成双来源，且升版逻辑拼出 '1.0+1' 这类垃圾版本号并经 __str__ 直达 UI。
    current_version = models.CharField(max_length=20, default='V1.0', verbose_name='当前版本', help_text='如 V1.2')

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

    # 版本化（T1）
    version_seq = models.PositiveIntegerField(default=1, db_index=True, verbose_name='版本序号')
    # is_latest 刻意**不加** db_index=True：低基数布尔单列索引近乎无用。
    # 主力查询 filter(code=..., is_latest=True, ...) 由下方复合索引 idx_process_code_latest 服务
    # （MySQL EXPLAIN 实测：仅有表达式索引时是 Table scan，加复合索引后为 Covering index lookup）。
    is_latest = models.BooleanField(default=False, verbose_name='是否最新版')

    class Meta:
        db_table = 'recruitment_processes'
        verbose_name = '招聘流程'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'is_latest'], name='idx_process_code_latest'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['code', 'version_seq'],
                name='uniq_process_code_version_seq',
            ),
            models.UniqueConstraint(
                fields=['code', 'current_version'],
                name='uniq_process_code_current_version',
            ),
            # C3'：每个 code 至多一行 is_latest=True。
            # 用表达式唯一索引让 DB 现算键值：is_latest=True 的行贡献 code，其余贡献 NULL；
            # 两库唯一索引均允许多个 NULL，故等价于「每 code 至多 1 行 latest」。
            # 严禁改成带 condition= 的 partial UniqueConstraint：MySQL supports_partial_indexes=False
            # 会让 Django 静默跳过（不报错、不建索引、不留痕迹），CI 全绿而生产无约束。
            models.UniqueConstraint(
                models.Case(
                    models.When(is_latest=True, then=models.F('code')),
                    default=models.Value(None),
                ),
                name='uniq_one_latest_per_code',
                violation_error_message='同一流程线（code）只能有一个最新版本（is_latest=True）',
            ),
        ]

    def __str__(self):
        return f'{self.code} {self.name} ({self.current_version})'

    def soft_delete(self, *args, **kwargs):
        """软删除时同步降级 is_latest。

        软删的流程行不得继续持有 is_latest=True：否则同 code 再建/克隆新行时会出现两行 latest
        （C3' 会直接抛 IntegrityError 打断正常业务）。

        基类 ``SoftDeleteModel.soft_delete()`` 只置 ``deleted_at`` 且用窄
        ``save(update_fields=['deleted_at', 'updated_at'])``——**不会**把 ``is_latest``
        写进库。故此处必须在调用 super() 之前显式单独落库一次。
        """
        if self.is_latest:
            self.is_latest = False
            self.save(update_fields=['is_latest', 'updated_at'])
        return super().soft_delete(*args, **kwargs)

    # 刻意**不** override restore()：恢复旧版本不得无条件抢回 latest，
    # 保持 is_latest=False 才是正确语义（如需提升须显式 promote）。

    @property
    def reference_count(self):
        """被引用的 **live** 需求数（X3/V8）。

        必须过滤软删：同语义的 ``versioning.is_process_referenced()`` 从来都过滤，
        这里不过滤等于同一个问题两套口径——``is_process_referenced()`` 说「没被引用」
        而 ``reference_count`` 说「3 个」，删除校验与提示文案会互相打脸。
        """
        return self.demands.filter(deleted_at__isnull=True).count()


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

    # 2026-07-03: 扩字段对齐 FE StageRuleConfigModal 用的字段集
    #   (autoAdvanceType / defaultHandlerType / timeLimit / interviewRoundIds).
    #   之前 FE 调用 /recruitment-rules/stage-rules (stub endpoint, 不入库),
    #   数据从未落到 model. 加上下面字段让 FE 走真 BE 后能持久化.
    auto_advance_type = models.CharField(
        max_length=32, blank=True, default='NONE', verbose_name='自动流转类型',
        help_text='NONE / MEET_NEXT / IGNORE_NEXT / MEET_NEXT_OR_N2 / N1_ALL_PASS',
    )
    auto_advance_timing = models.CharField(
        max_length=32, blank=True, default='NONE', verbose_name='自动流转触发时机',
        help_text='NONE / IMMEDIATE / DELAYED',
    )
    auto_advance_days = models.IntegerField(
        null=True, blank=True, verbose_name='延迟天数 (DELAYED 时使用)',
    )
    default_handler_type = models.CharField(
        max_length=32, blank=True, default='CUSTOM', verbose_name='默认处理人类型',
        help_text='FROM_DEMAND / FROM_POSITION / CUSTOM',
    )
    default_handler_fields = models.JSONField(
        default=list, blank=True, verbose_name='默认处理人字段',
    )
    default_handler_user_ids = models.JSONField(
        default=list, blank=True, verbose_name='默认处理人 user id 列表 (CUSTOM 时)',
    )
    time_limit = models.IntegerField(
        null=True, blank=True, verbose_name='阶段限时 (小时)',
    )
    time_limit_scope = models.CharField(
        max_length=32, blank=True, default='NEW_ONLY', verbose_name='限时范围',
        help_text='NEW_ONLY / ALL',
    )
    interview_round_ids = models.JSONField(
        default=list, blank=True, verbose_name='关联面试轮次 id 列表',
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


# ============================================================
# Phase 2 T06: CandidateScreen + CandidateRecommendation
# ============================================================
class CandidateScreen(SoftDeleteModel):
    """批量筛选记录 — 审计+查询

    POST /api/v1/processes/{id}/batch-screen/ 写入。
    设计依据: docs/PHASE2_DESIGN_2026-08-03.md §C.3.1
    """
    SCREEN_DECISIONS = [
        ('PASS', '通过'),
        ('REJECT', '淘汰'),
        ('KEEP', '待议'),
    ]

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    process = models.ForeignKey(
        RecruitmentProcess, on_delete=models.PROTECT,
        related_name='candidate_screens', verbose_name='所属流程',
    )
    candidate = models.ForeignKey(
        'candidate.Candidate', on_delete=models.PROTECT,
        related_name='screen_records', verbose_name='候选人',
    )
    stage = models.ForeignKey(
        RecruitmentStage, on_delete=models.PROTECT,
        related_name='candidate_screens', verbose_name='当前阶段',
        null=True, blank=True,
    )
    screen_result = models.JSONField(
        default=dict, verbose_name='筛选结果',
        help_text='{decision, comment, ...}',
    )
    screened_by = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='screen_decisions', verbose_name='筛选人',
    )
    screened_at = models.DateTimeField(auto_now_add=True, verbose_name='筛选时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'candidate_screens'
        verbose_name = '候选人筛选记录'
        verbose_name_plural = verbose_name
        ordering = ['-screened_at']
        indexes = [
            models.Index(fields=['process', 'candidate']),
            models.Index(fields=['screened_by', 'screened_at']),
        ]

    def __str__(self):
        decision = self.screen_result.get('decision', 'N/A')
        return f'CandidateScreen[{self.candidate_id}] {decision}'



    objects = SoftDeleteManager()
    all_objects = models.Manager()
class CandidateRecommendation(SoftDeleteModel):
    """候选人推荐记录 — 审计+查询

    POST /api/v1/processes/{id}/batch-recommend/ 写入。
    设计依据: docs/PHASE2_DESIGN_2026-08-03.md §C.3.2
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    process = models.ForeignKey(
        RecruitmentProcess, on_delete=models.PROTECT,
        related_name='candidate_recommendations', verbose_name='所属流程',
    )
    candidate = models.ForeignKey(
        'candidate.Candidate', on_delete=models.PROTECT,
        related_name='recommendation_records', verbose_name='候选人',
    )
    reason = models.TextField(blank=True, verbose_name='推荐理由')
    recommender = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='candidate_recommendations', verbose_name='推荐人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='推荐时间')

    class Meta:
        db_table = 'candidate_recommendations'
        verbose_name = '候选人推荐记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['process', 'candidate']),
            models.Index(fields=['recommender', 'created_at']),
        ]

    def __str__(self):
        return f'CandidateRecommendation[{self.candidate_id}] by {self.recommender_id}'


    objects = SoftDeleteManager()
    all_objects = models.Manager()