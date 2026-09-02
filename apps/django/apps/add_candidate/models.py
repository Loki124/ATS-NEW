"""Add Candidate V2 Models

本模块提供简历解析任务追踪的 ParseJob model（Phase 2 Task 2 引入）。
- apps.candidate.models.Candidate
- apps.application.models.Application
- apps.talent_pool.models.TalentPoolEntry
- apps.position.models.Position
"""
from django.db import models
from apps.common.models import SoftDeleteModel, SoftDeleteManager


class ParseJob(SoftDeleteModel):
    """简历解析任务（上传后由 Celery 处理）"""
    STATUS_CHOICES = [
        ('processing', '处理中'),
        ('done', '完成'),
        ('failed', '失败'),
    ]
    PHASE_CHOICES = [
        ('uploading', '上传中'),
        ('parsing', '解析中'),
        ('checking', '查重中'),
    ]

    job_id = models.CharField(max_length=32, unique=True, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='processing')
    phase = models.CharField(max_length=16, choices=PHASE_CHOICES, null=True, blank=True)
    progress = models.IntegerField(default=0)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=512)
    file_size = models.IntegerField()
    error = models.CharField(max_length=64, null=True, blank=True)
    parsed_data = models.JSONField(null=True, blank=True)
    duplicate_data = models.JSONField(null=True, blank=True)
    draft_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    actor = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'add_candidate_parsejob'
        ordering = ['-created_at']


    objects = SoftDeleteManager()
    all_objects = models.Manager()