"""QA-4 Round-2 黑盒 HTTP 验证：BUG-3 / BUG-4 / BUG-1 写链路修复。

工程师 commit 1e1ed1e 声称：
- BUG-4 (P0): create_candidate 里 `id_card_no=id_card` 在未填身份证时为 None,
  该列 null=False -> IntegrityError。改为 `id_card_no=id_card or ''`。
  故「不传 id_card_no 创建候选人」(最常见路径) 之前 100% 500, 现在应 201。
- BUG-3 (P0): CandidateHistory 继承 FullAuditModel, 没有 operator 字段,
  12 处 `operator=actor` 直接 TypeError。已统一改 `created_by=actor`。
  写操作后 CandidateHistory.created_by 应正确落库, 详情接口不应 500。
- BUG-1 (P0, f8708c9): 身份证查重走不可逆 id_card_hash 列。

本文件用真实 HTTP (DRF APIClient) 打 /api/v1/candidates/, 不经模型直连,
是候选人写链路唯一的护栏。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.candidate.models import Candidate, CandidateHistory
from apps.common.encryption import hash_for_search

VALID_ID = '110101199003071233'  # 校验码合法 (110101 + 19900307 + 123 + 3)


@pytest.fixture
def _auth(db, super_user):
    client = APIClient()
    refresh = RefreshToken.for_user(super_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client, super_user


def test_bug4_create_without_id_card_no_returns_201(_auth):
    """BUG-4: 不传 id_card_no 创建候选人 (最常见路径), 之前 100% 500, 现在应 201。"""
    client, user = _auth
    resp = client.post('/api/v1/candidates/', {
        'name': '张三',
        'phone': '13800000001',
    }, format='json')
    assert resp.status_code == 201, resp.content[:500]
    # 信封收口后创建接口返回 {success, data:{...}}
    body = resp.json()['data']
    assert body['name'] == '张三'
    # 落库后 id_card_no 应为空串 (不是 None / 不是崩溃)
    c = Candidate.objects.get(pk=body['id'])
    assert c.id_card_no == ''


def test_bug3_history_created_by_populated_not_operator(_auth):
    """BUG-3: 写历史操作人字段是 created_by, 不存在 operator 字段。"""
    client, user = _auth
    resp = client.post('/api/v1/candidates/', {
        'name': '李四',
        'phone': '13800000002',
        'id_card_no': VALID_ID,
    }, format='json')
    assert resp.status_code == 201, resp.content[:500]
    cid = resp.json()['data']['id']
    hist = CandidateHistory.objects.filter(candidate_id=cid).first()
    assert hist is not None, 'CandidateHistory 未写入'
    assert hist.created_by_id == user.pk, 'created_by 未落库为操作人'
    assert not hasattr(hist, 'operator'), 'CandidateHistory 不应存在 operator 字段'


def test_bug3_detail_endpoint_no_500(_auth):
    """BUG-3 连带: 详情接口序列化 history 不应 500 (之前 operator 字段缺失会 500)。"""
    client, user = _auth
    resp = client.post('/api/v1/candidates/', {
        'name': '王五',
        'phone': '13800000003',
    }, format='json')
    assert resp.status_code == 201, resp.content[:500]
    cid = resp.json()['data']['id']
    detail = client.get(f'/api/v1/candidates/{cid}/')
    assert detail.status_code == 200, detail.content[:500]


def test_bug1_duplicate_id_card_deduped_via_hash(_auth):
    """BUG-1: 同一身份证号重复提交应走 id_card_hash 查重命中, 不重复入库。"""
    client, user = _auth
    r1 = client.post('/api/v1/candidates/', {
        'name': '甲',
        'phone': '13800000011',
        'id_card_no': VALID_ID,
    }, format='json')
    assert r1.status_code == 201, r1.content[:500]
    id1 = r1.json()['data']['id']

    # 同身份证, 但手机/姓名都不同 -> 只能靠 id_card_hash 命中查重
    r2 = client.post('/api/v1/candidates/', {
        'name': '乙',
        'phone': '13900000022',
        'id_card_no': VALID_ID,
    }, format='json')
    assert r2.status_code == 201, r2.content[:500]
    assert r2.json()['data']['id'] == id1, '同一身份证应返回已存在的候选人'
    assert Candidate.objects.count() == 1, '身份证查重失效, 重复入库'
    assert Candidate.objects.first().id_card_hash == hash_for_search(VALID_ID)
