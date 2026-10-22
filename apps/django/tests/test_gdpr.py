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

2026-10-21 整改卡 C1 / C2 追加:
- C1: approve_and_export 的 result 列与详情接口**不再**含 PII 明文;
      明文改走一次性加密下载件 (下载即失效 + 密文擦除 + 审计留痕)
- C2: approve_and_forget 连盲索引 hash 列 (phone_hash/email_hash/id_card_hash) 一起清空
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.common.exceptions import NotFound, ValidationError
from apps.gdpr.models import (
    VERIFICATION_CODE_LENGTH,
    VERIFICATION_MAX_ATTEMPTS,
    GDPRExportArtifact,
    GDPRRequest,
    GDPRRequestStatus,
    GDPRRequestType,
    hash_verification_code,
)
from apps.gdpr.services import GdprService


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

        # 候选人 PII 应被清空 (用 all_objects 读回: 2026-10-21 卡 D3 后默认 manager 已过滤软删行)
        c = Candidate.all_objects.get(id=candidate.id)
        assert c.name.startswith('[匿名-')
        assert c.phone == ''
        assert c.email == ''
        assert c.id_card_no == ''
        # 软删除
        assert c.deleted_at is not None


@pytest.mark.django_db
class TestGdprAnonymizeClearsHashColumns:
    """整改卡 C2: 匿名化必须连盲索引 hash 列一起清空。

    phone_hash / email_hash / id_card_hash 是 salt 前置 SHA-256, 手机号空间仅
    ~10^10 且历史 salt 曾硬编码在源码里 → 只清明文列、留着 hash 列等于
    "把门锁了但把钥匙留在门口", 被遗忘权形同虚设。
    """

    def test_anonymize_clears_hash_columns(self, candidate, super_user):
        from apps.candidate.models import Candidate
        from apps.common.encryption import hash_for_search

        Candidate.objects.filter(id=candidate.id).update(
            phone_hash=hash_for_search('13800000001'),
            email_hash=hash_for_search('gdpr@example.com'),
            id_card_hash=hash_for_search('110101199001011234'),
        )

        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        GdprService.approve_and_forget(req.id, super_user)

        c = Candidate.all_objects.get(id=candidate.id)
        assert c.phone_hash == ''
        assert c.email_hash == ''
        assert c.id_card_hash == ''

    def test_hash_columns_cleared_in_db(self, candidate, super_user):
        """DB 层直查: 3 个 hash 列均为空串 (防 ORM 缓存/未落库)。"""
        from django.db import connection

        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.FORGET,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        GdprService.approve_and_forget(req.id, super_user)

        with connection.cursor() as cur:
            cur.execute(
                'SELECT phone_hash, email_hash, id_card_hash FROM candidates WHERE id=%s',
                [candidate.id],
            )
            row = cur.fetchone()
        assert row == ('', '', '')


@pytest.mark.django_db
class TestGdprApproveAndExport:
    """整改卡 C1: 导出不得把 PII 明文写进 result 列。"""

    def test_export_after_verify_succeeds(self, candidate, super_user):
        """导出成功 → result 只剩摘要, PII 明文不再落库。"""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.EXPORT,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)

        exported = GdprService.approve_and_export(req.id, super_user)
        assert exported.status == GDPRRequestStatus.COMPLETED
        assert '已导出' in exported.result
        # result 里不含任何 PII 明文
        assert candidate.name not in exported.result
        assert candidate.phone not in exported.result
        assert candidate.email not in exported.result

    def test_export_result_column_has_no_pii_plaintext(self, candidate, super_user):
        """DB 层的 result 列同样不得含 PII 明文 (改造前是 f'导出数据：{export_data}')."""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.EXPORT,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        GdprService.approve_and_export(req.id, super_user)

        db_req = GDPRRequest.objects.get(id=req.id)
        assert candidate.phone not in db_req.result
        assert candidate.email not in db_req.result
        assert 'gdpr@example.com' not in db_req.result


@pytest.mark.django_db
class TestGdprExportArtifact:
    """整改卡 C1: 一次性加密下载件。"""

    def test_artifact_payload_is_ciphertext(self, candidate, super_user):
        """落库的导出件必须是 Fernet 密文, 不含明文。"""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.EXPORT,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        GdprService.approve_and_export(req.id, super_user)

        artifact = GDPRExportArtifact.objects.get(request=req)
        assert artifact.payload.startswith('gAAAA')          # Fernet token 前缀
        assert candidate.phone not in artifact.payload
        assert candidate.email not in artifact.payload
        assert artifact.downloaded_at is None
        assert artifact.download_count == 0
        assert artifact.expires_at > timezone.now()

    def test_download_returns_data_then_token_is_dead(self, candidate, super_user):
        """下载一次拿到明文, 同一 token 二次下载被拒 + 密文已擦除。"""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.EXPORT,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        GdprService.approve_and_export(req.id, super_user)
        artifact = GDPRExportArtifact.objects.get(request=req)

        data = GdprService.consume_export_artifact(req.id, artifact.token)
        assert data['phone'] == candidate.phone
        assert data['email'] == candidate.email
        assert data['name'] == candidate.name

        # 下载后: 密文擦除 + 下载时间落库
        artifact.refresh_from_db()
        assert artifact.payload == ''
        assert artifact.downloaded_at is not None
        assert artifact.download_count == 1

        # 同一 token 不可二次使用
        with pytest.raises(ValidationError, match='已被下载'):
            GdprService.consume_export_artifact(req.id, artifact.token)

    def test_expired_artifact_rejected(self, candidate, super_user):
        """过期导出件拒绝下载。"""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.EXPORT,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        GdprService.approve_and_export(req.id, super_user)
        artifact = GDPRExportArtifact.objects.get(request=req)

        GDPRExportArtifact.objects.filter(id=artifact.id).update(
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        with pytest.raises(ValidationError, match='过期'):
            GdprService.consume_export_artifact(req.id, artifact.token)

    def test_wrong_token_rejected(self, candidate, super_user):
        """token 对不上 → 404 (不泄露"存在但无权"与"不存在"的差别)。"""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.EXPORT,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        GdprService.approve_and_export(req.id, super_user)

        with pytest.raises(NotFound):
            GdprService.consume_export_artifact(req.id, 'not-a-real-token')

    def test_cleanup_expired_exports_wipes_ciphertext(self, candidate, super_user):
        """超期未下载的导出件: 保留行, 擦掉密文。"""
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.EXPORT,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        GdprService.approve_and_export(req.id, super_user)
        artifact = GDPRExportArtifact.objects.get(request=req)

        GDPRExportArtifact.objects.filter(id=artifact.id).update(
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        assert GdprService.cleanup_expired_exports() == 1
        artifact.refresh_from_db()
        assert artifact.payload == ''


@pytest.mark.django_db
class TestGdprApiNoPlaintextLeak:
    """整改卡 C1 的 API 层验收: 读接口不得吐 PII 明文。"""

    def _prepare_verified(self, candidate):
        req = GdprService.submit_request(
            candidate_id=candidate.id,
            request_type=GDPRRequestType.EXPORT,
            submitted_email='gdpr@example.com',
        )
        plaintext = req._plaintext_code  # noqa: SLF001
        GdprService.verify_code(req.id, plaintext)
        return req

    def test_retrieve_response_has_no_pii_plaintext(self, auth_client, candidate):
        """GET 请求详情 → 响应体不含手机号/邮箱明文。"""
        req = self._prepare_verified(candidate)
        resp = auth_client.get(f'/api/v1/gdpr/{req.id}/')
        assert resp.status_code == 200, resp.content
        body = resp.content.decode()
        assert candidate.phone not in body
        assert candidate.email not in body
        # 提交邮箱改为脱敏输出
        assert resp.data['data']['submitted_email_masked'] == 'g***@example.com'
        assert 'submitted_email' not in resp.data['data']

    def test_process_export_returns_download_url_without_plaintext(self, auth_client, candidate):
        """process(approve_export) → 只给一次性下载链接, 响应体不含 PII 明文。"""
        req = self._prepare_verified(candidate)
        resp = auth_client.post(
            f'/api/v1/gdpr/{req.id}/process/',
            {'action': 'approve_export'},
            format='json',
        )
        assert resp.status_code == 200, resp.content
        body = resp.content.decode()
        assert candidate.phone not in body
        assert candidate.email not in body
        export_info = resp.data['data']['export']
        assert export_info['one_time'] is True
        assert 'token=' in export_info['download_url']

    def test_download_endpoint_serves_then_expires(self, auth_client, candidate):
        """一次性下载端点: 首次拿到明文, 再次下载被拒。"""
        req = self._prepare_verified(candidate)
        resp = auth_client.post(
            f'/api/v1/gdpr/{req.id}/process/',
            {'action': 'approve_export'},
            format='json',
        )
        assert resp.status_code == 200, resp.content
        token = resp.data['data']['export']['download_url'].split('token=')[1]

        first = auth_client.get(f'/api/v1/gdpr/{req.id}/export/', {'token': token})
        assert first.status_code == 200, first.content
        assert first.data['data']['phone'] == candidate.phone

        # 审计留痕: 下载动作写 AuditLog, 且日志里不含 PII 明文
        from apps.audit.models import AuditLog
        log = AuditLog.objects.filter(
            entity='GDPRRequest', entity_id=str(req.id), action='EXPORT',
        ).first()
        assert log is not None, '下载动作必须留审计记录'
        assert candidate.phone not in (log.old_value + log.new_value)
        assert candidate.email not in (log.old_value + log.new_value)

        second = auth_client.get(f'/api/v1/gdpr/{req.id}/export/', {'token': token})
        assert second.status_code >= 400

    def test_export_endpoint_requires_superadmin(self, client, candidate):
        """未登录访问一次性下载端点 → 拒绝。"""
        req = self._prepare_verified(candidate)
        resp = client.get(f'/api/v1/gdpr/{req.id}/export/', {'token': 'whatever'})
        assert resp.status_code in (401, 403)


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
