"""候选人合并 merge 端点测试.

背景 (2026-10-08 审查):
    `CandidateViewSet.merge` (views.py) 是**不可逆**写操作 —— 会把从候选人的
    申请/历史迁移到主候选人, 并**软删**从候选人。但全仓检索 `merge` 命中 0 个测试,
    且原实现完全不校验数据范围: 知道 id 就能合并任意部门的候选人。

测试分层 (避免"用没权限的用户测出 403"这种假绿):
    - 语义类用例用 `hr_user`: 具备 candidate 全权限且数据范围为全量,
      专测合并逻辑本身。
    - 越权类用例用 `hr_dept_a` + 把 has_perm 打桩成恒 True: 这样 403 只可能来自
      **数据范围**守卫, 而不是"用户本来就没权限"。
"""
import pytest
from rest_framework.test import APIClient

from apps.candidate.models import Candidate, CandidateHistory

MERGE_URL = '/api/v1/candidates/merge/'


def _mk(cand_id, name, phone, created_by, **extra):
    return Candidate.objects.create(
        id=cand_id, name=name, phone=phone, created_by=created_by, **extra,
    )


@pytest.fixture
def client_for():
    def _make(user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c
    return _make


def _payload(resp):
    """信封可能包一层 data, 统一取出业务体。"""
    body = resp.json()
    return body.get('data', body) if isinstance(body, dict) else body


# ---------------------------------------------------------------- 合并语义

@pytest.mark.django_db
def test_merge_migrates_history_and_soft_deletes_duplicate(client_for, hr_user):
    """合并后: 主候选保留, 从候选软删, 历史改指主候选。"""
    primary = _mk('cand-m-p', '主候选人', '13800001001', hr_user)
    dup = _mk('cand-m-d', '重复候选人', '13800001002', hr_user)

    CandidateHistory.objects.create(
        candidate=dup, action='CREATED', detail={'x': 1}, created_by=hr_user,
    )
    assert CandidateHistory.objects.filter(candidate=dup).count() == 1

    resp = client_for(hr_user).post(
        MERGE_URL,
        {'primary_id': primary.id, 'duplicate_ids': [dup.id]},
        format='json',
    )

    assert resp.status_code == 200, resp.content
    body = _payload(resp)
    assert body['primaryId'] == primary.id
    assert dup.id in body['mergedFrom']

    dup.refresh_from_db()
    primary.refresh_from_db()
    assert dup.deleted_at is not None, '从候选人应被软删'
    assert primary.deleted_at is None, '主候选人必须保留'
    assert CandidateHistory.objects.filter(candidate=primary, action='MERGED').count() == 1
    assert CandidateHistory.objects.filter(candidate=dup, action='CREATED').count() == 0


@pytest.mark.django_db
def test_merge_backfills_empty_fields_and_tags(client_for, hr_user):
    """主候选空字段由从候选补齐, tags 去重合并。"""
    primary = _mk('cand-m-p2', '主候选人', '13800001003', hr_user, tags=['A'])
    dup = _mk('cand-m-d2', '重复候选人', '13800001004', hr_user,
              tags=['A', 'B'], current_city='上海', email='dup@example.com')

    resp = client_for(hr_user).post(
        MERGE_URL,
        {'primary_id': primary.id, 'duplicate_ids': [dup.id]},
        format='json',
    )

    assert resp.status_code == 200, resp.content
    primary.refresh_from_db()
    assert primary.current_city == '上海'
    assert primary.email == 'dup@example.com'
    assert set(primary.tags) == {'A', 'B'}


@pytest.mark.django_db
def test_merge_skips_self_and_unknown_ids(client_for, hr_user):
    """primary 出现在 duplicate_ids 中时不得软删自己; 不存在的 id 跳过不报错。"""
    primary = _mk('cand-m-p3', '主候选人', '13800001005', hr_user)

    resp = client_for(hr_user).post(
        MERGE_URL,
        {'primary_id': primary.id,
         'duplicate_ids': [primary.id, 'cand-not-exist']},
        format='json',
    )

    assert resp.status_code == 200, resp.content
    primary.refresh_from_db()
    assert primary.deleted_at is None, '主候选人不得因自合并被软删'


@pytest.mark.django_db
def test_merge_writes_history_with_actor(client_for, hr_user):
    """合并必须留痕且记录操作人, 便于事后追溯谁动了数据。"""
    primary = _mk('cand-m-p6', '主候选人', '13800001010', hr_user)
    dup = _mk('cand-m-d6', '重复候选人', '13800001011', hr_user)

    resp = client_for(hr_user).post(
        MERGE_URL,
        {'primary_id': primary.id, 'duplicate_ids': [dup.id]},
        format='json',
    )

    assert resp.status_code == 200, resp.content
    history = CandidateHistory.objects.filter(candidate=primary, action='MERGED').first()
    assert history is not None
    assert history.created_by_id == hr_user.id
    assert history.detail.get('merged_from') == dup.id


# ---------------------------------------------------------------- 数据范围越权

@pytest.fixture
def _all_perms(monkeypatch):
    """把资源级权限判定打桩为恒 True, 使 403 只可能来自数据范围守卫。"""
    from apps.core import permissions_v2 as pv2
    monkeypatch.setattr(pv2, 'has_perm', lambda user, code: True)
    return None


@pytest.mark.django_db
def test_merge_denied_for_out_of_scope_candidate(_all_perms, client_for,
                                                 hr_dept_a, hr_dept_b):
    """核心回归: 不得合并数据范围之外的候选人 (原实现无任何校验)。"""
    primary = _mk('cand-m-p4', '主候选人', '13800001006', hr_dept_a)
    foreign = _mk('cand-m-f4', '他人候选人', '13800001007', hr_dept_b)

    resp = client_for(hr_dept_a).post(
        MERGE_URL,
        {'primary_id': primary.id, 'duplicate_ids': [foreign.id]},
        format='json',
    )

    assert resp.status_code == 403, resp.content
    foreign.refresh_from_db()
    primary.refresh_from_db()
    assert foreign.deleted_at is None, '越权的从候选人绝不能被软删'
    assert primary.deleted_at is None
    assert CandidateHistory.objects.filter(action='MERGED').count() == 0


@pytest.mark.django_db
def test_merge_denied_when_primary_out_of_scope(_all_perms, client_for,
                                                hr_dept_a, hr_dept_b):
    """主候选人越权同样拦截。"""
    primary = _mk('cand-m-p5', '他人候选人', '13800001008', hr_dept_b)
    mine = _mk('cand-m-m5', '我的候选人', '13800001009', hr_dept_a)

    resp = client_for(hr_dept_a).post(
        MERGE_URL,
        {'primary_id': primary.id, 'duplicate_ids': [mine.id]},
        format='json',
    )

    assert resp.status_code == 403, resp.content
    mine.refresh_from_db()
    assert mine.deleted_at is None, '越权请求不得软删自己可见的数据'


# ---------------------------------------------------------------- 守卫单元层

@pytest.mark.django_db
def test_assert_candidates_visible_reports_invisible(rf, hr_dept_a, hr_dept_b):
    """scope 助手本身: 只把不可见的 id 报出来, 不影响可见的。"""
    from apps.candidate.scope import assert_candidates_visible

    mine = _mk('cand-v-mine', '我的', '13800002001', hr_dept_a)
    foreign = _mk('cand-v-foreign', '他人的', '13800002002', hr_dept_b)

    req = rf.post('/x/')
    req.user = hr_dept_a
    req.recruit_type = 'social'

    invisible = assert_candidates_visible(req, [mine.id, foreign.id])
    assert mine.id not in invisible
    assert foreign.id in invisible
