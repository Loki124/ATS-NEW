"""C4 —— 候选人 phone / email 落库加密（2026-10-21）

**改前**：phone / email 是**明文列**（还带 db_index）→ 一次库导出即全量 PII 泄露。
**改后**：两者改 `EncryptedCharField`（Fernet，与 id_card_no 同构）。

**本文件锁死 5 件事**：

1. **明文不可见**：原始 SQL 直查列 → 拿不到明文；
2. **应用层透明**：ORM 读出来仍是明文（业务代码无感）；
3. **查重仍可用**：Fernet 是**非确定性**加密（同一明文每次密文不同）→
   按明文 `filter(phone=...)` 必然**静默落空** → 查重必须走 `phone_hash` 盲索引列；
4. **搜索按完整手机号仍能搜到**（hash 精确匹配），但**部分号码的模糊搜索不再支持**
   （密文无法 LIKE）—— 这是本次改动的**已知口径变更**，必须显式记录；
5. **GDPR 清理仍会清掉 hash 列**（与 C2 的交互）。
"""
import pytest
from django.db import connection

from apps.candidate.models import Candidate

pytestmark = pytest.mark.django_db

PHONE = '13800001234'
EMAIL = 'c4_encrypt@example.com'


def _raw_column(table: str, column: str, pk: str):
    """绕过 ORM 直查列的原始值（ORM 会自动解密，直查才看得到存储形态）。"""
    with connection.cursor() as cur:
        cur.execute(f'SELECT {column} FROM {table} WHERE id = %s', [pk])
        row = cur.fetchone()
    return row[0] if row else None


def _make_candidate(pk='cand-c4-001', name='加密候选人', phone=PHONE, email=EMAIL):
    return Candidate.objects.create(id=pk, name=name, phone=phone, email=email)


class TestPlaintextNotInDB:
    def test_phone_column_has_no_plaintext(self):
        """库里存的是密文，不是明文。"""
        c = _make_candidate()
        stored = _raw_column('candidates', 'phone', c.id)
        assert stored is not None
        assert stored != PHONE
        assert PHONE not in stored
        assert stored.startswith('gAAAA'), 'Fernet token 前缀'

    def test_email_column_has_no_plaintext(self):
        c = _make_candidate()
        stored = _raw_column('candidates', 'email', c.id)
        assert stored is not None
        assert stored != EMAIL
        assert EMAIL not in stored
        assert stored.startswith('gAAAA')

    def test_orm_read_is_still_plaintext(self):
        """应用层透明加解密：业务代码读到的仍是明文。"""
        c = _make_candidate()
        c.refresh_from_db()
        assert c.phone == PHONE
        assert c.email == EMAIL

    def test_hash_columns_are_written(self):
        """盲索引列仍按明文算（查重靠它）。"""
        from apps.common.encryption import hash_candidates_for_search

        c = _make_candidate()
        c.refresh_from_db()
        assert c.phone_hash in hash_candidates_for_search(PHONE)
        assert c.email_hash in hash_candidates_for_search(EMAIL)


class TestDedupStillWorks:
    def test_find_duplicate_matches_by_hash(self):
        """按明文查会落空，但查重走 hash → 仍能命中（这是改动的关键风险点）。"""
        from apps.candidate.services import CandidateService

        _make_candidate()
        found = CandidateService._find_duplicate(PHONE, None, None, None)
        assert found is not None, '查重必须命中（走 phone_hash 盲索引列）'
        assert found.phone == PHONE

    def test_raw_plaintext_filter_is_silent_noop(self):
        """记录事实：明文 = 过滤必然落空（且不报错）—— 故禁止再用这种方式查。"""
        _make_candidate()
        assert Candidate.objects.filter(phone=PHONE).count() == 0
        # 而 hash 列能查到
        from apps.common.encryption import hash_candidates_for_search
        assert Candidate.objects.filter(
            phone_hash__in=hash_candidates_for_search(PHONE),
        ).count() == 1

    def test_get_or_create_by_phone_returns_existing(self):
        """快速导入的 upsert 仍能命中已存在候选人。"""
        from apps.candidate.services import CandidateService

        _make_candidate()
        existing = CandidateService.get_or_create_by_phone(PHONE, defaults={})
        assert existing.phone == PHONE

    def test_email_dedup_matches(self):
        from apps.candidate.services import CandidateService

        _make_candidate()
        found = CandidateService._find_duplicate(None, EMAIL, None, None)
        assert found is not None
        assert found.email == EMAIL


class TestSearchByPhone:
    def test_search_by_full_phone_finds_candidate(self):
        """粘贴完整手机号 → 仍能搜到（走 hash 精确匹配）。"""
        from apps.candidate.services import candidate_keyword_q

        _make_candidate()
        qs = Candidate.objects.filter(
            candidate_keyword_q(PHONE, 'name', model=Candidate),
        )
        assert qs.count() == 1

    def test_search_by_full_email_finds_candidate(self):
        from apps.candidate.services import candidate_keyword_q

        _make_candidate()
        qs = Candidate.objects.filter(
            candidate_keyword_q(EMAIL, 'name', model=Candidate),
        )
        assert qs.count() == 1

    def test_search_by_name_still_fuzzy(self):
        """姓名仍是明文且可模糊匹配（密文只影响 phone/email 两个字段）。

        注: 这里用**直接 LIKE** 而非 candidate_keyword_q —— 后者走 MySQL 全文索引,
        而 InnoDB FULLTEXT **看不到未提交事务里的行** (仓内已知限制, 见
        apps/common/tests/test_search.py), 在测试事务里必然查不到, 与加密无关。
        """
        _make_candidate(name='张三名')
        assert Candidate.objects.filter(name__icontains='张三名').count() == 1
        # 姓名未被加密
        assert _raw_column('candidates', 'name', 'cand-c4-001') == '张三名'


class TestGdprInteraction:
    def test_gdpr_forget_clears_encrypted_fields_and_hashes(self):
        """被遗忘权执行后：密文列与 hash 列都要清空。"""
        from apps.gdpr.models import GDPRRequestStatus, GDPRRequestType
        from apps.gdpr.services import GdprService

        c = _make_candidate()
        from apps.gdpr.models import GDPRRequest
        req = GDPRRequest.objects.create(
            candidate=c, request_type=GDPRRequestType.FORGET,
            status=GDPRRequestStatus.AWAITING_VERIFICATION,
            submitted_email=EMAIL,
        )
        # 走完整流程需要验证码，这里直接验证清理后的形态:
        # 匿名化会把 phone/email 置空 → 密文列存空串, hash 列也清空
        from django.contrib.auth import get_user_model
        admin = get_user_model().objects.create_superuser(
            username='c4_admin', password='Test@1234', email='c4_admin@example.com',
        )
        req.status = GDPRRequestStatus.PENDING
        req.verified_at = timezone_now()
        req.save()
        GdprService.approve_and_forget(req.id, admin)

        c.refresh_from_db()
        assert c.phone == ''
        assert c.email == ''
        assert c.phone_hash == ''
        assert c.email_hash == ''


def timezone_now():
    from django.utils import timezone
    return timezone.now()
