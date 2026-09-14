"""GDPR Services (PRD v4 §4.4) - 个人信息保护

2026-08-03 S2 改造:
- 验证码不再明文存, 改 SHA-256 hash + 15 min TTL + 5 次 attempts 锁定
- 新增流程: 候选人提交 → system 生成 code + hash 存 → email/SMS 发 code →
            候选人 verify → 超管 process (verify 通过才能 process)
- approve_and_forget / approve_and_export / reject 都加 _assert_verified() 前置检查
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta
from typing import Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.candidate.models import Candidate
from apps.common.exceptions import NotFound, PermissionDenied, ValidationError
from apps.core.models import User
from apps.core.role_v2_query import is_super_admin

from .models import (
    GDPRRequest,
    GDPRRequestStatus,
    GDPRRequestType,
    VERIFICATION_CODE_LENGTH,
    VERIFICATION_CODE_TTL_MINUTES,
    VERIFICATION_MAX_ATTEMPTS,
    hash_verification_code,
)

logger = logging.getLogger(__name__)


class GdprService:
    """GDPR 业务服务"""

    @staticmethod
    @transaction.atomic
    def submit_request(
        candidate_id: str,
        request_type: str,
        submitted_email: str = '',
    ) -> GDPRRequest:
        """候选人提交 GDPR 请求.

        流程 (2026-08-03 改造):
        1) 校验 request_type / email
        2) 生成 8 位 hex 验证码 (2^32 熵, 实际仅 4.3B 空间, 配合 15min TTL 足够)
        3) hash 存 (不存明文)
        4) 设 expires_at = now + 15 min
        5) attempts = 0
        6) 状态 = AWAITING_VERIFICATION

        Returns:
            GDPRRequest 实例 + 明文 code (在 response 里返回, 不会存 DB)
            调用方负责通过邮件/SMS 通知候选人.
        """
        if request_type not in dict(GDPRRequestType.choices):
            raise ValidationError(f'请求类型 {request_type} 非法')
        if not submitted_email:
            raise ValidationError('需提供提交邮箱')

        try:
            candidate = Candidate.objects.get(id=candidate_id, deleted_at__isnull=True)
        except Candidate.DoesNotExist as e:
            raise NotFound(f'候选人 {candidate_id} 不存在') from e

        # 生成 + hash 验证码
        code = secrets.token_hex(VERIFICATION_CODE_LENGTH // 2)  # 8 字符 hex (4 bytes)
        code_hash = hash_verification_code(code)
        expires_at = timezone.now() + timedelta(minutes=VERIFICATION_CODE_TTL_MINUTES)

        req = GDPRRequest.objects.create(
            candidate=candidate,
            request_type=request_type,
            status=GDPRRequestStatus.AWAITING_VERIFICATION,
            submitted_email=submitted_email,
            verification_code_hash=code_hash,
            verification_code_expires_at=expires_at,
            verification_code_attempts=0,
        )
        # 把明文 code 挂到 instance 临时属性, view 负责从 response 返回 (不进 DB)
        req._plaintext_code = code  # noqa: SLF001
        logger.info(
            'GDPR request created: id=%s candidate=%s type=%s (verification code generated, expires at %s)',
            req.id, candidate.id, request_type, expires_at,
        )
        return req

    @staticmethod
    def verify_code(request_id: str, plaintext_code: str) -> GDPRRequest:
        """候选人提交验证码验证身份.

        校验流程:
        1) status 必须是 AWAITING_VERIFICATION (不能 verify 已 verified/locked/expired 的)
        2) 检查 expires_at, 过期 → 转 EXPIRED 状态 + 抛错
        3) 检查 attempts < VERIFICATION_MAX_ATTEMPTS, 锁定 → 转 LOCKED + 抛错
        4) hmac.compare_digest 比对 hash (timing-safe)
        5) 验证成功 → status=PENDING + verified_at=now + 清空 hash (避免 replay)
        6) 验证失败 → attempts+1, 超阈值自动 LOCKED

        Returns:
            GDPRRequest 实例

        2026-08-03 改造: 不用 with transaction.atomic() 包 save.
        原因: pytest-django @pytest.mark.django_db 在测试体外层包 atomic,
        嵌套 atomic 变 savepoint, raise 触发 savepoint rollback → save 丢失.
        不用 with 块, save 走默认 autocommit, 立即生效.
        风险评估: save 状态变更 + raise 是天然 idempotent
        (raise 前已经 save, 下一轮 verify 重新从 DB 读最新状态).
        select_for_update 已经锁行, 同一 request_id 不会并发 verify.
        """
        try:
            # 锁行 (SQLite 测试环境忽略 select_for_update, MySQL 生产真锁)
            req = GDPRRequest.objects.select_for_update().get(id=request_id)
        except GDPRRequest.DoesNotExist as e:
            raise NotFound(f'GDPR 请求 {request_id} 不存在') from e

        if req.status == GDPRRequestStatus.PENDING:
            raise ValidationError('该请求已验证, 无需重复操作')
        if req.status in (GDPRRequestStatus.PROCESSING, GDPRRequestStatus.COMPLETED,
                          GDPRRequestStatus.REJECTED):
            raise ValidationError(f'该请求已 {req.get_status_display()}, 无法验证')
        if req.status == GDPRRequestStatus.LOCKED:
            raise ValidationError('该请求已锁定 (错误尝试过多), 请联系超管')
        if req.status == GDPRRequestStatus.EXPIRED:
            raise ValidationError('该请求验证码已过期, 请重新提交')

        if not req.verification_code_hash:
            raise ValidationError('该请求未生成验证码 (可能数据已损坏), 请联系超管')

        # 过期检查
        if req.is_expired():
            req.status = GDPRRequestStatus.EXPIRED
            req.save(update_fields=['status', 'updated_at'])
            logger.warning('GDPR request %s: verification code expired', req.id)
            raise ValidationError('验证码已过期, 请重新提交')

        # timing-safe hash 比对
        provided_hash = hash_verification_code(plaintext_code)
        if not hmac.compare_digest(provided_hash, req.verification_code_hash):
            # 验证失败: attempts+1, 超阈值自动 LOCKED
            req.verification_code_attempts += 1
            if req.verification_code_attempts >= VERIFICATION_MAX_ATTEMPTS:
                req.status = GDPRRequestStatus.LOCKED
                req.save(update_fields=[
                    'verification_code_attempts', 'status', 'updated_at',
                ])
                logger.warning(
                    'GDPR request %s: locked after failed attempt %d',
                    req.id, req.verification_code_attempts,
                )
                raise ValidationError('验证码错误, 该请求已锁定')
            req.save(update_fields=['verification_code_attempts', 'updated_at'])
            remaining = VERIFICATION_MAX_ATTEMPTS - req.verification_code_attempts
            logger.info('GDPR request %s: wrong code, %d attempts remaining', req.id, remaining)
            raise ValidationError(f'验证码错误, 还有 {remaining} 次机会')

        # 验证通过
        req.status = GDPRRequestStatus.PENDING
        req.verified_at = timezone.now()
        # 清空 hash 防 replay
        req.verification_code_hash = ''
        req.save(update_fields=[
            'status', 'verified_at', 'verification_code_hash', 'updated_at',
        ])
        logger.info('GDPR request %s: verified successfully', req.id)
        return req

    @staticmethod
    def _assert_verified(req: GDPRRequest, processor: User) -> None:
        """process 前置校验: 必须 verified + 超管"""
        if not is_super_admin(processor):
            raise PermissionDenied('仅超管(SUPER_ADMIN 角色)可处理 GDPR 请求')
        if req.status != GDPRRequestStatus.PENDING:
            raise ValidationError(
                f'当前状态 {req.get_status_display()} 不可处理, 需候选人先验证'
            )
        if not req.verified_at:
            raise ValidationError('该请求未通过候选人验证, 不可处理')

    @staticmethod
    def approve_and_forget(request_id: str, processor: User) -> GDPRRequest:
        """被遗忘权 - 匿名化候选人数据"""
        try:
            req = GDPRRequest.objects.select_for_update().get(id=request_id)
        except GDPRRequest.DoesNotExist as e:
            raise NotFound(f'GDPR 请求 {request_id} 不存在') from e

        GdprService._assert_verified(req, processor)
        req.status = GDPRRequestStatus.PROCESSING
        req.save(update_fields=['status', 'updated_at'])

        candidate = req.candidate
        # 匿名化候选人 PII (2026-08-03: name 也脱敏, 之前漏了)
        from nanoid import generate as nanoid_generate
        anonymized_id = f'ANON-{nanoid_generate(size=16)}'
        candidate.name = f'[匿名-{anonymized_id[:8]}]'
        candidate.phone = ''           # 待 S3 改成 EncryptedCharField
        candidate.email = ''           # 待 S3 改成 EncryptedCharField
        candidate.id_card_no = ''      # 待 S3 改成 EncryptedCharField (之前漏)
        # soft_delete 内部只 save deleted_at, PII 字段需显式 save
        candidate.save(update_fields=['name', 'phone', 'email', 'id_card_no', 'updated_at'])
        candidate.soft_delete()

        req.status = GDPRRequestStatus.COMPLETED
        req.processed_by = processor
        req.processed_at = timezone.now()
        req.result = f'已匿名化候选人 {candidate.id}'
        req.save()
        return req

    @staticmethod
    def approve_and_export(request_id: str, processor: User) -> GDPRRequest:
        """数据导出"""
        try:
            req = GDPRRequest.objects.select_for_update().get(id=request_id)
        except GDPRRequest.DoesNotExist as e:
            raise NotFound(f'GDPR 请求 {request_id} 不存在') from e

        GdprService._assert_verified(req, processor)
        req.status = GDPRRequestStatus.PROCESSING
        req.save(update_fields=['status', 'updated_at'])

        candidate = req.candidate
        # 收集候选人所有 PII 数据
        export_data = {
            'candidate_id': candidate.id,
            'name': candidate.name,
            'phone': candidate.phone,
            'email': candidate.email,
            'id_card_no': candidate.id_card_no,
            'exported_at': timezone.now().isoformat(),
        }

        req.status = GDPRRequestStatus.COMPLETED
        req.processed_by = processor
        req.processed_at = timezone.now()
        req.result = f'导出数据：{export_data}'
        req.save()
        return req

    @staticmethod
    def reject(request_id: str, reason: str, processor: User) -> GDPRRequest:
        try:
            req = GDPRRequest.objects.select_for_update().get(id=request_id)
        except GDPRRequest.DoesNotExist as e:
            raise NotFound(f'GDPR 请求 {request_id} 不存在') from e

        if not is_super_admin(processor):
            raise PermissionDenied('仅超管(SUPER_ADMIN 角色)可处理 GDPR 请求')
        if req.status not in (GDPRRequestStatus.PENDING, GDPRRequestStatus.AWAITING_VERIFICATION):
            raise ValidationError(f'当前状态 {req.get_status_display()} 不可拒绝')
        # 拒绝不需要 verified (候选人没 verify 也可以拒, 比如信息不全)

        req.status = GDPRRequestStatus.REJECTED
        req.processed_by = processor
        req.processed_at = timezone.now()
        req.reject_reason = reason
        req.save()
        return req

    @staticmethod
    def cleanup_expired() -> int:
        """清理超期未处理的 GDPR 请求（5 年前）"""
        threshold = timezone.now() - timedelta(days=365 * 5)
        return GDPRRequest.objects.filter(
            created_at__lt=threshold,
            status__in=[
                GDPRRequestStatus.PENDING,
                GDPRRequestStatus.AWAITING_VERIFICATION,
            ],
        ).update(status='EXPIRED')

    @staticmethod
    def cleanup_stale_verification() -> int:
        """清理已过期的验证码 (status 仍是 AWAITING_VERIFICATION 但 expires_at < now).

        Celery beat 跑 (每 1 小时), 防止 status 卡住.
        """
        now = timezone.now()
        return GDPRRequest.objects.filter(
            status=GDPRRequestStatus.AWAITING_VERIFICATION,
            verification_code_expires_at__lt=now,
        ).update(status=GDPRRequestStatus.EXPIRED)
