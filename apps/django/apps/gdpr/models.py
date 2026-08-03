"""GDPR Models (PRD v4 §4.4)"""
import hashlib
import hmac
import secrets

from django.db import models
from django.utils import timezone
from datetime import timedelta

from apps.common.models import TimestampedModel
from nanoid import generate as nanoid_generate


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


class GDPRRequest(TimestampedModel):
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
