"""Resume Flow Models — 审批流

设计依据: docs/PHASE2_DESIGN_2026-08-03.md §C.4

关键决策:
- nodes 用 JSONField 而非独立 ApprovalNode model — 访问模式匹配（按 flow_id 拉列表）
- approverId 存 snapshot 非 FK — 审批人离职/转岗不影响历史
- status + current_node_id 两字段加 service guard，不引入 FSM 库
"""
from django.db import models
from apps.common.models import SoftDeleteModel, SoftDeleteManager
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class ApprovalFlow(SoftDeleteModel):
    """审批流

    前端契约 (SpecialApproval.vue:162-184):
    - GET /resumes/approval-flows 返回 approvalFlows 数组
    - canApprove() 解析 nodes 找当前节点, 比对 currentNode.approverId 与 localStorage.userId
    """
    STATUS_CHOICES = [
        ('PENDING', '待审批'),
        ('IN_PROGRESS', '审批中'),
        ('APPROVED', '已通过'),
        ('REJECTED', '已驳回'),
        ('CANCELLED', '已取消'),
    ]

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    candidate = models.ForeignKey(
        'candidate.Candidate', on_delete=models.PROTECT,
        related_name='approval_flows', verbose_name='候选人',
    )
    resume_id = models.CharField(
        max_length=64, blank=True, db_index=True,
        verbose_name='简历ID', help_text='关联的简历标识',
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default='PENDING',
        db_index=True, verbose_name='状态',
    )
    current_node_id = models.CharField(
        max_length=32, blank=True, verbose_name='当前节点ID',
    )
    nodes = models.JSONField(
        default=list, verbose_name='审批节点',
        help_text='[{nodeId, role, approverId?, decidedAt?, comment?}]',
    )
    created_by = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='created_approval_flows', verbose_name='创建人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'approval_flows'
        verbose_name = '审批流'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['candidate', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'ApprovalFlow[{self.id}] candidate={self.candidate_id} status={self.status}'

    objects = SoftDeleteManager()
    all_objects = models.Manager()


class ApprovalFlowHistory(SoftDeleteModel):
    """审批流操作历史 — 自动审计"""
    ACTION_CHOICES = [
        ('CREATED', '创建'),
        ('APPROVED', '批准'),
        ('REJECTED', '驳回'),
        ('DELEGATED', '转交'),
        ('CANCELLED', '取消'),
    ]

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    flow = models.ForeignKey(
        ApprovalFlow, on_delete=models.CASCADE,
        related_name='histories', verbose_name='审批流',
    )
    action = models.CharField(
        max_length=16, choices=ACTION_CHOICES, verbose_name='操作',
    )
    from_node = models.CharField(
        max_length=32, blank=True, verbose_name='来源节点ID',
    )
    to_node = models.CharField(
        max_length=32, blank=True, verbose_name='目标节点ID',
    )
    operated_by = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='approval_flow_histories', verbose_name='操作人',
    )
    comment = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')

    class Meta:
        db_table = 'approval_flow_histories'
        verbose_name = '审批流历史'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['flow', 'created_at']),
        ]

    def __str__(self):
        return f'ApprovalFlowHistory[{self.action}] flow={self.flow_id}'

    objects = SoftDeleteManager()
    all_objects = models.Manager()
