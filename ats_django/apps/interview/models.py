"""Interview Models (PRD v4 §14.5 面试)"""
from django.db import models
from apps.common.models import FullAuditModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class InterviewFormat(models.TextChoices):
    SINGLE = 'SINGLE', '单面'
    JOINT = 'JOINT', '联合面试'
    COMPREHENSIVE = 'COMPREHENSIVE', '综合面试'
    VIDEO = 'VIDEO', '视频面试'
    PHONE = 'PHONE', '电话面试'


class InterviewStatus(models.TextChoices):
    SCHEDULED = 'SCHEDULED', '已安排'
    IN_PROGRESS = 'IN_PROGRESS', '进行中'
    COMPLETED = 'COMPLETED', '已完成'
    CANCELLED = 'CANCELLED', '已取消'
    NO_SHOW = 'NO_SHOW', '候选人未到场'


class Interview(FullAuditModel):
    """面试"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    code = models.CharField(max_length=20, unique=True, verbose_name='面试编号')

    application = models.ForeignKey(
        'application.Application', on_delete=models.CASCADE,
        related_name='interviews', verbose_name='申请',
    )
    stage_record = models.ForeignKey(
        'application.ApplicationStageRecord', on_delete=models.CASCADE,
        related_name='interviews', verbose_name='阶段记录',
    )

    round_number = models.IntegerField(default=1, verbose_name='轮次')
    format = models.CharField(max_length=16, choices=InterviewFormat.choices, default=InterviewFormat.SINGLE, verbose_name='形式')

    scheduled_at = models.DateTimeField(db_index=True, verbose_name='安排时间')
    duration_minutes = models.IntegerField(default=60, verbose_name='时长（分钟）')
    location = models.CharField(max_length=200, blank=True, verbose_name='地点')
    meeting_url = models.URLField(max_length=500, blank=True, verbose_name='视频链接')

    interviewers = models.ManyToManyField(
        'core.User', related_name='interview_assignments',
        verbose_name='面试官',
    )

    status = models.CharField(
        max_length=16, choices=InterviewStatus.choices,
        default=InterviewStatus.SCHEDULED, db_index=True, verbose_name='面试状态',
    )

    class Meta:
        db_table = 'interviews'
        verbose_name = '面试'
        verbose_name_plural = verbose_name
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['application', 'scheduled_at']),
        ]

    def __str__(self):
        return f'Interview[{self.code}] @ {self.scheduled_at}'


class InterviewEvaluation(FullAuditModel):
    """面试评价"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    interview = models.ForeignKey(
        Interview, on_delete=models.CASCADE,
        related_name='evaluations', verbose_name='面试',
    )
    interviewer = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='+', verbose_name='面试官',
    )

    # 评分维度（JSON 存储灵活评分项）
    scores = models.JSONField(default=dict, verbose_name='评分维度', help_text='{"专业能力": 4, "沟通能力": 5}')

    overall_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, verbose_name='综合评分')
    recommendation = models.CharField(max_length=32, verbose_name='推荐结果',
        help_text='STRONGLY_RECOMMEND/RECOMMEND/NEUTRAL/NOT_RECOMMEND/STRONGLY_NOT_RECOMMEND')

    comment = models.TextField(verbose_name='评语', help_text='限 1000 字')

    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='提交时间')

    class Meta:
        db_table = 'interview_evaluations'
        verbose_name = '面试评价'
        verbose_name_plural = verbose_name
        unique_together = [('interview', 'interviewer')]
