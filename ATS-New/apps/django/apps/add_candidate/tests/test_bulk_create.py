"""BulkCreateService 单元测试

覆盖：
- 3 方向路由：pending / talent / position
- 混合方向（同一 batch 含 3 种方向）
- 必填字段校验（name/phone/email）
- 占用状态下阻止创建
- 部分失败 rollback（事务）
"""
import pytest
from django.db import transaction
from apps.add_candidate.services.bulk_create import (
    BulkCreateService,
    BulkCreateDraft,
    BulkCreateResult,
    BulkCreateError,
)


@pytest.fixture
def draft_pending():
    return BulkCreateDraft(
        draft_id='draft_001',
        direction='pending',
        name='张三',
        phone='13800138001',
        email='zhang@test.com',
        parsed_data={},
        channel='招聘网站',
        source='Boss直聘',
        provider='',
    )


@pytest.fixture
def draft_position(published_position):
    return BulkCreateDraft(
        draft_id='draft_002',
        direction='position',
        position_id=str(published_position.id),
        name='李四',
        phone='13800138002',
        email='li@test.com',
        parsed_data={},
        channel='内推',
        source='员工推荐',
        provider='王五',
    )


@pytest.fixture
def draft_talent():
    return BulkCreateDraft(
        draft_id='draft_003',
        direction='talent',
        name='孙六',
        phone='13800138003',
        email='sun@test.com',
        parsed_data={},
        channel='招聘网站',
        source='LinkedIn',
        provider='',
    )


class TestBulkCreateService:
    """3 方向路由"""

    def test_pending_creates_candidate_only(
        self, draft_pending, hr_user,
    ):
        """pending 方向：仅创建 Candidate，无 Application/TalentPoolEntry"""
        result = BulkCreateService.create_batch(
            drafts=[draft_pending],
            actor=hr_user,
        )
        # result.created_candidate_ids 是 candidate.id（nanoid），按 phone 找 candidate
        from apps.candidate.models import Candidate
        cand = Candidate.objects.get(phone='13800138001')
        assert result.created_candidate_ids == [str(cand.id)]
        assert result.route == {'draft_001': 'pending'}

        assert cand.name == '张三'
        assert cand.applications.count() == 0
        assert cand.talent_pool_entries.count() == 0

    def test_position_creates_candidate_and_application(
        self, draft_position, hr_user, published_position,
    ):
        """position 方向：创建 Candidate + Application(state=ACTIVE)"""
        result = BulkCreateService.create_batch(
            drafts=[draft_position],
            actor=hr_user,
        )

        from apps.application.models import Application, ApplicationState
        from apps.candidate.models import Candidate
        cand = Candidate.objects.get(phone='13800138002')
        assert result.created_candidate_ids == [str(cand.id)]

        app = Application.objects.get(candidate=cand)
        assert app.position == published_position
        assert app.state == ApplicationState.ACTIVE
        # 注：Application 模型没有 channel/source/referrer 字段
        # 渠道/来源/推荐人信息存到 Candidate.extra（V2 流程的统一存储位置）
        assert cand.extra.get('channel') == '内推'
        assert cand.extra.get('source') == '员工推荐'
        assert cand.extra.get('provider') == '王五'

    def test_talent_creates_candidate_and_talent_pool_entry(
        self, draft_talent, hr_user,
    ):
        """talent 方向：创建 Candidate + TalentPoolEntry(source=DIRECT_IMPORT)"""
        result = BulkCreateService.create_batch(
            drafts=[draft_talent],
            actor=hr_user,
        )

        from apps.candidate.models import Candidate
        from apps.talent_pool.models import TalentPoolEntry
        cand = Candidate.objects.get(phone='13800138003')
        assert result.created_candidate_ids == [str(cand.id)]

        entry = TalentPoolEntry.objects.get(candidate=cand)
        assert entry.source == TalentPoolEntry.EntrySource.DIRECT_IMPORT

    def test_mixed_directions(
        self, draft_pending, draft_position, draft_talent, hr_user,
    ):
        """混合方向：同一 batch 含 3 种方向"""
        result = BulkCreateService.create_batch(
            drafts=[draft_pending, draft_position, draft_talent],
            actor=hr_user,
        )
        from apps.candidate.models import Candidate
        cands = {
            '张三': Candidate.objects.get(phone='13800138001'),
            '李四': Candidate.objects.get(phone='13800138002'),
            '孙六': Candidate.objects.get(phone='13800138003'),
        }
        assert len(result.created_candidate_ids) == 3
        assert sorted(result.created_candidate_ids) == sorted([str(c.id) for c in cands.values()])
        assert result.route == {
            'draft_001': 'pending',
            'draft_002': 'position',
            'draft_003': 'talent',
        }

    def test_missing_required_fields_raises_error(self, hr_user):
        """必填字段缺失 → BulkCreateError"""
        bad_draft = BulkCreateDraft(
            draft_id='draft_bad',
            direction='pending',
            name='',  # 空
            phone='13800138099',
            email='ok@test.com',
            parsed_data={},
        )
        with pytest.raises(BulkCreateError) as exc_info:
            BulkCreateService.create_batch(drafts=[bad_draft], actor=hr_user)
        assert 'name' in str(exc_info.value)

    def test_position_direction_requires_position_id(self, hr_user):
        """position 方向必须提供 position_id"""
        bad_draft = BulkCreateDraft(
            draft_id='draft_bad',
            direction='position',
            position_id=None,  # 缺失
            name='王五',
            phone='13800138099',
            email='ok@test.com',
            parsed_data={},
        )
        with pytest.raises(BulkCreateError) as exc_info:
            BulkCreateService.create_batch(drafts=[bad_draft], actor=hr_user)
        assert 'position_id' in str(exc_info.value)

    def test_rollback_on_partial_failure(self, draft_pending, hr_user):
        """部分失败 → 全部 rollback"""
        # draft_pending 合法，下一个 draft 缺字段
        bad_draft = BulkCreateDraft(
            draft_id='draft_bad',
            direction='position',
            position_id=None,
            name='Bad',
            phone='13800138099',
            email='ok@test.com',
            parsed_data={},
        )
        with pytest.raises(BulkCreateError):
            BulkCreateService.create_batch(
                drafts=[draft_pending, bad_draft],
                actor=hr_user,
            )
        # 验证 draft_pending 也没创建
        from apps.candidate.models import Candidate
        assert not Candidate.objects.filter(phone='13800138001').exists()

    def test_idempotency_same_draft_id_twice(self, draft_pending, hr_user):
        """同一 draft_id 重复调用 → 不创建第二个（去重）"""
        BulkCreateService.create_batch(drafts=[draft_pending], actor=hr_user)
        # 第二次
        result2 = BulkCreateService.create_batch(drafts=[draft_pending], actor=hr_user)
        # 返回相同 ID，不报错
        # 注：created_candidate_ids 实际是 candidate.id（nanoid），但同一 draft 两次调用应返回相同 ID
        from apps.candidate.models import Candidate
        first_cand = Candidate.objects.get(phone='13800138001')
        assert result2.created_candidate_ids == [str(first_cand.id)]
        assert Candidate.objects.filter(phone='13800138001').count() == 1