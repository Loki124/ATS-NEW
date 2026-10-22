"""GDPR Services (PRD v4 §4.4) - 个人信息保护

2026-08-03 S2 改造:
- 验证码不再明文存, 改 SHA-256 hash + 15 min TTL + 5 次 attempts 锁定
- 新增流程: 候选人提交 → system 生成 code + hash 存 → email/SMS 发 code →
            候选人 verify → 超管 process (verify 通过才能 process)
- approve_and_forget / approve_and_export / reject 都加 _assert_verified() 前置检查
"""
from __future__ import annotations

import hmac
import json
import logging
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.candidate.models import Candidate
from apps.common.encryption import decrypt_value, encrypt_value
from apps.common.exceptions import NotFound, PermissionDenied, ValidationError
from apps.core.models import User
from apps.core.role_v2_query import is_super_admin

from .models import (
    EXPORT_TOKEN_TTL_MINUTES,
    VERIFICATION_CODE_LENGTH,
    VERIFICATION_CODE_TTL_MINUTES,
    VERIFICATION_MAX_ATTEMPTS,
    GDPRExportArtifact,
    GDPRRequest,
    GDPRRequestStatus,
    GDPRRequestType,
    hash_verification_code,
)

logger = logging.getLogger(__name__)


def send_verification_code(req, plaintext_code: str) -> bool:
    """把验证码发送到候选人登记邮箱。

    2026-10-08: 验证码此前直接放在 HTTP 响应体里返回给**匿名**调用者 ——
    只要知道候选人 id + 任意邮箱就能拿到验证码, 再用公开的 verify 端点把请求
    置为"已验证", 使审批人误以为请求确由候选人本人发起。现在验证码只走邮件下发。

    日志只记录邮箱后 4 位, 避免把 PII 写进日志。
    """
    from django.conf import settings
    from django.core.mail import send_mail

    to = (getattr(req, 'submitted_email', '') or '').strip()
    if not to:
        logger.warning('GDPR request %s: 无登记邮箱, 验证码无法下发', req.id)
        return False

    try:
        send_mail(
            subject='【招聘系统】个人信息处理请求验证码',
            message=(
                f'你发起的个人信息处理请求验证码为: {plaintext_code}\n'
                f'有效期 {VERIFICATION_CODE_TTL_MINUTES} 分钟。\n'
                '如非本人操作请忽略本邮件。'
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=[to],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001 — 邮件后端异常类型多样（smtplib/socket/模板渲染），统一降级为「发送失败」并保留 exception 日志
        logger.exception('GDPR request %s: 验证码邮件发送失败', req.id)
        return False

    logger.info('GDPR request %s: 验证码已发送至邮箱 ***%s', req.id, to[-4:])
    return True


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

        # 2026-10-08: 提交邮箱必须与候选人已登记邮箱一致, 否则任何人凭任意邮箱
        #   就能发起「以候选人名义」的删除/导出请求, 身份验证形同虚设。
        #   用恒定时间比较, 避免通过响应耗时侧信道枚举邮箱。
        registered = (getattr(candidate, 'email', '') or '').strip().lower()
        if not registered or not hmac.compare_digest(
            registered, (submitted_email or '').strip().lower(),
        ):
            raise ValidationError('提交邮箱与候选人登记邮箱不一致')

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
        # 2026-10-21 (整改卡 C2): 盲索引 hash 列必须一并清空。
        #   phone_hash / email_hash / id_card_hash 是 salt 前置 SHA-256, 手机号空间
        #   仅 ~10^10 且明文 salt 曾在源码里硬编码 → 留着它们等于"清空明文但保留
        #   可反查的钥匙", 被遗忘权形同虚设。三列均 db_index=True, 查重走 hash 列,
        #   匿名化后该候选人本就不该再参与查重, 清空无业务副作用。
        candidate.phone_hash = ''
        candidate.email_hash = ''
        candidate.id_card_hash = ''
        # soft_delete 内部只 save deleted_at, PII 字段需显式 save
        candidate.save(update_fields=[
            'name', 'phone', 'email', 'id_card_no',
            'phone_hash', 'email_hash', 'id_card_hash',
            'updated_at',
        ])
        candidate.soft_delete()

        # 2026-10-21 (整改卡 C3): 清关联表里的 PII 副本。
        #   主表清了不代表 PII 没了 —— 动态字段值表、简历原文、面评备注、审计链里
        #   还各存着一份副本 (见 apps/gdpr/purge.py 的口径说明)。
        from .purge import purge_candidate_pii
        purge_report = purge_candidate_pii(candidate, processor=processor)

        req.status = GDPRRequestStatus.COMPLETED
        req.processed_by = processor
        req.processed_at = timezone.now()
        # 提交邮箱是候选人邮箱的副本, 请求已处理完 → 一并清空
        req.submitted_email = ''
        req.result = (
            f'已匿名化候选人 {candidate.id}：主表 PII 与 3 个 hash 盲索引已清空，'
            f'关联表 PII 副本已按被遗忘权清理（详见清理报告）'
        )
        req.save(update_fields=[
            'status', 'processed_by', 'processed_at', 'result', 'submitted_email', 'updated_at',
        ])
        logger.info(
            'GDPR forget executed: candidate=%s purge_report=%s',
            candidate.id, purge_report,
        )
        return req

    @staticmethod
    def approve_and_export(request_id: str, processor: User) -> GDPRRequest:
        """数据导出 (2026-10-21 整改卡 C1: PII 明文不再落 `result` 列)

        **改造前**: `req.result = f'导出数据：{export_data}'` —— export_data 含
        name/phone/email/id_card_no 明文, 而 `result` 在 `GDPRRequestSerializer.fields`
        里 → PII 明文既写进 `gdpr_requests` 表, 又能被请求详情接口原样吐回。

        **改造后**:
        1) 明文只在内存里组装一次
        2) Fernet 加密 → 存 `GDPRExportArtifact` (一次性下载件)
        3) `result` 只写摘要 (不含任何 PII)
        4) 下载走独立端点: 超管登录 + 一次性 token + 有效期, 下载后 token 失效且密文擦除
        """
        try:
            req = GDPRRequest.objects.select_for_update().get(id=request_id)
        except GDPRRequest.DoesNotExist as e:
            raise NotFound(f'GDPR 请求 {request_id} 不存在') from e

        GdprService._assert_verified(req, processor)
        req.status = GDPRRequestStatus.PROCESSING
        req.save(update_fields=['status', 'updated_at'])

        candidate = req.candidate
        # 收集候选人所有 PII 数据 —— 只存在于本函数栈内, 加密后即从内存语义上"消亡"
        export_data = {
            'candidate_id': candidate.id,
            'name': candidate.name,
            'phone': candidate.phone,
            'email': candidate.email,
            'id_card_no': candidate.id_card_no,
            'exported_at': timezone.now().isoformat(),
        }

        artifact = GdprService._create_export_artifact(req, export_data, processor)

        req.status = GDPRRequestStatus.COMPLETED
        req.processed_by = processor
        req.processed_at = timezone.now()
        pii_field_count = sum(
            1 for key in export_data if key not in ('candidate_id', 'exported_at')
        )
        req.result = (
            f'已导出候选人 {candidate.code or candidate.id} 的 {pii_field_count} 项个人信息；'
            f'导出件为一次性下载（{EXPORT_TOKEN_TTL_MINUTES} 分钟内有效），下载动作已留审计记录'
        )
        req.save()
        # 导出件信息只在本次返回体里流转 (含 token), 不再写进 result 列
        req._export_artifact = artifact  # noqa: SLF001
        return req

    @staticmethod
    def _create_export_artifact(
        req: GDPRRequest, export_data: dict, processor: User | None
    ) -> GDPRExportArtifact:
        """把导出明文加密成一次性下载件。

        加密用 `apps.common.encryption.encrypt_value` (Fernet), 与 `id_card_no`
        同一套密钥体系 —— 换密钥时行为一致 (MultiFernet 双读)。
        """
        token = secrets.token_urlsafe(32)
        payload = json.dumps(export_data, ensure_ascii=False, default=str)
        ciphertext = encrypt_value(payload)
        if not ciphertext:
            raise ValidationError('导出件加密失败：请检查 ENCRYPTION_KEY 配置')
        return GDPRExportArtifact.objects.create(
            request=req,
            payload=ciphertext,
            token=token,
            expires_at=timezone.now() + timedelta(minutes=EXPORT_TOKEN_TTL_MINUTES),
            created_by=processor if (processor and processor.is_authenticated) else None,
        )

    @staticmethod
    def consume_export_artifact(request_id: str, token: str) -> dict:
        """消费一次性导出件, 返回导出明文 (下载后即失效)。

        校验链: 归属该请求 → 未被下载过 → 未过期 → 密文可解。
        成功后立刻擦除密文并落 `downloaded_at`, 同一 token 不可二次使用;
        即便 DB 事后被导出, 该导出件也已无明文可取。
        """
        if not token:
            raise ValidationError('缺少导出件 token')
        try:
            artifact = GDPRExportArtifact.objects.get(request_id=request_id, token=token)
        except GDPRExportArtifact.DoesNotExist as e:
            raise NotFound('导出件不存在或链接已失效') from e

        if artifact.downloaded_at is not None:
            raise ValidationError('导出件已被下载，一次性链接已失效')
        if artifact.expires_at < timezone.now():
            raise ValidationError('导出件已过期，请重新发起导出')

        plaintext = decrypt_value(artifact.payload, field_name='gdpr_export_payload')
        if not plaintext:
            raise NotFound('导出件内容已擦除，请重新发起导出')
        try:
            data = json.loads(plaintext)
        except json.JSONDecodeError as e:
            raise ValidationError('导出件内容损坏，请重新发起导出') from e

        # 一次性语义: 下载即擦除密文
        artifact.payload = ''
        artifact.downloaded_at = timezone.now()
        artifact.download_count = (artifact.download_count or 0) + 1
        artifact.save(update_fields=[
            'payload', 'downloaded_at', 'download_count', 'updated_at',
        ])
        return data

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
    def cleanup_expired_exports() -> int:
        """擦除超期未下载的导出件密文 (2026-10-21 卡 C1 配套)。

        导出件即使没人下载, 到期后其 Fernet 密文也不应无限期留在库里 ——
        擦掉 payload 后即便 DB 被整体导出, 也取不到候选人 PII。
        """
        expired = GDPRExportArtifact.objects.filter(
            expires_at__lt=timezone.now(),
            payload__gt='',
        )
        count = expired.count()
        expired.update(payload='', downloaded_at=timezone.now())
        return count

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
