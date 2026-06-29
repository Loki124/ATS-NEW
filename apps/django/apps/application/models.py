"""Application Models (PRD v4 §6.1, §14.3)

申请/投递 - 候选人在某个职位上的申请记录
"""
from django.db import models
from django_fsm import FSMField, transition
from apps.common.models import FullAuditModel
from apps.candidate.models import Candidate
from apps.process.models import RecruitmentProcess, ProcessStageLink, RecruitmentStage
from apps.position.models import Position
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class ApplicationState(models.TextChoices):
    PENDING = 'PENDING', '待启动'
    ACTIVE = 'ACTIVE', '流程中'
    PAUSED = 'PAUSED', '流程暂停'
    OFFER_SENT = 'OFFER_SENT', '已发Offer'
    OFFER_ACCEPTED = 'OFFER_ACCEPTED', '已接受Offer'
    ONBOARDED = 'ONBOARDED', '已入职'
    REJECTED = 'REJECTED', '本流程未通过'
    WITHDRAWN = 'WITHDRAWN', '候选人主动撤回'
    TIMEOUT = 'TIMEOUT', '超时归档'


class Application(FullAuditModel):
    """申请 - 候选人在某个职位的申请记录

    关键设计：
    - workflow_version: 创建时的流程版本（版本冻结，PRD BR-102）
    - current_link: 当前所在的流程-阶段关联
    - state: 申请级状态机
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    code = models.CharField(max_length=20, unique=True, verbose_name='申请编号')

    candidate = models.ForeignKey(
        Candidate, on_delete=models.PROTECT,
        related_name='applications', verbose_name='候选人',
    )
    position = models.ForeignKey(
        Position, on_delete=models.PROTECT,
        related_name='applications', verbose_name='职位',
    )
    process = models.ForeignKey(
        RecruitmentProcess, on_delete=models.PROTECT,
        related_name='applications', verbose_name='使用的流程',
    )
    workflow_version = models.CharField(max_length=20, verbose_name='流程版本', help_text='创建时的版本（冻结）')

    # 当前所在阶段
    current_link = models.ForeignKey(
        ProcessStageLink, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name='当前阶段关联',
    )
    current_stage = models.ForeignKey(
        RecruitmentStage, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name='当前阶段',
    )

    # 状态机
    state = FSMField(
        default=ApplicationState.PENDING, db_index=True,
        protected=True, verbose_name='申请状态',
    )

    # 阶段限时信息
    time_limit_rule_id = models.CharField(max_length=32, null=True, blank=True, verbose_name='匹配的限时规则ID')
    total_time_limit_days = models.IntegerField(null=True, blank=True, verbose_name='总限时天数')
    stage_entered_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='当前阶段进入时间')
    stage_deadline = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='阶段截止时间')

    # 抢单模式专用
    is_grabbed = models.BooleanField(default=False, verbose_name='是否已被认领')
    grabbed_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name='认领人',
    )
    grabbed_at = models.DateTimeField(null=True, blank=True, verbose_name='认领时间')

    # 审计
    last_advanced_at = models.DateTimeField(null=True, blank=True, verbose_name='最后推进时间')

    class Meta:
        db_table = 'applications'
        verbose_name = '申请'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['candidate', 'position']),
            models.Index(fields=['state', 'current_stage']),
            models.Index(fields=['stage_deadline']),
        ]

    def __str__(self):
        return f'{self.code} {self.candidate.name} @ {self.position.title}'

    @transition(field=state, source=ApplicationState.PENDING, target=ApplicationState.ACTIVE)
    def start(self):
        """启动申请"""
        from django.utils import timezone
        self.last_advanced_at = timezone.now()

    @transition(field=state, source=ApplicationState.ACTIVE, target=ApplicationState.PAUSED)
    def pause(self):
        """暂停"""
        pass

    @transition(field=state, source=ApplicationState.PAUSED, target=ApplicationState.ACTIVE)
    def resume(self):
        """恢复"""
        pass

    @transition(field=state, source=ApplicationState.ACTIVE, target=ApplicationState.OFFER_SENT)
    def send_offer_state(self):
        """标记为已发 Offer"""
        pass

    @transition(field=state, source=ApplicationState.OFFER_SENT, target=ApplicationState.OFFER_ACCEPTED)
    def accept_offer(self):
        """候选人接受 Offer"""
        pass

    @transition(field=state, source=ApplicationState.OFFER_ACCEPTED, target=ApplicationState.ONBOARDED)
    def mark_onboarded(self):
        """标记入职完成"""
        pass

    @transition(field=state, source=[ApplicationState.ACTIVE, ApplicationState.PAUSED], target=ApplicationState.REJECTED)
    def mark_rejected(self):
        """本流程未通过"""
        pass


class ApplicationStageRecord(FullAuditModel):
    """申请-阶段记录 - 候选人在每个阶段的历史（PRD §6.2, §13.1）

    软回退（PRD §6.3 规则 1）：保留所有历史记录
    """
    class StageState(models.TextChoices):
        NOT_STARTED = 'NOT_STARTED', '未开始'
        PENDING = 'PENDING', '待处理'
        TO_BE_SCHEDULED = 'TO_BE_SCHEDULED', '待安排'
        PROCESSING = 'PROCESSING', '处理中'
        PASSED = 'PASSED', '已通过'
        FAILED = 'FAILED', '未通过'
        SKIPPED = 'SKIPPED', '已跳过'
        REJECTED = 'REJECTED', '已回退'
        TIMEOUT = 'TIMEOUT', '超时'
        ARCHIVED = 'ARCHIVED', '已归档'

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE,
        related_name='stage_records', verbose_name='申请',
    )
    link = models.ForeignKey(
        ProcessStageLink, on_delete=models.PROTECT,
        related_name='application_records', verbose_name='流程-阶段关联',
    )
    stage = models.ForeignKey(
        RecruitmentStage, on_delete=models.PROTECT,
        related_name='+', verbose_name='阶段',
    )

    state = models.CharField(
        max_length=20, choices=StageState.choices,
        default=StageState.NOT_STARTED, db_index=True, verbose_name='阶段状态',
    )

    # 时间
    entered_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='进入时间')
    exited_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='离开时间')
    duration_days = models.IntegerField(null=True, blank=True, verbose_name='停留时长（天）')

    # 限时（PRD v4 §11.5 + §13.1）
    time_limit_rule_id = models.CharField(max_length=32, null=True, blank=True, verbose_name='匹配限时规则ID')
    total_time_limit_days = models.IntegerField(null=True, blank=True, verbose_name='总限时天数')
    deadline = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='阶段截止时间')

    # 处理人
    current_handlers = models.JSONField(default=list, verbose_name='当前处理人', help_text='list of userId')
    auto_promoted = models.BooleanField(default=False, verbose_name='是否自动推进')
    automation_rule_id = models.CharField(max_length=32, null=True, blank=True, verbose_name='触发的规则ID')

    # 备注/评价
    note = models.TextField(blank=True, verbose_name='备注')

    class Meta:
        db_table = 'application_stage_records'
        verbose_name = '申请阶段记录'
        verbose_name_plural = verbose_name
        ordering = ['application', 'entered_at']
        indexes = [
            models.Index(fields=['application', 'state']),
            models.Index(fields=['stage', 'state']),
            models.Index(fields=['deadline']),
        ]

    def __str__(self):
        return f'Record[{self.application.code} / {self.stage.name}] {self.state}'


class ApplicationHistory(FullAuditModel):
    """申请操作历史 - 所有写操作审计"""
    class ActionType(models.TextChoices):
        CREATED = 'CREATED', '创建'
        ADVANCED = 'ADVANCED', '推进'
        REJECTED = 'REJECTED', '回退'
        SKIPPED = 'SKIPPED', '跳过'
        PAUSED = 'PAUSED', '暂停'
        RESUMED = 'RESUMED', '恢复'
        OFFER_SENT = 'OFFER_SENT', '发送Offer'
        GRABBED = 'GRABBED', '抢单'
        TIMEOUT = 'TIMEOUT', '超时'
        UPGRADE_VERSION = 'UPGRADE_VERSION', '升版本'
        AUTO = 'AUTO', '自动操作'

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE,
        related_name='histories', verbose_name='申请',
    )

    action = models.CharField(max_length=32, choices=ActionType.choices, verbose_name='操作类型')
    from_stage = models.ForeignKey(
        RecruitmentStage, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name='来源阶段',
    )
    to_stage = models.ForeignKey(
        RecruitmentStage, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name='目标阶段',
    )

    detail = models.JSONField(default=dict, blank=True, verbose_name='详情')
    operator = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='操作人',
    )
    is_auto = models.BooleanField(default=False, verbose_name='是否自动')

    class Meta:
        db_table = 'application_histories'
        verbose_name = '申请操作历史'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]
