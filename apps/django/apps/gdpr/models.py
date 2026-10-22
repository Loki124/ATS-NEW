"""GDPR Models (PRD v4 §4.4)"""
import hashlib

from django.db import models
from django.utils import timezone
from nanoid import generate as nanoid_generate

from apps.common.models import SoftDeleteManager, SoftDeleteModel, TimestampedModel


def gen_id():
    return nanoid_generate(size=21)


# 2026-08-03 S2: 验证码 hash 化 + 加 expiration + attempts 防爆破
def hash_verification_code(code: str) -> str:
    """Hash GDPR 验证码. SHA-256 (固定长度 64 字符 hex).

    为什么不加 salt: GDPR 验证码是 6 位数字, 攻击者拿到 hash 表反查成本极低;
    但加盐会让候选人自己提供的 code 跟存储对不上 (候选人没存 salt). 所以:
    - 验证码足够短 (6-10 位) + 一次性 + 短过期 (15 min) + 限制 attempts (5 次) → 综合防护
    - 不加 salt (保持候选人能自验)
    """
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


# GDPR 验证码策略常量
VERIFICATION_CODE_LENGTH = 8          # 候选人生成 8 位 hex (32 bit 熵, 2^32 = 4.3B 空间)
VERIFICATION_CODE_TTL_MINUTES = 15   # 15 分钟过期
VERIFICATION_MAX_ATTEMPTS = 5        # 5 次错误锁定

# 导出件一次性下载 token 有效期 (分钟)。超期即拒, 与 token 单次消费共同构成"一次性"。
EXPORT_TOKEN_TTL_MINUTES = 30


class GDPRRequestType(models.TextChoices):
    FORGET = 'FORGET', '被遗忘权（删除）'
    EXPORT = 'EXPORT', '数据导出'
    RECTIFY = 'RECTIFY', '数据更正'


class GDPRRequestStatus(models.TextChoices):
    PENDING = 'PENDING', '待验证'  # 2026-08-03: 重命名语义, 等候选人 verify
    AWAITING_VERIFICATION = 'AWAITING_VERIFICATION', '待候选人验证'  # 2026-08-03: 候选人生成 code 但未 verify
    PROCESSING = 'PROCESSING', '处理中'
    COMPLETED = 'COMPLETED', '已完成'
    REJECTED = 'REJECTED', '已拒绝'
    EXPIRED = 'EXPIRED', '已过期'  # 2026-08-03: 验证码过期自动转
    LOCKED = 'LOCKED', '已锁定'  # 2026-08-03: attempts 超阈值锁定


class GDPRRequest(TimestampedModel, SoftDeleteModel):
    """GDPR 请求"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    candidate = models.ForeignKey(
        'candidate.Candidate', on_delete=models.PROTECT,
        related_name='gdpr_requests', verbose_name='候选人',
    )
    request_type = models.CharField(max_length=16, choices=GDPRRequestType.choices, verbose_name='请求类型')
    status = models.CharField(
        max_length=24, choices=GDPRRequestStatus.choices,
        default=GDPRRequestStatus.AWAITING_VERIFICATION, db_index=True, verbose_name='状态',
    )

    # 处理
    processed_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='处理人',
    )
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')
    result = models.TextField(blank=True, verbose_name='处理结果')
    reject_reason = models.TextField(blank=True, verbose_name='拒绝原因')

    # 候选人提交信息
    submitted_email = models.EmailField(blank=True, verbose_name='提交邮箱')

    # 2026-08-03 S2: 验证码字段全部 hash 化
    # 旧字段 verification_code (明文 CharField 10) 已废弃, 通过 0002 migration 删除
    # 新增:
    verification_code_hash = models.CharField(
        max_length=128, blank=True, db_index=True, verbose_name='验证码 SHA-256',
    )
    verification_code_expires_at = models.DateTimeField(
        null=True, blank=True, verbose_name='验证码过期时间',
    )
    verification_code_attempts = models.IntegerField(
        default=0, verbose_name='错误尝试次数',
    )
    verified_at = models.DateTimeField(
        null=True, blank=True, verbose_name='候选人验证通过时间',
    )

    class Meta:
        db_table = 'gdpr_requests'
        verbose_name = 'GDPR 请求'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['candidate', 'request_type']),
            models.Index(fields=['verification_code_expires_at']),
        ]

    def is_expired(self) -> bool:
        return (
            self.verification_code_expires_at is not None
            and self.verification_code_expires_at < timezone.now()
        )

    def is_locked(self) -> bool:
        return self.verification_code_attempts >= VERIFICATION_MAX_ATTEMPTS

    def __str__(self):
        return f'GDPRRequest({self.id}, {self.request_type}, {self.status})'


    objects = SoftDeleteManager()
    all_objects = models.Manager()


class GDPRExportArtifact(TimestampedModel):
    """GDPR 导出件 (2026-10-21 · 整改卡 C1)

    **为什么要有这张表**: 改造前 `GdprService.approve_and_export` 把含 PII 明文的
    `export_data` 直接 f-string 进 `GDPRRequest.result` 列, 而 `result` 又在
    `GDPRRequestSerializer.fields` 里 → 候选人姓名/手机号/邮箱/身份证号**明文落库**,
    并且任何能读该接口的超管 API 调用都能原样取回。

    改造后:
    - 明文只在内存里组装一次 → Fernet 加密后落到本表 (与 `id_card_no` 同一套密钥体系);
    - 通过**一次性 token** 下载 → 下载成功即擦除密文 + 落 `downloaded_at`, token 不可复用;
    - `expires_at` 到期即拒 (默认 `EXPORT_TOKEN_TTL_MINUTES`);
    - 下载动作写审计日志 (只记 id, 不记 PII);
    - `GDPRRequest.result` 只留**摘要**, 不含任何 PII。

    安全属性一句话: **PII 明文从不进 `gdpr_requests` 表, 也从不随请求详情接口返回**。
    """

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    request = models.ForeignKey(
        'gdpr.GDPRRequest', on_delete=models.CASCADE,
        related_name='export_artifacts', verbose_name='GDPR 请求',
    )
    # Fernet 密文; 下载成功后被擦除为空串
    payload = models.TextField(verbose_name='导出内容 (Fernet 密文)')
    # 一次性下载 token (urlsafe base64, 32 字节熵)
    token = models.CharField(max_length=64, unique=True, db_index=True, verbose_name='一次性下载 token')
    expires_at = models.DateTimeField(db_index=True, verbose_name='过期时间')
    downloaded_at = models.DateTimeField(null=True, blank=True, verbose_name='首次下载时间')
    download_count = models.IntegerField(default=0, verbose_name='下载次数')
    created_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='创建人',
    )

    class Meta:
        db_table = 'gdpr_export_artifacts'
        verbose_name = 'GDPR 导出件'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request', 'expires_at']),
        ]

    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at < timezone.now()

    def is_consumed(self) -> bool:
        """已下载过 (一次性语义) 或密文已被擦除。"""
        return self.downloaded_at is not None or not self.payload

    def __str__(self):
        return f'GDPRExportArtifact({self.id}, request={self.request_id}, consumed={self.is_consumed()})'