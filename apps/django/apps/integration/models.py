"""Integration Models (PRD v4 §14.4 外部系统集成)"""
from django.db import models
from nanoid import generate as nanoid_generate

from apps.common.models import SoftDeleteManager, SoftDeleteModel, TimestampedModel


def gen_id():
    return nanoid_generate(size=21)


class IntegrationType(models.TextChoices):
    MOKA = 'MOKA', '摩卡 HRIS'
    EMAIL = 'EMAIL', '邮件服务'
    WECOM = 'WECOM', '企业微信'
    SMS = 'SMS', '短信服务'
    BACKGROUND_CHECK = 'BACKGROUND_CHECK', '背调服务'
    PORTAL = 'PORTAL', '招聘门户'


class IntegrationConfig(TimestampedModel, SoftDeleteModel):
    """外部系统集成配置

    Fix 6: 新增 encrypted_secret 字段, 用 Fernet 加密敏感凭据.
    config JSON 保留为非敏感配置 (URL / 签名名 / 模板号 等).
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    type = models.CharField(max_length=32, choices=IntegrationType.choices, verbose_name='类型')
    provider = models.CharField(max_length=64, blank=True, default='', db_index=True, verbose_name='供应商代码', help_text='背调场景下区分多家供应商，如 quanjing/xinda/andun')
    name = models.CharField(max_length=100, verbose_name='名称')
    config = models.JSONField(default=dict, verbose_name='非敏感配置', help_text='API URL, 签名名, 模板号 等')
    encrypted_secret = models.TextField(blank=True, verbose_name='加密凭据 (Fernet)', help_text='JSON: {"corp_secret":"...", "access_key_secret":"..."} 加密后')
    field_mapping = models.JSONField(default=dict, verbose_name='字段映射')

    is_active = models.BooleanField(default=True, db_index=True, verbose_name='启用')
    # 是否系统已对接（决定「系统下单」可选范围；自主下单额外包含自主背调与所有供应商）
    is_system_integrated = models.BooleanField(default=True, db_index=True, verbose_name='系统已对接')
    # 背调展示元数据：交付效率/使用率排名与标签、套餐目录；前端未配置时优雅降级
    bg_metadata = models.JSONField(
        default=dict, blank=True, verbose_name='背调展示元数据',
        help_text='交付效率/使用率排名与标签、套餐目录；前端未配置时优雅降级',
    )
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='最后同步时间')

    class Meta:
        db_table = 'integration_configs'
        verbose_name = '集成配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'[{self.type}] {self.name}'



    objects = SoftDeleteManager()
    all_objects = models.Manager()
class IntegrationSyncLog(TimestampedModel, SoftDeleteModel):
    """集成同步日志"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    config = models.ForeignKey(
        IntegrationConfig, on_delete=models.CASCADE,
        related_name='sync_logs', verbose_name='配置',
    )
    sync_type = models.CharField(max_length=32, verbose_name='同步类型', help_text='USER_PULL/USER_PUSH/RESUME_PUSH/...')
    status = models.CharField(max_length=16, verbose_name='状态', help_text='SUCCESS/PARTIAL/FAILED')
    total_count = models.IntegerField(default=0, verbose_name='总数')
    success_count = models.IntegerField(default=0, verbose_name='成功数')
    failed_count = models.IntegerField(default=0, verbose_name='失败数')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    endpoint = models.CharField(max_length=255, blank=True, default='', verbose_name='接口路径')
    method = models.CharField(max_length=16, blank=True, default='', verbose_name='请求方法')
    direction = models.CharField(max_length=8, blank=True, default='', verbose_name='方向', help_text='OUT 出向 / IN 入向')
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name='耗时(ms)')
    # 2026-08-28 寇豆码: 回调入向新增字段
    # request_data 存完整回调体（便于审计/排障）；external_ref 存供应商单号（number）便于幂等与展示
    request_data = models.JSONField(null=True, blank=True, verbose_name='原始请求体', help_text='回调等入向请求的原始负载，便于审计与排障')
    external_ref = models.CharField(max_length=128, blank=True, default='', db_index=True, verbose_name='外部单号', help_text='供应商订单号/回执号(number)，便于幂等与展示')

    class Meta:
        db_table = 'integration_sync_logs'
        verbose_name = '集成同步日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            # 回调幂等查询 (config, sync_type, external_ref, status) 加速
            models.Index(
                fields=['config', 'sync_type', 'external_ref', 'status'],
                name='idx_synclog_cb_idem',
            ),
        ]



    objects = SoftDeleteManager()
    all_objects = models.Manager()
class BGOrderStatus(models.IntegerChoices):
    """背调订单状态机枚举（统一规范 §2.3，沿用现行 8 态 + 0 已受理）"""
    ACCEPTED = 0, '已受理/已下单'
    COMPLETED = 1, '已完成'
    PENDING_AUTH = 2, '待授权'
    IN_PROGRESS = 3, '背调中'
    AUTH_EXPIRED = 4, '授权过期'
    PENDING_PAYMENT = 5, '待支付'
    CANCELLED = 6, '已取消'
    STAGE_REPORT = 7, '阶段报告'
    AUTH_REVOKED = 8, '授权撤销'

    @classmethod
    def label_of(cls, value):
        try:
            return cls(value).label
        except ValueError:
            return ''


class BGChannel(models.TextChoices):
    """背调下单渠道（步骤式弹窗：自主背调 / 自主下单 / 系统下单）"""
    SELF = 'SELF', '自主背调'
    SELF_ORDER = 'SELF_ORDER', '自主下单'
    SYSTEM_ORDER = 'SYSTEM_ORDER', '系统下单'

    @classmethod
    def label_of(cls, value):
        try:
            return cls(value).label
        except ValueError:
            return ''


class BGRiskLevel(models.IntegerChoices):
    """背调风险等级（统一规范 §2.3）"""
    LOW = 1, '低风险'
    MID = 2, '中风险'
    HIGH = 3, '高风险'
    NONE = 4, '无风险'
    UNRATED = 9, '未评级'

    @classmethod
    def label_of(cls, value):
        try:
            return cls(value).label
        except ValueError:
            return ''


class BGResult(models.TextChoices):
    """背调结果（上传分支 HR 人工结论，独立于供应商 risk_level）。

    默认空串 '' 表示「未填」，以区别于 PENDING（待定）。
    """

    PASS = 'PASS', '通过'
    DOUBT = 'DOUBT', '存疑'
    FAIL = 'FAIL', '不通过'
    PENDING = 'PENDING', '待定'

    @classmethod
    def label_of(cls, value):
        try:
            return cls(value).label
        except ValueError:
            return ''


# 状态机合法转移表（供应商为权威来源，非合法转移仍落库但标记 is_legal_transition=False 供监控）
ALLOWED_ORDER_TRANSITIONS = {
    BGOrderStatus.ACCEPTED: {2, 3, 5, 6, 7, 8},
    BGOrderStatus.PENDING_AUTH: {3, 4, 8},
    BGOrderStatus.IN_PROGRESS: {1, 6, 7, 8},
    BGOrderStatus.PENDING_PAYMENT: {3, 6},
    BGOrderStatus.STAGE_REPORT: {1, 3, 6, 8},
    BGOrderStatus.COMPLETED: {6},
    BGOrderStatus.AUTH_EXPIRED: set(),
    BGOrderStatus.CANCELLED: set(),
    BGOrderStatus.AUTH_REVOKED: set(),
}


class BackgroundCheckOrder(TimestampedModel, SoftDeleteModel):
    """背调订单（状态机主体）。

    唯一键 (config, order_number)：order_number 为平台生成的背调订单全链路主键（规范 §2.2.3）。
    当前 status 由供应商回调驱动（apply_callback_to_order）；转移历史见 BackgroundCheckOrderEvent。
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    config = models.ForeignKey(
        IntegrationConfig, on_delete=models.CASCADE,
        related_name='bg_orders', verbose_name='供应商配置', null=True, blank=True,
    )
    # 下单渠道（步骤式弹窗）：SELF(自主背调) / SELF_ORDER(自主下单) / SYSTEM_ORDER(系统下单)
    channel = models.CharField(
        max_length=16, choices=BGChannel.choices, default=BGChannel.SYSTEM_ORDER,
        db_index=True, verbose_name='下单渠道',
    )
    # 订单备注 / 背调建议承载（无报告下单时填充背调建议；上传时承载回答）
    remark = models.TextField(blank=True, verbose_name='订单备注/背调建议')
    # 是否补充背调（待入职/补充场景）
    is_supplementary = models.BooleanField(default=False, db_index=True, verbose_name='是否补充背调')
    # 父订单（补充背调关联）
    parent_order_id = models.CharField(max_length=32, blank=True, default='', db_index=True, verbose_name='父订单ID')
    # 背调建议快照（按面试官）：[{interviewer, interviewer_name, suggestion, answer}]
    bg_suggestions = models.JSONField(default=list, blank=True, verbose_name='背调建议快照')
    order_number = models.CharField(max_length=64, verbose_name='订单号(number)', help_text='平台生成，全链路主键')
    candidate_id = models.CharField(max_length=64, blank=True, default='', db_index=True, verbose_name='候选人ID')
    candidate_name = models.CharField(max_length=64, blank=True, default='', verbose_name='候选人姓名')
    status = models.IntegerField(
        choices=BGOrderStatus.choices, default=BGOrderStatus.ACCEPTED, db_index=True, verbose_name='订单状态',
    )
    status_name = models.CharField(max_length=32, blank=True, default='', verbose_name='状态名称')
    risk_level = models.IntegerField(null=True, blank=True, verbose_name='风险等级', help_text='1低/2中/3高/4无/9未评级')
    report_url = models.CharField(max_length=512, blank=True, default='', verbose_name='报告地址')
    completion_time = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    latest_payload = models.JSONField(null=True, blank=True, verbose_name='最近一次回调/响应原始体')
    # 上传分支：套餐名称（冗余可读）/ 自主背调供应商（自由文本，无 FK）/ 背调时间 / 背调结果（人工结论）
    package_name = models.CharField(max_length=100, blank=True, default='', verbose_name='套餐名称')
    bg_provider = models.CharField(max_length=100, blank=True, default='', verbose_name='背调供应商')
    bg_time = models.DateTimeField(null=True, blank=True, verbose_name='背调时间')
    bg_result = models.CharField(
        max_length=16, blank=True, default='', choices=BGResult.choices, verbose_name='背调结果',
    )
    # 下单分支：是否可以联系候选人（null=未选）
    contactable = models.BooleanField(null=True, blank=True, verbose_name='是否可以联系候选人')
    # 背调人信息快照（不建 Candidate 新列，避免迁移扩散）
    subject_snapshot = models.JSONField(default=dict, blank=True, verbose_name='背调人信息快照')

    class Meta:
        db_table = 'background_check_orders'
        verbose_name = '背调订单'
        verbose_name_plural = verbose_name
        unique_together = [('config', 'order_number')]
        ordering = ['-created_at']

    def __str__(self):
        return f'BGOrder[{self.order_number}] {self.get_status_display()}'

    @property
    def status_label(self):
        return BGOrderStatus.label_of(self.status)

    @property
    def channel_label(self):
        return BGChannel.label_of(self.channel)

    @property
    def risk_label(self):
        return BGRiskLevel.label_of(self.risk_level) if self.risk_level is not None else ''



    objects = SoftDeleteManager()
    all_objects = models.Manager()
class BackgroundCheckOrderEvent(TimestampedModel, SoftDeleteModel):
    """背调订单状态机转移历史（append-only）。

    每次状态变更（创建/回调/取消）记一条，记录 from→to、是否合法转移、来源、原始 payload，
    并关联触发它的同步审计日志 IntegrationSyncLog。这是订单状态机的审计核心。
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    order = models.ForeignKey(
        BackgroundCheckOrder, on_delete=models.CASCADE,
        related_name='events', verbose_name='订单',
    )
    config = models.ForeignKey(
        IntegrationConfig, on_delete=models.CASCADE,
        related_name='bg_order_events', verbose_name='供应商配置',
    )
    from_status = models.IntegerField(null=True, blank=True, verbose_name='原状态')
    to_status = models.IntegerField(verbose_name='新状态')
    risk_level = models.IntegerField(null=True, blank=True, verbose_name='风险等级')
    report_url = models.CharField(max_length=512, blank=True, default='', verbose_name='报告地址')
    completion_time = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    source = models.CharField(max_length=16, verbose_name='来源', help_text='CREATE/CALLBACK/CANCEL')
    is_legal_transition = models.BooleanField(default=True, verbose_name='是否合法转移')
    raw_payload = models.JSONField(null=True, blank=True, verbose_name='原始负载')
    sync_log = models.ForeignKey(
        IntegrationSyncLog, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bg_order_events', verbose_name='关联同步日志',
    )

    class Meta:
        db_table = 'background_check_order_events'
        verbose_name = '背调订单事件'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'BGEvt[{self.order_id}] {self.from_status}->{self.to_status} ({self.source})'


    objects = SoftDeleteManager()
    all_objects = models.Manager()