"""注册审核模型 (自注册 → 邮件验证码 → 管理员审核 → 激活登录).

安全范式 (与 gdpr 验证码一致):
- 验证码只存 SHA-256 hash, 绝不存明文.
- 15 分钟过期, 5 次错误锁定.
- 注册即建 User(is_active=False), 审核通过才激活; 拒绝保持 is_active=False.
"""
from django.db import models
from nanoid import generate as nanoid_generate

from apps.common.models import TimestampedModel


def gen_id():
    return nanoid_generate(size=21)


class EmailVerificationCode(TimestampedModel):
    """邮箱验证码 (SHA-256 hash, 15min 过期, 5 次错误锁定)."""

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    email = models.EmailField(db_index=True, verbose_name='邮箱')
    code_hash = models.CharField(max_length=128, verbose_name='验证码 SHA-256')
    purpose = models.CharField(max_length=32, default='REGISTER', verbose_name='用途')
    expires_at = models.DateTimeField(verbose_name='过期时间')
    attempts = models.IntegerField(default=0, verbose_name='错误尝试次数')
    status = models.CharField(
        max_length=16, default='ACTIVE',
        choices=[('ACTIVE', '有效'), ('USED', '已使用'), ('EXPIRED', '已过期'), ('LOCKED', '已锁定')],
        verbose_name='状态',
    )

    class Meta:
        db_table = 'email_verification_codes'
        verbose_name = '邮箱验证码'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['email', 'purpose', 'status']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f'Code[{self.email}][{self.status}]'


class RegistrationApplication(TimestampedModel):
    """注册申请: 自注册用户 → 管理员审核."""

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    user = models.OneToOneField(
        'core.User', on_delete=models.CASCADE, related_name='registration', verbose_name='用户',
    )
    email = models.EmailField(unique=True, verbose_name='邮箱')
    full_name = models.CharField(max_length=64, blank=True, verbose_name='姓名')
    status = models.CharField(
        max_length=16, default='PENDING', db_index=True,
        choices=[
            ('PENDING', '待审核'),
            ('APPROVED', '已通过'),
            ('REJECTED', '已拒绝'),
            ('EXPIRED', '已过期'),
        ],
        verbose_name='状态',
    )
    email_verified = models.BooleanField(default=False, verbose_name='邮箱已验证')
    reviewed_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='审核人',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    reject_reason = models.TextField(blank=True, verbose_name='拒绝原因')

    class Meta:
        db_table = 'registration_applications'
        verbose_name = '注册申请'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'Reg[{self.email}][{self.status}]'
