"""Demand Models (PRD v4 §14.1)"""
from django.db import models
from django_fsm import FSMField, transition
from apps.common.models import FullAuditModel
from apps.reason_library.models import RECRUIT_TYPE_CHOICES, RecruitType
from apps.process.models import RecruitmentProcess
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class DemandState(models.TextChoices):
    DRAFT = 'DRAFT', '草稿'
    PENDING = 'PENDING', '待审批'
    REJECTED = 'REJECTED', '已驳回'
    APPROVED = 'APPROVED', '已通过'
    RECRUITING = 'RECRUITING', '招聘中'
    PAUSED = 'PAUSED', '已暂停'
    COMPLETED = 'COMPLETED', '已完成'
    CANCELLED = 'CANCELLED', '已取消'


class Demand(FullAuditModel):
    """招聘需求"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    # 招聘类型硬分区 (social/campus): 社会/校园招聘数据相互隔离, 历史数据默认 social.
    recruit_type = models.CharField(
        max_length=16, choices=RECRUIT_TYPE_CHOICES, default=RecruitType.SOCIAL.value,
        db_index=True, verbose_name='招聘类型',
    )
    code = models.CharField(max_length=20, unique=True, verbose_name='需求编号')

    title = models.CharField(max_length=200, verbose_name='需求标题')
    department = models.ForeignKey(
        'core.Department', on_delete=models.PROTECT,
        related_name='demands', verbose_name='需求部门',
    )
    requested_by = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='requested_demands', verbose_name='需求提出人',
    )
    hr = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='assigned_demands', verbose_name='负责HR',
    )

    headcount = models.IntegerField(verbose_name='需求人数')
    filled_count = models.IntegerField(default=0, verbose_name='已招人数')
    level = models.CharField(max_length=50, blank=True, verbose_name='职级')
    position_title = models.CharField(max_length=100, blank=True, verbose_name='职务')

    process = models.ForeignKey(
        RecruitmentProcess, on_delete=models.PROTECT,
        related_name='demands', verbose_name='招聘流程',
    )
    # T9/G2：与 RecruitmentProcess.current_version（default 'V1.0'）以及 service 层
    # 实际写入值（demand/services.py:78 写 process.current_version，带 V 前缀）对齐。
    # 旧 default '1.0' 与真实写入自相矛盾。
    process_version = models.CharField(max_length=20, default='V1.0', verbose_name='流程版本')

    jd = models.TextField(blank=True, verbose_name='JD')
    requirements = models.TextField(blank=True, verbose_name='任职要求')

    state = FSMField(
        default=DemandState.DRAFT, db_index=True,
        protected=True, verbose_name='需求状态',
    )

    priority = models.CharField(
        max_length=8, default='P1',
        choices=[('P0', 'P0-高'), ('P1', 'P1-中'), ('P2', 'P2-低')],
        verbose_name='优先级',
    )

    # TODO-B 选项①：恢复前端 demandType 对应的后端字段（社招 / 校招）。
    # 此前模型无 demand_type，前端 DemandList.vue 的 demandType（SOCIAL/CAMPUS）
    # 一直是"发送了但后端不收、读取了但后端不返回"的脱节状态：列表/详情页
    # 一律按 undefined 渲染成「校招」，表单选中「社招」提交后也被静默丢弃。
    demand_type = models.CharField(
        max_length=10, default='SOCIAL',
        choices=[('SOCIAL', '社会招聘'), ('CAMPUS', '校园招聘')],
        verbose_name='需求类型',
    )

    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='提交时间')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='审批通过时间')

    class Meta:
        db_table = 'demands'
        verbose_name = '招聘需求'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['state', 'department']),
            models.Index(fields=['hr', 'state']),
        ]

    def __str__(self):
        return f'{self.code} {self.title}'

    @transition(field=state, source=DemandState.DRAFT, target=DemandState.PENDING)
    def submit(self):
        from django.utils import timezone
        self.submitted_at = timezone.now()

    @transition(field=state, source=DemandState.PENDING, target=DemandState.APPROVED)
    def approve(self):
        from django.utils import timezone
        self.approved_at = timezone.now()

    @transition(field=state, source=DemandState.PENDING, target=DemandState.REJECTED)
    def reject(self):
        pass

    @transition(field=state, source=DemandState.APPROVED, target=DemandState.RECRUITING)
    def start_recruiting(self):
        pass

    @transition(field=state, source=DemandState.RECRUITING, target=DemandState.PAUSED)
    def pause(self):
        pass

    @transition(field=state, source=DemandState.PAUSED, target=DemandState.RECRUITING)
    def resume(self):
        pass

    @transition(field=state, source='*', target=DemandState.COMPLETED)
    def complete(self):
        pass

    @transition(field=state, source='*', target=DemandState.CANCELLED)
    def cancel(self):
        pass


# 2026-06-29 花无缺: pytest 的 UnorderedObjectListWarning 来自 Demand 缺 ordering.
#   父类 FullAuditModel.Meta 已经声明, Django 不允许子类重声明. 用两种方式都行:
#   a) 父类加 ordering (影响所有子类, 30+ 模型, 风险大)
#   b) 子类 meta 修: 通过 metaclass Options 间接注入. 但 Django 不支持.
#   c) 在 view 的 queryset 里显式 .order_by() (best practice)
#   这里选 (c): Demand 的 list endpoint 显式 .order_by('-created_at'),
#   比改 model 影响更小. (model.Meta.ordering 留空)
class DemandApproval(FullAuditModel):
    """需求审批记录"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    demand = models.ForeignKey(
        Demand, on_delete=models.CASCADE,
        related_name='approvals', verbose_name='需求',
    )
    approver = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='+', verbose_name='审批人',
    )
    level = models.IntegerField(verbose_name='审批层级')
    result = models.CharField(
        max_length=16,
        choices=[('PENDING', '待审批'), ('APPROVED', '通过'), ('REJECTED', '驳回')],
        default='PENDING', verbose_name='审批结果',
    )
    comment = models.TextField(blank=True, verbose_name='审批意见')

    class Meta:
        db_table = 'demand_approvals'
        verbose_name = '需求审批'
        verbose_name_plural = verbose_name
        ordering = ['demand', 'level']


class DemandSetting(FullAuditModel):
    """招聘需求全局配置（单体 JSON 存储）—— FE DemandConfig.vue 调用

    key 固定 'demand'，config 为自由 JSON dict，与前端 formData 同构
    （demandMode / grabModeEnabled / profileFieldRules / salaryUnit ...）。
    camel-case 解析器会把入参 key snake 化、渲染器再 camel 化回来，
    整体 round-trip 安全（form 仅扁平 string/bool/list 字段，无嵌套 dict）。
    """

    key = models.CharField(max_length=64, unique=True, default='demand', verbose_name='配置键')
    config = models.JSONField(default=dict, blank=True, verbose_name='配置内容')

    class Meta:
        db_table = 'demand_settings'
        verbose_name = '招聘需求配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'DemandSetting({self.key})'
