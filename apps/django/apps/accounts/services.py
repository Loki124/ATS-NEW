"""注册审核服务: 验证码生成/发送/校验 (安全范式与 gdpr 一致)."""
import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailVerificationCode, RegistrationApplication

logger = logging.getLogger(__name__)

CODE_TTL_MINUTES = 15
MAX_ATTEMPTS = 5
CODE_PURPOSE = 'REGISTER'


def hash_code(code: str) -> str:
    """SHA-256 hex digest. 永远只存 hash, 不存明文."""
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def generate_code() -> str:
    """6 位数字验证码 (10^6 空间)."""
    return f'{secrets.randbelow(1_000_000):06d}'


def _send_code_email(email: str, code: str, full_name: str = '') -> None:
    """发送注册验证码邮件. 用 Django 配置的 EMAIL_BACKEND (env 驱动).

    dev=console, test=locmem (可断言 outbox), prod 设 EMAIL_* 环境变量即真实发信.
    """
    subject = '【ATS 招聘系统】您的注册验证码'
    greeting = f'您好 {full_name}' if full_name else '您好'
    message = (
        f'{greeting}，\n\n'
        f'您的账号注册验证码为：{code}\n'
        f'该验证码 15 分钟内有效，请勿泄露给他人。\n\n'
        f'如非本人操作，请忽略此邮件。'
    )
    html = (
        f'<p>{greeting}，</p>'
        f'<p>您的账号注册验证码为：<b style="font-size:20px;letter-spacing:2px">{code}</b></p>'
        f'<p>该验证码 15 分钟内有效，请勿泄露给他人。</p>'
        f'<p style="color:#999">如非本人操作，请忽略此邮件。</p>'
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[email],
        html_message=html,
        fail_silently=False,
    )


def issue_code(email: str, full_name: str = '') -> EmailVerificationCode:
    """生成并发送新的注册验证码; 使该邮箱旧的有效码失效."""
    EmailVerificationCode.objects.filter(
        email=email, purpose=CODE_PURPOSE, status='ACTIVE',
    ).update(status='EXPIRED')
    code = generate_code()
    rec = EmailVerificationCode.objects.create(
        email=email,
        code_hash=hash_code(code),
        purpose=CODE_PURPOSE,
        expires_at=timezone.now() + timedelta(minutes=CODE_TTL_MINUTES),
        attempts=0,
        status='ACTIVE',
    )
    _send_code_email(email, code, full_name)
    # 2026-10-08: 不再把验证码明文写日志 (dev.py 的 apps logger 是 DEBUG,
    #   这条会原样落到日志文件; 验证码等同一次性凭据)。
    #   本地调试请直接看 console 邮件后端 (EMAIL_BACKEND=console) 的输出。
    logger.info('Register verification code issued for %s (已发送邮件)', email)
    return rec


def verify_code(email: str, code: str):
    """校验验证码. 返回 (ok: bool, reason: str).

    reason ∈ {OK, NO_CODE, EXPIRED, LOCKED, WRONG}.
    OK 时同步把该邮箱 PENDING 申请的 email_verified 置 True.
    """
    rec = EmailVerificationCode.objects.filter(
        email=email, purpose=CODE_PURPOSE, status='ACTIVE',
    ).order_by('-created_at').first()
    if rec is None:
        return False, 'NO_CODE'
    if rec.expires_at < timezone.now():
        rec.status = 'EXPIRED'
        rec.save(update_fields=['status'])
        return False, 'EXPIRED'
    if rec.attempts >= MAX_ATTEMPTS:
        rec.status = 'LOCKED'
        rec.save(update_fields=['status'])
        return False, 'LOCKED'
    if not code or rec.code_hash != hash_code(code):
        rec.attempts += 1
        rec.save(update_fields=['attempts'])
        return False, 'WRONG'
    rec.status = 'USED'
    rec.save(update_fields=['status'])
    RegistrationApplication.objects.filter(
        email=email, status='PENDING',
    ).update(email_verified=True)
    return True, 'OK'
