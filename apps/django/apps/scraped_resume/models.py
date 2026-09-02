"""scraped_resume models (Phase 2 T02: 落地最小 ScrapedResume model).

历史:
- 2026-06-29: 0-model 占位 (URL + viewset + serializer 都就位但 model 空)
- 2026-08-04 (T02): 0-model 占位导致 ResumeList.vue 等前端拿不到任何数据,
  本次落地最小 model 让 URL 不再是 500/空列表.

本 model 仅满足以下约束 (本任务范围):
1. 让 /api/v1/scraped-resumes/ 注册后能 GET 真实数据 (空表返 []).
2. 让 ScrapedResumeViewSet.detail(scrape/import_to) 不抛 AttributeError.
3. 不实现完整业务 (list/create/import 真实逻辑是 T06 任务).

字段集决策 (依据 PHASE2_DESIGN_2026-08-03.md §C.4 / T02.5):
- source_url: 从哪个 URL 抓到, 排查 + 去重依据
- source_platform: 哪个平台 (拉勾/BOSS/智联), Phase 3 枚举字典化
- raw_content: 抓回的原始 HTML / 文本, 解析失败可回看
- parsed_content: 结构化解析结果, JSONField 形态灵活
- candidate: 解析后映射到的候选人 (空 = 未匹配, 后续 import 走 T06 逻辑)
- extra: Phase 3 扩展字段 (当前 scraper_job_name / status 等可入此)
  — 强制 default=dict 避免 NOT NULL 问题

完整字段 (status=枚举 / scraper_job_name / scraped_at / import_error 等)
将由 T06 (G30 任务) 落地, 这里留 stub 文档指引.
"""
from django.db import models
from apps.common.models import SoftDeleteModel, SoftDeleteManager


class ScrapedResume(SoftDeleteModel):
    """一条抓回的简历原始记录。

    生命周期 (T06 落地):
        PENDING → SCRAPED → IMPORTED / DUPLICATE / FAILED
    """

    # === 主键: 默认 BigAutoField, 显式写出便于 later migration introspect ===
    id = models.BigAutoField(primary_key=True)

    # === 数据来源 ===
    source_url = models.URLField(
        max_length=1024,
        help_text='原始抓取 URL, 用于排查 + 去重',
    )
    source_platform = models.CharField(
        max_length=64,
        help_text='平台标识 (拉勾/BOSS/智联/...) - Phase 3 改为枚举外键',
    )

    # === 内容 ===
    raw_content = models.TextField(
        help_text='抓回的原始 HTML / 文本, 解析失败时回看',
    )
    parsed_content = models.JSONField(
        default=dict,
        blank=True,
        help_text='结构化解析结果 (姓名/电话/邮箱/工作经历等), JSON 形态',
    )

    # === 关联 ===
    candidate = models.ForeignKey(
        'candidate.Candidate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scraped_sources',
        help_text='解析后映射到的候选人 (NULL = 未匹配, 待 T06 落地)',
    )

    # === 时间戳 ===
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='入库时间 (抓取完成入库点)',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='字段最近修改时间',
    )

    # === 扩展 ===
    extra = models.JSONField(
        default=dict,
        blank=True,
        help_text='Phase 3 扩展字段: status(scraper_state) / scraper_job_name / '
                  'import_error / retry_count 等暂存此处',
    )

    class Meta:
        verbose_name = '抓取简历 (G30 stub)'
        verbose_name_plural = verbose_name
        db_table = 'scraped_resumes'
        indexes = [
            models.Index(fields=['source_platform', '-created_at'], name='idx_scraped_resume_lookup'),
        ]
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'ScrapedResume<{self.id} {self.source_platform} {self.source_url[:60]}>'


    objects = SoftDeleteManager()
    all_objects = models.Manager()