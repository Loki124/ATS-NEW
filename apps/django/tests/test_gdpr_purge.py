"""GDPR 关联表 PII 清理测试 (2026-10-21 · 整改卡 C3)

口径 (兵哥 2026-10-21 拍板):
  1. 动态字段值 → 按白名单只清个人敏感项 (身份证/手机/邮箱/住址), 其余保留
  2. 简历正文 → raw_content / resume_text 整段清空; parsed_content 保留结构化字段
  3. 面评/推荐理由/备注类文本 → 保留业务事实, 但正则脱敏其中的手机号/邮箱
  4. 无 PII 的关联表 → 不动 (业务事实保留)

覆盖:
- 主表 resume_text 清空
- candidate_field_values: 白名单 key 清空 / 非白名单 key 保留 + 值内脱敏
- dynamic_field_values (泛型引用, 非 FK): 按 field_type 清 / 其余脱敏
- scraped_resumes: raw_content 清空 / parsed_content 保结构清 PII 键
- 面评/备注/推荐理由/拒信原因: 文本脱敏, 业务语义保留
- gdpr_requests.submitted_email 清空
- candidate_histories: detail 脱敏 + 哈希链重算 + 校验端点仍 ok
- 软删行也要被清理
"""
import pytest
from django.utils import timezone

from apps.candidate.models import Candidate, CandidateFieldValue
from apps.common.pii import scrub_text
from apps.gdpr.models import GDPRRequestStatus, GDPRRequestType
from apps.gdpr.services import GdprService

PHONE = '13800000009'
EMAIL = 'purge@example.com'
ID_CARD = '110101199001011234'


@pytest.fixture
def candidate(db):
    return Candidate.objects.create(
        id='cand-purge-001',
        name='待遗忘候选人',
        phone=PHONE,
        email=EMAIL,
    )


@pytest.fixture
def super_user(db):
    from apps.core.models import User
    return User.objects.create_user(
        username='purge_admin',
        password='Test@1234',
        is_staff=True,
        is_superuser=True,
    )


def _forget(candidate, super_user):
    """走完整被遗忘权流程 (含 C2 主表清理 + C3 关联表清理)。"""
    req = GdprService.submit_request(
        candidate_id=candidate.id,
        request_type=GDPRRequestType.FORGET,
        submitted_email=EMAIL,
    )
    plaintext = req._plaintext_code  # noqa: SLF001
    GdprService.verify_code(req.id, plaintext)
    return GdprService.approve_and_forget(req.id, super_user)


# ══════════════════════════════════════════════════════════════════
# 1. 主表
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPurgeMainTable:
    def test_resume_text_cleared(self, candidate, super_user):
        """决策 2: 简历正文整段清空 (与 scraped_resumes.raw_content 同口径)。"""
        Candidate.objects.filter(id=candidate.id).update(resume_text='张三 13800000009 上海某公司')
        _forget(candidate, super_user)
        c = Candidate.all_objects.get(id=candidate.id)
        assert c.resume_text == ''

    def test_business_fields_preserved(self, candidate, super_user):
        """业务事实保留: 学历/城市/期望薪资/当前公司 不动。"""
        from decimal import Decimal

        Candidate.objects.filter(id=candidate.id).update(
            highest_education='本科',
            current_city='上海',
            expected_salary=Decimal('20000'),
            current_company='某科技',
        )
        _forget(candidate, super_user)
        c = Candidate.all_objects.get(id=candidate.id)
        assert c.highest_education == '本科'
        assert c.current_city == '上海'
        assert c.current_company == '某科技'
        assert c.expected_salary == Decimal('20000')


# ══════════════════════════════════════════════════════════════════
# 2. candidate_field_values (白名单清 / 其余保留)
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPurgeCandidateFieldValues:
    def test_sensitive_keys_cleared(self, candidate, super_user):
        """白名单 key (姓名/电话/邮箱/身份证/住址) → value 清空。"""
        for key, value in [
            ('name', '待遗忘候选人'),
            ('mobile', PHONE),
            ('email', EMAIL),
            ('id_card_number', ID_CARD),
            ('residence_address', '上海市浦东新区某路 1 号'),
        ]:
            CandidateFieldValue.objects.create(
                candidate=candidate, field_key=key, value=value,
            )
        _forget(candidate, super_user)
        for key in ('name', 'mobile', 'email', 'id_card_number', 'residence_address'):
            fv = CandidateFieldValue.objects.get(candidate=candidate, field_key=key)
            assert fv.value in (None, ''), f'{key} 未清空: {fv.value!r}'

    def test_business_keys_preserved(self, candidate, super_user):
        """非白名单 key (学历/期望薪资/技能) → 保留, 不被误清。"""
        CandidateFieldValue.objects.create(
            candidate=candidate, field_key='highest_degree', value='本科',
        )
        CandidateFieldValue.objects.create(
            candidate=candidate, field_key='expected_salary', value={'min': 20000, 'max': 30000},
        )
        _forget(candidate, super_user)
        assert CandidateFieldValue.objects.get(
            candidate=candidate, field_key='highest_degree').value == '本科'
        assert CandidateFieldValue.objects.get(
            candidate=candidate, field_key='expected_salary').value == {'min': 20000, 'max': 30000}

    def test_non_sensitive_value_with_phone_is_scrubbed(self, candidate, super_user):
        """非白名单 key 但值里夹带手机号 → 脱敏 (不清除整条)。"""
        CandidateFieldValue.objects.create(
            candidate=candidate, field_key='about_me', value=f'我叫张三，电话 {PHONE}',
        )
        _forget(candidate, super_user)
        value = CandidateFieldValue.objects.get(
            candidate=candidate, field_key='about_me').value
        assert value is not None
        assert PHONE not in value
        assert '138****0009' in value
        assert '我叫张三' in value  # 上下文保留


# ══════════════════════════════════════════════════════════════════
# 3. dynamic_field_values (泛型引用, 按 field_type 清)
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPurgeDynamicFieldValues:
    def test_pii_field_type_cleared_business_kept(self, candidate, super_user):
        """field_type 白名单 (PHONE/EMAIL/ID_CARD/ADDRESS) → 清; TEXT 类 → 保留+脱敏。"""
        from apps.dynamic_field.models import DynamicField, DynamicFieldValue

        DynamicField.objects.create(
            id='df_phone_001', resource='Candidate', field_key='phone_field',
            label='联系电话', field_type='PHONE',
        )
        DynamicField.objects.create(
            id='df_skill_001', resource='Candidate', field_key='skill_field',
            label='技能', field_type='TEXT',
        )
        DynamicFieldValue.objects.create(
            resource='Candidate', entity_id=candidate.id, field_key='phone_field', value=PHONE,
        )
        DynamicFieldValue.objects.create(
            resource='Candidate', entity_id=candidate.id, field_key='skill_field',
            value=f'熟悉 Python，可联系 {PHONE}',
        )
        _forget(candidate, super_user)

        phone_row = DynamicFieldValue.objects.get(
            resource='Candidate', entity_id=candidate.id, field_key='phone_field')
        assert phone_row.value in (None, '')

        skill_row = DynamicFieldValue.objects.get(
            resource='Candidate', entity_id=candidate.id, field_key='skill_field')
        assert skill_row.value is not None
        assert PHONE not in skill_row.value
        assert '熟悉 Python' in skill_row.value


# ══════════════════════════════════════════════════════════════════
# 4. scraped_resumes (raw 清 / parsed 保结构)
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPurgeScrapedResumes:
    def test_raw_content_cleared_parsed_structure_kept(self, candidate, super_user):
        from apps.scraped_resume.models import ScrapedResume

        ScrapedResume.objects.create(
            source_url='https://example.com/job/1',
            source_platform='lagou',
            raw_content=f'张三 13800000009 邮箱 {EMAIL} 本科毕业于某大学',
            candidate=candidate,
            parsed_content={
                'name': '张三',
                'phone': PHONE,
                'email': EMAIL,
                'education': [{'school': '某大学', 'degree': '本科'}],
                'skills': ['Python', 'Django'],
            },
        )
        _forget(candidate, super_user)

        resume = ScrapedResume.objects.get(candidate=candidate)
        assert resume.raw_content == ''
        # 结构化业务字段保留
        assert resume.parsed_content.get('education') == [{'school': '某大学', 'degree': '本科'}]
        assert resume.parsed_content.get('skills') == ['Python', 'Django']
        # PII 键被清
        assert not resume.parsed_content.get('phone')
        assert not resume.parsed_content.get('email')
        assert not resume.parsed_content.get('name')


# ══════════════════════════════════════════════════════════════════
# 5. 面评 / 备注 / 推荐理由 / 拒信原因 (脱敏, 保业务)
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPurgeTextFields:
    def test_screening_comment_scrubbed(self, candidate, super_user):
        from apps.candidate.models import CandidateScreening
        from apps.core.models import User

        screener = User.objects.create_user(
            username='screener01', password='Test@1234',
        )
        row = CandidateScreening.objects.create(
            candidate=candidate, result='PASS',
            comment=f'技术面通过，候选人手机 {PHONE}，邮箱 {EMAIL}',
            screener=screener,
        )
        _forget(candidate, super_user)
        row.refresh_from_db()
        assert PHONE not in row.comment
        assert EMAIL not in row.comment
        assert '138****0009' in row.comment
        assert '技术面通过' in row.comment  # 业务评价保留

    def test_forward_note_scrubbed(self, candidate, super_user):
        """转发附言 → 脱敏 (转发记录只依赖 User, 构造最轻)。"""
        from apps.candidate.models import CandidateForward
        from apps.core.models import User

        sender = User.objects.create_user(username='fwd_from', password='Test@1234')
        receiver = User.objects.create_user(username='fwd_to', password='Test@1234')
        row = CandidateForward.objects.create(
            candidate=candidate, from_user=sender, to_user=receiver,
            note=f'内推，候选人电话 {PHONE}',
        )
        _forget(candidate, super_user)
        row.refresh_from_db()
        assert PHONE not in row.note
        assert '内推' in row.note

    def test_all_text_specs_registered(self):
        """7 张文本表都要在清理规格里 (用结构断言替代重 fixture 的 DB 用例)。

        这些表的必填外键 (position/application/process) 构造代价高, 用规格表断言
        覆盖"表没漏登记"这一风险, 内容脱敏行为由 CandidateScreening / CandidateForward
        两条真实 DB 用例守住。
        """
        from apps.gdpr.purge import TEXT_SCRUB_SPECS

        registered = {(m.__name__, f) for m, f in TEXT_SCRUB_SPECS}
        expected = {
            ('CandidateScreening', 'comment'),
            ('CandidateForward', 'note'),
            ('CandidatePositionRecommendation', 'reason'),
            ('CandidateRecommendation', 'reason'),
            ('CandidateReasonRecord', 'note'),
            ('Referral', 'note'),
            ('Offer', 'rejection_reason'),
        }
        assert expected <= registered, f'漏登记的文本表: {expected - registered}'


# ══════════════════════════════════════════════════════════════════
# 6. gdpr_requests.submitted_email
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPurgeGdprRequest:
    def test_submitted_email_cleared(self, candidate, super_user):
        req = _forget(candidate, super_user)
        req.refresh_from_db()
        assert req.submitted_email == ''
        assert req.status == GDPRRequestStatus.COMPLETED


# ══════════════════════════════════════════════════════════════════
# 7. 审计链 (脱敏 + 哈希链重算)
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPurgeAuditChain:
    def test_history_detail_scrubbed_and_chain_valid(self, candidate, super_user):
        from apps.candidate.models import CandidateHistory

        CandidateHistory.objects.create(
            candidate=candidate, action='INFO_UPDATED',
            detail={'changes': [
                {'field': 'email', 'label': '邮箱', 'old': 'old@example.com', 'new': EMAIL},
                {'field': 'resume_text', 'label': '简历文本', 'old': '整份简历原文', 'new': '新版'},
                {'field': 'highest_education', 'label': '最高学历', 'old': '大专', 'new': '本科'},
            ], 'source': 'api'},
        )
        _forget(candidate, super_user)

        row = CandidateHistory.objects.filter(
            candidate=candidate, action='INFO_UPDATED').first()
        changes = {c['field']: c for c in row.detail['changes']}
        assert EMAIL not in str(row.detail)
        assert '整份简历原文' not in str(row.detail)
        # 业务字段值保留
        assert changes['highest_education']['old'] == '大专'
        assert changes['highest_education']['new'] == '本科'
        # 变更事实仍在 (old/new 非空)
        assert changes['email']['new']

    def test_chain_recomputed_and_still_valid(self, candidate, super_user):
        """改 detail 后哈希链必须重算 —— 链仍然自洽。

        注: 走不了 HTTP 的 `histories/verify` 端点 —— 被遗忘权执行后候选人已软删,
        而该端点用 `get_object()` (默认 manager 过滤 deleted_at) → 404。
        这里按**端点同一套判定逻辑**直接校验链 (seq 连续 + prev_hash 链接 + row_hash 重算)。
        """
        from apps.candidate.audit import compute_row_hash
        from apps.candidate.models import CandidateHistory

        CandidateHistory.objects.create(
            candidate=candidate, action='INFO_UPDATED',
            detail={'changes': [
                {'field': 'email', 'label': '邮箱', 'old': 'old@example.com', 'new': EMAIL},
            ]},
        )
        _forget(candidate, super_user)

        rows = list(CandidateHistory.objects.filter(candidate_id=candidate.id).order_by('seq'))
        assert rows, '应至少留下一条清理标记行'
        prev = ''
        for idx, row in enumerate(rows, start=1):
            assert row.seq == idx, f'seq 不连续: {row.seq}'
            assert row.prev_hash == prev, f'第 {row.seq} 行 prev_hash 断链'
            recomputed = compute_row_hash(
                candidate.id, row.seq, row.action, row.detail, row.created_by_id, row.prev_hash,
            )
            assert recomputed == row.row_hash, f'第 {row.seq} 行 row_hash 失配 (链被改坏)'
            prev = row.row_hash

    def test_purge_marker_row_appended(self, candidate, super_user):
        """清理动作本身在链上留痕 (GDPR_PII_PURGED 标记行)。"""
        from apps.candidate.models import CandidateHistory

        _forget(candidate, super_user)
        marker = CandidateHistory.objects.filter(
            candidate=candidate, action='GDPR_PII_PURGED',
        ).first()
        assert marker is not None
        assert marker.detail['source'] == 'gdpr_forget'


# ══════════════════════════════════════════════════════════════════
# 8. 软删行也要清理
# ══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPurgeSoftDeletedRows:
    def test_soft_deleted_row_also_purged(self, candidate, super_user):
        """软删行同样持有 PII, 必须一并清理。"""
        from apps.candidate.models import CandidateScreening
        from apps.core.models import User

        screener = User.objects.create_user(
            username='screener02', password='Test@1234',
        )
        row = CandidateScreening.objects.create(
            candidate=candidate, result='FAIL',
            comment=f'不通过，联系方式 {PHONE}',
            screener=screener,
        )
        row.soft_delete()
        _forget(candidate, super_user)
        row.refresh_from_db()
        assert PHONE not in row.comment


# ══════════════════════════════════════════════════════════════════
# 9. 审计写入端治本
# ══════════════════════════════════════════════════════════════════

class TestAuditWriterNoRawPII:
    """写入端不再落 PII 原值 —— 否则每次改简历都会再产生一份副本 (打地鼠)。"""

    def test_diff_fields_redacts_pii_values(self):
        from apps.candidate.audit import diff_fields

        changes = diff_fields(
            {'email': 'old@example.com', 'resume_text': '整份简历原文', 'highest_education': '大专'},
            {'email': 'new@example.com', 'resume_text': '新版原文', 'highest_education': '本科'},
            ['email', 'resume_text', 'highest_education'],
        )
        by_field = {c['field']: c for c in changes}
        assert 'old@example.com' not in str(changes)
        assert 'new@example.com' not in str(changes)
        assert '整份简历原文' not in str(changes)
        assert '新版原文' not in str(changes)
        # 业务字段原样
        assert by_field['highest_education']['old'] == '大专'
        assert by_field['highest_education']['new'] == '本科'

    def test_diff_fields_still_detects_change_after_redaction(self):
        """脱敏后仍要能识别真实变更 (否则会漏记审计)。"""
        from apps.candidate.audit import diff_fields

        changes = diff_fields(
            {'email': 'ab@example.com'}, {'email': 'ac@example.com'}, ['email'],
        )
        assert len(changes) == 1

    def test_scrub_text_masks_id_card_and_email(self):
        assert ID_CARD not in scrub_text(f'证件 {ID_CARD}')
        assert EMAIL not in scrub_text(f'邮箱 {EMAIL}')
