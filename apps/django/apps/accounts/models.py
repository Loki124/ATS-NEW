"""邮箱验证码模型（供「邮箱验证码免密登录」使用）。

安全范式 (与 gdpr 验证码一致):
- 验证码只存 SHA-256 hash, 绝不存明文.
- 15 分钟过期, 5 次错误锁定.

2026-10-18 兵哥：移除自助注册后，本 app 只保留验证码基础设施；
  RegistrationApplication（注册申请审核）模型已随自助注册一并删除。
"""
from django.db import models
from nanoid import generate as nanoid_generate

from apps.common.models import TimestampedModel


def gen_id():
    return nanoid_generate(size=21)


class EmailVerificationCode(TimestampedModel):
    """邮箱验证码 (SHA-256 hash, 15min 过期, 5 次错误锁定).

    purpose 区分用途：'LOGIN'（邮箱验证码登录）。字段保留为通用字符串，
    便于未来扩展其它一次性验证码场景（如改密二次校验）。
    """

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    email = models.EmailField(db_index=True, verbose_name='邮箱')
    code_hash = models.CharField(max_length=128, verbose_name='验证码 SHA-256')
    purpose = models.CharField(max_length=32, default='LOGIN', verbose_name='用途')
    expires_at = models.DateTimeField(verbose_name='过期时间')
    attempts = models.IntegerField(default=0, verbose_name='错误尝试次数')
    status = models.CharField(
        max_length=16, default='ACTIVE',
        choices=[('ACTIVE', '有效'), ('USED', '已使用'), ('EXPIRED', '已过期'), ('LOCKED', '已锁定')],
        verbose_name='状态',
                   db_index=True,
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
        return f'Code[{self.email}][{self.purpose}][{self.status}]'
