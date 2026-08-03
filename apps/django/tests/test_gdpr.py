"""GDPR Service 测试 (2026-08-03 S2: 验证码 hash 化 + 过期 + 锁定)

覆盖:
- submit_request 生成 code, hash 存, 不明文
- verify_code 正确路径 → status=PENDING + 清空 hash
- verify_code 错误 → attempts+1
- verify_code 5 次错误 → status=LOCKED
- verify_code 过期 → status=EXPIRED
- verify_code 已 verified 重复 verify → 报错
- verify_code 已 PROCESSING/COMPLETED/REJECTED → 报错
- approve_and_forget 未 verified → 报错
- approve_and_forget 已 verified + 超管 → 成功 + PII 匿名化
- reject 不需要 verified
- cleanup_stale_verification 自动转 EXPIRED
"""
import pytest
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from apps.gdpr.models import (
    GDPRRequest,
    GDPRRequestStatus,
    GDPRRequestType,
    VERIFICATION_CODE_LENGTH,
    VERIFICATION_MAX_ATTEMPTS,
    hash_verification_code,
)
from apps.gdpr.services import GdprService
from apps.common.exceptions import ValidationError, NotFound


@pytest.fixture
def candidate(db):
    from apps.candidate.models import Candidate
    return Candidate.objects.create(
        id='cand-gdpr-001',
        name='GDPR 测试候选人',
        phone='13800000001',
        email='gdpr@example.com',
    )


@pytest.fixture
def super_user(db, department):
    from apps.core.models import User
    return User.objects.create_user(
        username='gdpr_admin',
        password='Test@1234',
        is_staff=True,
        is_superuser=True,
    )


@pytest.mark.django_db
class TestGdprSubmitRequest:
    def test_submit_generates_code_and_hashes_it(self, candidate):
        """提交时生成 code, hash 存 DB, 响应带明文 (一次性)."""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        # status 应该是 AWAITING_VERIFICATION
        assert req.status == GDPRRequestStatus.AWAITING_VERIFICATION
        # verification_code_hash 应该有值, 但不是明文 code
        assert req.verification_code_hash != ''
        assert req._plaintext_code  # noqa: SLF001
        assert len(req._plaintext_code) == VERIFICATION_CODE_LENGTH  # noqa: SLF001
        # 明文 code 不应等于 hash
        assert req._plaintext_code != req.verification_code_hash  # noqa: SLF001
        # hash 应等于明文 code 的 sha256
        assert req.verification_code_hash == hash_verification_code(req._plaintext_code)  # noqa: SLF001
        # expires_at 应是 ~15 分钟后
        delta = req.verification_code_expires_at - timezone.now()
        assert timedelta(minutes=14) < delta < timedelta(minutes=16)
        # attempts 应是 0
        assert req.verification_code_attempts == 0

    def test_submit_does_not_store_plaintext_in_db(self, candidate):
        """关键安全断言: DB 里不应有明文 code 任何痕迹."""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        # 重新查 DB
        from apps.gdpr.models import GDPRRequest
        db_req = GDPRRequest.objects.get(id=req.id)
        # DB 里所有 string 字段加起来不应有 plaintext
        all_text = (
            db_req.verification_code_hash
            + db_req.result
            + db_req.reject_reason
            + db_req.submitted_email
        )
        assert plaintext not in all_text, (
            f'明文 verification code "{plaintext}" 不应出现在 DB 任何字段!'
        )

    def test_submit_invalid_type_raises(self, candidate):
        with pytest.raises(ValidationError, match='请求类型'):
            GdprService.submit_request(
                candidate_id=candidate.id,
                request_type='NOT_A_REAL_TYPE',
                submitted_email='a@b.com',
            )

    def test_submit_missing_email_raises(self, candidate):
        with pytest.raises(ValidationError, match='邮箱'):
            GdprService.submit_request(
                candidate_id=candidate.id,
                request_type=GDPRRequestType.FORGET,
                submitted_email='',
            )

    def test_submit_nonexistent_candidate_raises(self, db):
        with pytest.raises(NotFound):
            GdprService.submit_request(
                candidate_id='cand-not-exist',
                request_type=GDPRRequestType.FORGET,
                submitted_email='a@b.com',
            )


@pytest.mark.django_db
class TestGdprVerifyCode:
    def test_verify_correct_code_succeeds(self, candidate):
        """正确验证码 → status=PENDING, verified_at 有值, hash 清空."""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001

        verified = GdprService.verify_code(req.id, plaintext)
        assert verified.status == GDPRRequestStatus.PENDING
        assert verified.verified_at is not None
        # hash 应清空防 replay
        assert verified.verification_code_hash == ''

    def test_verify_wrong_code_increments_attempts(self, candidate):
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        with pytest.raises(ValidationError, match='验证码错误'):
            GdprService.verify_code(req.id, 'wrongcode1')
        req.refresh_from_db()
        assert req.verification_code_attempts == 1
        assert req.status == GDPRRequestStatus.AWAITING_VERIFICATION  # 未锁定

    def test_verify_5_wrong_attempts_locks(self, candidate):
        """5 次错误 → status=LOCKED."""
        from apps.gdpr.models import GDPRRequest
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        from django.db import connection
        for i in range(VERIFICATION_MAX_ATTEMPTS):
            with pytest.raises(ValidationError):
                GdprService.verify_code(req.id, f'wrong{i}xxx')
            # 看 db 实际状态
            with connection.cursor() as c:
                c.execute("SELECT status, verification_code_attempts FROM gdpr_requests WHERE id=%s", [req.id])
                row = c.fetchone()
                print(f'  after attempt {i+1}: db status={row[0]}, attempts={row[1]}')
        req.refresh_from_db()
        assert req.status == GDPRRequestStatus.LOCKED
        assert req.verification_code_attempts == VERIFICATION_MAX_ATTEMPTS

    def test_verify_after_lock_raises(self, candidate):
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        for i in range(VERIFICATION_MAX_ATTEMPTS):
            with pytest.raises(ValidationError):
                GdprService.verify_code(req.id, f'wrong{i}xxx')
        # 锁定后再 verify → 报错
        with pytest.raises(ValidationError, match='锁定'):
            GdprService.verify_code(req.id, 'anything')

    def test_verify_expired_marks_status(self, candidate):
        """过期 → status=EXPIRED, 验证失败."""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        # 强制过期
        GDPRRequest.objects.filter(id=req.id).update(
            verification_code_expires_at=timezone.now() - timedelta(minutes=1)
        )
        with pytest.raises(ValidationError, match='过期'):
            GdprService.verify_code(req.id, plaintext)
        req.refresh_from_db()
        assert req.status == GDPRRequestStatus.EXPIRED

    def test_verify_already_verified_raises(self, candidate):
        """已 verified 重复 verify → 报错 (防 replay)."""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)  # 第一次 OK
        # 第二次 (即使 code 已经被清空) → 报错
        with pytest.raises(ValidationError, match='已验证'):
            GdprService.verify_code(req.id, plaintext)

    def test_verify_processing_request_raises(self, candidate, super_user):
        """状态 PROCESSING/COMPLETED/REJECTED 不能再 verify."""
        from apps.gdpr.models import GDPRRequest
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        # 强制改成 PROCESSING
        GDPRRequest.objects.filter(id=req.id).update(status=GDPRRequestStatus.PROCESSING)
        with pytest.raises(ValidationError, match='处理中'):
            GdprService.verify_code(req.id, plaintext)

    def test_verify_nonexistent_request_raises(self, db):
        with pytest.raises(NotFound):
            GdprService.verify_code('req-not-exist', 'whatever')


@pytest.mark.django_db
class TestGdprApproveAndForget:
    def test_approve_without_verify_raises(self, candidate, super_user):
        """未 verified 直接 approve → 报错 (核心安全修复!)."""
        GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        # 此时 status = AWAITING_VERIFICATION, 直接 approve 应失败
        from apps.gdpr.models import GDPRRequest
        req = GDPRRequest.objects.get(candidate=candidate)
        with pytest.raises(ValidationError, match='不可处理'):
            GdprService.approve_and_forget(req.id, super_user)

    def test_approve_non_superuser_raises(self, candidate):
        from apps.core.models import User
        non_super = User.objects.create_user(
            username='normal', password='Test@1234', is_staff=True
        )
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        with pytest.raises(Exception, match='超管'):
            GdprService.approve_and_forget(req.id, non_super)

    def test_approve_anonymizes_pii(self, candidate, super_user):
        """approve_and_forget 真正匿名化 PII (name/phone/email/id_card)."""
        from apps.candidate.models import Candidate
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)

        approved = GdprService.approve_and_forget(req.id, super_user)
        assert approved.status == GDPRRequestStatus.COMPLETED
        assert approved.processed_by == super_user
        assert approved.processed_at is not None
        assert '已匿名化' in approved.result

        # 候选人 PII 应被清空 (用 raw queryset 避免 django-fsm 阻止)
        c = Candidate.objects.get(id=candidate.id)
        assert c.name.startswith('[匿名-')
        assert c.phone == ''
        assert c.email == ''
        assert c.id_card_no == ''
        # 软删除
        assert c.deleted_at is not None


@pytest.mark.django_db
class TestGdprApproveAndExport:
    def test_export_after_verify_succeeds(self, candidate, super_user):
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.EXPORT,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)

        exported = GdprService.approve_and_export(req.id, super_user)
        assert exported.status == GDPRRequestStatus.COMPLETED
        # 导出数据应包含所有 PII 字段
        assert candidate.name in exported.result
        assert candidate.phone in exported.result
        assert candidate.email in exported.result


@pytest.mark.django_db
class TestGdprReject:
    def test_reject_without_verify_allowed(self, candidate, super_user):
        """reject 不需要候选人 verify (信息不全也能拒)."""
        GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        from apps.gdpr.models import GDPRRequest
        req = GDPRRequest.objects.get(candidate=candidate)
        rejected = GdprService.reject(req.id, '信息不全', super_user)
        assert rejected.status == GDPRRequestStatus.REJECTED
        assert rejected.reject_reason == '信息不全'

    def test_reject_non_superuser_raises(self, candidate):
        from apps.core.models import User
        normal = User.objects.create_user(
            username='normal2', password='Test@1234', is_staff=True
        )
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        with pytest.raises(Exception, match='超管'):
            GdprService.reject(req.id, '...', normal)


@pytest.mark.django_db
class TestGdprCleanup:
    def test_cleanup_stale_verification_marks_expired(self, candidate):
        """cleanup_stale_verification 把 AWAITING_VERIFICATION 且 expires_at < now 的转 EXPIRED."""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        # 强制过期
        GDPRRequest.objects.filter(id=req.id).update(
            verification_code_expires_at=timezone.now() - timedelta(minutes=1)
        )
        updated = GdprService.cleanup_stale_verification()
        assert updated == 1
        req.refresh_from_db()
        assert req.status == GDPRRequestStatus.EXPIRED

    def test_cleanup_5_year_old_marks_expired(self, candidate):
        """cleanup_expired: 5 年前的请求转 EXPIRED."""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        GDPRRequest.objects.filter(id=req.id).update(
            created_at=timezone.now() - timedelta(days=365 * 6)
        )
        updated = GdprService.cleanup_expired()
        assert updated >= 1
        req.refresh_from_db()
        assert req.status == GDPRRequestStatus.EXPIRED
