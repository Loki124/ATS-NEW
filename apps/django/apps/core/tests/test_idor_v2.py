"""IDOR / 越权测试.

验证: 无权限者被拒、超管放行, 以及**跨部门**数据隔离。

2026-10-08 修正:
    原文件里有两处"双值断言" —— `assert res.status_code in (200, 403)` 与
    `in (401, 403)`。这等于同时接受"通过"和"拒绝", **越权测试形同虚设**
    (审查报告 S-02 / 测试项 P0-3)。已全部改为单值精确断言。

    另: 跨部门场景统一把 `has_perm` 打桩为恒 True, 这样 403/404 只可能来自
    **数据范围**守卫, 而不是"用户本来就没权限" —— 避免用错误的理由得到正确的结果。
"""
import pytest
from rest_framework.test import APIClient

from apps.candidate.models import Candidate

User = __import__('django.contrib.auth', fromlist=['get_user_model']).get_user_model()


@pytest.fixture
def interviewer(db):
    return User.objects.create_user(
        username='iv_user', password='x',
        is_staff=False, is_superuser=False,
    )


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='admin_user', password='x',
        is_staff=True, is_superuser=True,
    )


@pytest.fixture
def all_perms(monkeypatch):
    """把资源级权限判定打桩为恒 True, 使失败只可能源于数据范围。"""
    from apps.core import permissions_v2 as pv2
    monkeypatch.setattr(pv2, 'has_perm', lambda user, code: True)
    return None


def _ids(payload):
    rows = payload.get('data', payload)
    return {r['id'] for r in rows} if isinstance(rows, list) else set()


# ---------------------------------------------------------------- 权限基线

@pytest.mark.django_db
@pytest.mark.v2_permission
def test_interviewer_cannot_create_offer(interviewer):
    """无 offer:create 权限的面试官不得创建 Offer。"""
    client = APIClient()
    client.force_authenticate(user=interviewer)
    res = client.post('/api/v1/offers/', {'candidate': 1, 'amount': 100}, format='json')
    assert res.status_code == 403, res.content


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_hr_user_with_role_can_list_offers(hr_user):
    """具备 offer:list 的 HR 角色可以列出 Offer (原用例接受 200/403, 已收紧为 200)。"""
    client = APIClient()
    client.force_authenticate(user=hr_user)
    res = client.get('/api/v1/offers/')
    assert res.status_code == 200, res.content


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_admin_full_access(admin):
    client = APIClient()
    client.force_authenticate(user=admin)
    assert client.get('/api/v1/offers/').status_code == 200
    assert client.get('/api/v1/candidates/').status_code == 200


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_anonymous_blocked():
    """未认证必须 401 (JWT 会带 WWW-Authenticate), 原用例接受 401/403, 已收紧。"""
    client = APIClient()
    res = client.get('/api/v1/offers/')
    assert res.status_code == 401, res.content


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_superuser_bypass_via_is_superuser(admin):
    """is_superuser=True 应 bypass 所有 V2 permission check."""
    client = APIClient()
    client.force_authenticate(user=admin)
    assert client.get('/api/v1/permissions/resources/').status_code == 200
    assert client.get('/api/v1/permissions/templates/').status_code == 200
    assert client.get('/api/v1/permissions/roles/').status_code == 200


# ---------------------------------------------------------------- 跨部门矩阵

@pytest.mark.django_db
@pytest.mark.v2_permission
def test_cross_dept_candidate_list_isolated(all_perms, hr_dept_a, hr_dept_b):
    """A 部门 HR 的候选人列表不得包含 B 部门的数据。"""
    mine = Candidate.objects.create(
        id='idor-c-a', name='A部门候选人', phone='13800004001',
        created_by=hr_dept_a, referrer=hr_dept_a,
    )
    foreign = Candidate.objects.create(
        id='idor-c-b', name='B部门候选人', phone='13800004002',
        created_by=hr_dept_b, referrer=hr_dept_b,
    )

    client = APIClient()
    client.force_authenticate(user=hr_dept_a)
    res = client.get('/api/v1/candidates/')

    assert res.status_code == 200, res.content
    listed = _ids(res.json())
    assert mine.id in listed, '自己范围内的数据必须可见 (否则是用空结果假绿)'
    assert foreign.id not in listed, 'B 部门候选人泄漏给了 A 部门 HR'


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_cross_dept_candidate_detail_forbidden(all_perms, hr_dept_a, hr_dept_b):
    """A 部门 HR 直接按 id 取 B 部门候选人详情 → 404。"""
    foreign = Candidate.objects.create(
        id='idor-d-b', name='B部门候选人', phone='13800004003',
        created_by=hr_dept_b, referrer=hr_dept_b,
    )
    client = APIClient()
    client.force_authenticate(user=hr_dept_a)
    res = client.get(f'/api/v1/candidates/{foreign.id}/')
    assert res.status_code == 404, res.content


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_cross_dept_resume_fields_forbidden(all_perms, hr_dept_a, hr_dept_b):
    """扩展简历字段读写: 越权一律 404 (该端点曾为纯 IDOR, 只校验候选人是否存在)。"""
    foreign = Candidate.objects.create(
        id='idor-r-b', name='B部门候选人', phone='13800004004',
        created_by=hr_dept_b, referrer=hr_dept_b,
    )
    url = f'/api/v1/candidates/{foreign.id}/resume-fields/'
    client = APIClient()
    client.force_authenticate(user=hr_dept_a)

    assert client.get(url).status_code == 404
    assert client.put(url, {'values': {'k': 'v'}}, format='json').status_code == 404


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_cross_dept_candidate_merge_forbidden(all_perms, hr_dept_a, hr_dept_b):
    """越权合并必须被拒, 且不产生任何副作用。"""
    mine = Candidate.objects.create(
        id='idor-m-a', name='A部门候选人', phone='13800004005',
        created_by=hr_dept_a, referrer=hr_dept_a,
    )
    foreign = Candidate.objects.create(
        id='idor-m-b', name='B部门候选人', phone='13800004006',
        created_by=hr_dept_b, referrer=hr_dept_b,
    )
    client = APIClient()
    client.force_authenticate(user=hr_dept_a)
    res = client.post(
        '/api/v1/candidates/merge/',
        {'primary_id': mine.id, 'duplicate_ids': [foreign.id]},
        format='json',
    )

    assert res.status_code == 403, res.content
    foreign.refresh_from_db()
    assert foreign.deleted_at is None
