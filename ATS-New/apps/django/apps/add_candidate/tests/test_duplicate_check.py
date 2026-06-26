"""DuplicateCheckService 单元测试

覆盖 5 种判定分支：
1. Moka ID 命中 + 有 active application → occupied
2. ID card 命中 + 有 active application → occupied
3. ID card 命中 + 无 active application → unocc
4. 手机号命中（无 ID card）→ unocc 或 occupied 取决于 application
5. 邮箱命中（无手机）→ unocc
6. 全无命中 → clean
"""
import pytest
from apps.add_candidate.services.duplicate_check import (
    DuplicateCheckService,
    DuplicateStatus,
    DuplicateInfo,
)


@pytest.fixture
def candidate_with_active_app(db, published_position, hr_user):
    """存在候选人 + 有 active application"""
    from apps.candidate.models import Candidate
    from apps.application.models import Application, ApplicationState
    cand = Candidate.objects.create(
        name='张三',
        phone='13800138001',
        email='zhang@test.com',
        id_card_no='110101199605151234',
    )
    # 注：Application 模型要求 process + workflow_version + code 必填
    # （plan 里的 create() 调用遗漏这三个字段，按模型实际 schema 补齐）
    Application.objects.create(
        candidate=cand,
        position=published_position,
        process=published_position.process,
        workflow_version=published_position.process.current_version,
        code=f'APP-ACTIVE-{cand.id}',
        state=ApplicationState.ACTIVE,
    )
    return cand


@pytest.fixture
def candidate_archived_only(db, published_position, hr_user):
    """存在候选人 + 只有归档 application（无 active）"""
    from apps.candidate.models import Candidate
    from apps.application.models import Application, ApplicationState
    cand = Candidate.objects.create(
        name='李四',
        phone='13800138002',
        email='li@test.com',
        id_card_no='110101199801011234',
    )
    # 注：Application 模型要求 process + workflow_version + code 必填
    Application.objects.create(
        candidate=cand,
        position=published_position,
        process=published_position.process,
        workflow_version=published_position.process.current_version,
        code=f'APP-REJ-{cand.id}',
        state=ApplicationState.REJECTED,  # 终态
    )
    return cand


class TestDuplicateCheckService:
    """5 种判定分支"""

    def test_clean_when_no_match(self, db):
        """全无命中 → clean"""
        result = DuplicateCheckService.find(
            phone='13900000001',
            email='unique@test.com',
            id_card='999999999999999999',
            moka_id='moka_unique_001',
        )
        assert result.status == DuplicateStatus.CLEAN
        assert result.matched_candidate is None
        assert result.active_application_id is None

    def test_occupied_when_matched_with_active_app(
        self, candidate_with_active_app
    ):
        """手机号命中 + 有 active application → occupied"""
        result = DuplicateCheckService.find(
            phone='13800138001',
            email='other@test.com',
            id_card=None,
            moka_id=None,
        )
        assert result.status == DuplicateStatus.OCCUPIED
        assert result.matched_candidate == candidate_with_active_app
        assert result.active_application_id is not None

    def test_unocc_when_matched_without_active_app(
        self, candidate_archived_only
    ):
        """手机号命中 + 无 active application → unocc"""
        result = DuplicateCheckService.find(
            phone='13800138002',
            email='other@test.com',
            id_card=None,
            moka_id=None,
        )
        assert result.status == DuplicateStatus.UNOCC
        assert result.matched_candidate == candidate_archived_only
        assert result.active_application_id is None

    def test_id_card_takes_priority_over_phone(
        self, candidate_with_active_app
    ):
        """ID card 优先于 phone 匹配"""
        result = DuplicateCheckService.find(
            phone='13900000999',  # 不匹配
            email='other@test.com',
            id_card='110101199605151234',  # 匹配
            moka_id=None,
        )
        assert result.status == DuplicateStatus.OCCUPIED
        assert result.matched_candidate == candidate_with_active_app

    def test_moka_id_takes_priority_over_id_card(
        self, candidate_with_active_app
    ):
        """Moka ID 优先于 ID card"""
        from apps.candidate.models import Candidate
        Candidate.objects.filter(id=candidate_with_active_app.id).update(
            moka_candidate_id='moka_zhang_001',
        )
        result = DuplicateCheckService.find(
            phone='13900000999',
            email='other@test.com',
            id_card='999999999999999999',  # 不匹配
            moka_id='moka_zhang_001',  # 匹配
        )
        assert result.status == DuplicateStatus.OCCUPIED
        assert result.matched_candidate.id == candidate_with_active_app.id

    def test_email_fallback_when_no_phone_no_id_card(
        self, candidate_archived_only
    ):
        """无手机无身份证，邮箱命中 → unocc"""
        result = DuplicateCheckService.find(
            phone=None,
            email='li@test.com',
            id_card=None,
            moka_id=None,
        )
        assert result.status == DuplicateStatus.UNOCC
        assert result.matched_candidate == candidate_archived_only

    def test_info_dict_contains_required_fields(
        self, candidate_with_active_app
    ):
        """DuplicateInfo.to_dict() 包含前端所需字段"""
        result = DuplicateCheckService.find(
            phone='13800138001',
            email='other@test.com',
            id_card=None,
            moka_id=None,
        )
        info = result.to_dict()
        assert 'status' in info
        assert 'existing_resume_id' in info
        assert 'created_at' in info
        assert 'history' in info
        assert 'cur_status_label' in info
        assert 'active_application_id' in info
        assert info['status'] == 'occupied'
        assert info['cur_status_label'] == '已占用 · 面试中，不可合并'

    def test_unocc_info_label(self, candidate_archived_only):
        """unocc 状态显示「未占用 · 可安全合并」"""
        result = DuplicateCheckService.find(
            phone='13800138002',
            email=None,
            id_card=None,
            moka_id=None,
        )
        info = result.to_dict()
        assert info['cur_status_label'] == '未占用 · 可安全合并'