"""M07 长尾：批量 / 合并入口的**端点级行为**验证（真 HTTP 请求 + 真落库断言）。

与同目录两个文件的分工：
  - ``test_write_guard.py``     : 静态守卫（源码里有没有守卫 / 有没有退回全表取）
  - ``test_batch_write_scope.py``: helper 层单测（scope helper 的纯语义）
  - **本文件**                    : 端点级黑盒 —— 真发请求，看**真的返回码、真的落不落库**

为什么必须有第三层
=================
静态守卫只能证明"代码里写了 is_writable"，不能证明"守卫真的生效"。历史上最容易
出现的假绿是：守卫调用写了，但响应壳/异常分支把它吞了、或者失败后仍然落了库。
本文件全部走 ``APIClient`` 真请求，并逐条断言 DB 状态。

覆盖的三个缺口
==============
1. ``process.batch_screen`` / ``batch_recommend``
   越权候选人 -> ``NO_WRITE_PERMISSION`` 且 **不落库**；
   不存在的 id -> ``CANDIDATE_NOT_FOUND``（沿用历史语义，不被新守卫误伤）；
   可写候选人 -> 正常落库。
2. ``candidate.merge``
   可见但不可写 -> 403 且**不合并**（不软删 duplicate）。
3. 无 WRITE 规则时全部 fail-open，既有功能权限不变（防回归）。

角色构造
========
本文件踩过两个坑, 记录下来避免下次重蹈:

1. **必须非超管**。``write_scope_q`` 对 ``is_super_admin`` 直接返回 None(恒放行),
   用超管测写范围等于什么都没测。
2. **必须给角色授资源码**。V2Permission 走 ``RolePermissionV2`` 判功能权限,
   光挂角色不给 ``RolePermissionV2`` 行会直接 403("未定义 recruit:candidate:edit"),
   请求根本进不到业务代码 —— 那样测的就不是写范围守卫了。
   故 ``actor`` fixture 同时登记 PermissionResource + 授 list/edit 资源码。
"""
import pytest
from rest_framework.test import APIClient

from apps.candidate.models import Candidate
from apps.core.models import Department, User
from apps.core.models_permission_v2 import (
    PermissionResource,
    RolePermissionV2,
    RoleV2,
    UserRoleV2,
)
from apps.data_permission.models import DataPermissionRule, RowScopeAccess, RowScopeType
from apps.process.models import CandidateRecommendation, CandidateScreen, RecruitmentProcess

ROLE_CODE = 'M07_BATCH_ENDPOINT_ROLE'

# 本文件涉及的 ViewSet 声明的权限码(permission_required / 派生 :edit)。
RESOURCE_CODES = (
    'recruit:candidate:list',
    'recruit:candidate:edit',
    'recruit:settings:recruitment-process:list',
    'recruit:settings:recruitment-process:edit',
)


def _write_rule(scope_type, payload=None):
    """建写范围规则, 并**顺带建一条 READ=ALL 规则把读范围放开**。

    为什么必须配 READ=ALL: 读范围(role_entity_scope_q / scope_filter_q)默认按部门或
    管理单元裁剪, 候选人在本测试里是凭空造的(无部门归属), 会先被读范围判成"不可见",
    于是返回的是 ``CANDIDATE_NOT_FOUND`` 而不是 ``NO_WRITE_PERMISSION`` —— 测的就不是
    写范围守卫了。配 READ=ALL 后读范围全量可见, 请求必定走到写范围判定分支,
    断言才真正对准 M07。
    """
    DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value=ROLE_CODE, level='ROW',
        row_access=RowScopeAccess.READ, entity='candidate',
        scope_type=RowScopeType.ALL, scope_payload=None, status=1,
    )
    return DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value=ROLE_CODE, level='ROW',
        row_access=RowScopeAccess.WRITE, entity='candidate',
        scope_type=scope_type, scope_payload=payload, status=1,
    )


def _read_all_rule():
    """只建 READ=ALL(不建 WRITE), 用于"无写规则 -> fail-open"用例。"""
    return DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value=ROLE_CODE, level='ROW',
        row_access=RowScopeAccess.READ, entity='candidate',
        scope_type=RowScopeType.ALL, scope_payload=None, status=1,
    )


def _grant_resources(role_code):
    """登记资源并把 list/edit 全授给该角色, 让 V2Permission 放行到业务代码。"""
    for code in RESOURCE_CODES:
        PermissionResource.objects.get_or_create(
            resource_code=code,
            defaults={'resource_name': code, 'resource_type': 'BUTTON',
                      'system_code': 'recruit', 'status': 1},
        )
        RolePermissionV2.objects.get_or_create(
            role_code=role_code, resource_code=code,
            defaults={'system_code': 'recruit'},
        )
    # 让 V2Permission 的 action 派生不再回退(仅影响日志噪音, 不影响判定)
    from apps.core.permissions_v2 import invalidate_known_codes
    invalidate_known_codes()


def _user(username, role=ROLE_CODE):
    dept, _ = Department.objects.get_or_create(
        id=f'D_{username}', defaults={'name': username})
    u = User.objects.create(username=username, department=dept)
    if role:
        UserRoleV2.objects.get_or_create(
            user_id=u.pk, role_code=role, system_code='recruit')
    return u


@pytest.fixture
def actor(department):
    """受测操作人：持自定义角色 + 资源权限, 非超管, 真正走到写范围判定。"""
    RoleV2.objects.get_or_create(
        system_code='recruit', role_code=ROLE_CODE,
        defaults={'role_name': 'M07 批量端点角色', 'status': 1},
    )
    _grant_resources(ROLE_CODE)
    return _user('m07_batch_actor')


@pytest.fixture
def client(actor):
    c = APIClient()
    c.force_authenticate(user=actor)
    return c


@pytest.fixture
def process(db):
    return RecruitmentProcess.objects.create(
        id='proc-m07-batch',
        code='M07_BATCH',
        name='M07 批量守卫流程',
        current_version='1.0',
        is_template=False,
        is_enabled=True,
        is_latest=True,
    )


def _candidate(cid, referrer=None):
    return Candidate.objects.create(
        id=cid, name=f'候选人-{cid}', phone=f'138{abs(hash(cid)) % 100000000:08d}',
        referrer=referrer,
    )


# ---------------------------------------------------------------------------
# 1) batch_screen
# ---------------------------------------------------------------------------

def test_batch_screen_blocks_unwritable_and_does_not_persist(
    client, actor, process,
):
    """可见但 OWNER 范围外 -> NO_WRITE_PERMISSION 且**不落库**。"""
    _write_rule(RowScopeType.OWNER)
    mine = _candidate('cand-m07-mine', referrer=actor)
    others = _candidate('cand-m07-others', referrer=None)

    resp = client.post(
        f'/api/v1/processes/{process.id}/batch-screen/',
        {'candidate_ids': [mine.id, others.id], 'decision': 'PASS'},
        format='json',
    )

    assert resp.status_code == 200
    results = {r['candidateId']: r for r in resp.json()['data']['results']}

    assert results[mine.id]['success'] is True, '自己负责的候选人应可写'
    assert results[others.id]['success'] is False
    assert results[others.id]['error'] == 'NO_WRITE_PERMISSION'

    # 关键断言：失败项真的没落库（这是静态守卫测不出来的）
    assert CandidateScreen.objects.filter(candidate=others).count() == 0, \
        '不可写候选人绝不能产生筛选记录'
    assert CandidateScreen.objects.filter(candidate=mine).count() == 1


def test_batch_screen_invisible_id_is_not_reported_as_write_denied(
    client, process,
):
    """不存在的 id -> CANDIDATE_NOT_FOUND，不被误报成无写权限。

    这条守住"新增守卫不改变既有批量语义"：不存在的 id 在历史上就是取不到跳过。
    """
    _write_rule(RowScopeType.NONE)

    resp = client.post(
        f'/api/v1/processes/{process.id}/batch-screen/',
        {'candidate_ids': ['cand-not-exist-at-all'], 'decision': 'PASS'},
        format='json',
    )

    assert resp.status_code == 200
    row = resp.json()['data']['results'][0]
    assert row['error'] == 'CANDIDATE_NOT_FOUND'
    assert CandidateScreen.objects.count() == 0


def test_batch_screen_fail_open_without_write_rule(client, process, actor):
    """未配置 WRITE 规则 -> 全部放行（opt-in，不因 M07 上线锁死既有写入口）。"""
    _read_all_rule()  # 只放开读范围, 故意不配 WRITE
    c = _candidate('cand-m07-failopen', referrer=None)

    resp = client.post(
        f'/api/v1/processes/{process.id}/batch-screen/',
        {'candidate_ids': [c.id], 'decision': 'PASS'},
        format='json',
    )

    assert resp.status_code == 200
    assert resp.json()['data']['results'][0]['success'] is True
    assert CandidateScreen.objects.filter(candidate=c).count() == 1


# ---------------------------------------------------------------------------
# 2) batch_recommend
# ---------------------------------------------------------------------------

def test_batch_recommend_blocks_unwritable_and_does_not_persist(
    client, actor, process,
):
    _write_rule(RowScopeType.OWNER)
    mine = _candidate('cand-rec-mine', referrer=actor)
    others = _candidate('cand-rec-others', referrer=None)

    resp = client.post(
        f'/api/v1/processes/{process.id}/batch-recommend/',
        {'candidate_ids': [mine.id, others.id], 'reason': '推荐'},
        format='json',
    )

    assert resp.status_code == 200
    results = {r['candidateId']: r for r in resp.json()['data']['results']}

    assert results[others.id]['success'] is False
    assert results[others.id]['error'] == 'NO_WRITE_PERMISSION'
    assert CandidateRecommendation.objects.filter(candidate=others).count() == 0, \
        '不可写候选人绝不能产生推荐记录'
    assert CandidateRecommendation.objects.filter(candidate=mine).count() == 1


def test_batch_recommend_none_scope_blocks_everything(client, process, actor):
    """NONE 写范围 -> 全部拒绝且一条都不落库。"""
    _write_rule(RowScopeType.NONE)
    c = _candidate('cand-rec-none', referrer=actor)

    resp = client.post(
        f'/api/v1/processes/{process.id}/batch-recommend/',
        {'candidate_ids': [c.id], 'reason': 'x'},
        format='json',
    )

    assert resp.status_code == 200
    assert resp.json()['data']['results'][0]['error'] == 'NO_WRITE_PERMISSION'
    assert CandidateRecommendation.objects.count() == 0


# ---------------------------------------------------------------------------
# 3) candidate.merge
# ---------------------------------------------------------------------------

def test_merge_rejects_readable_but_unwritable(client, actor):
    """读范围看得见、但写范围不可写 -> 403，且不执行合并（不软删 duplicate）。"""
    _write_rule(RowScopeType.NONE)
    primary = _candidate('cand-merge-primary', referrer=actor)
    dup = _candidate('cand-merge-dup', referrer=actor)

    resp = client.post(
        '/api/v1/candidates/merge/',
        {'primary_id': primary.id, 'duplicate_ids': [dup.id]},
        format='json',
    )

    assert resp.status_code == 403
    # merge 走裸 DRF Response(非统一异常信封), 故断言 error 文案前缀。
    # 文案要能区分两道守卫: 读范围拦的是「无权访问候选人」, 写范围拦的是「无写权限」——
    # 断言后者, 才能证明请求确实穿过了读范围、真正撞在写范围上。
    assert '无写权限' in resp.json()['error']

    dup.refresh_from_db()
    assert dup.deleted_at is None, '被拒绝的合并不得软删 duplicate'


def test_merge_allows_when_all_within_write_scope(client, actor):
    """ALL 写范围 -> 合并放行（正向对照, 证明 403 不是接口本身坏了）。"""
    _write_rule(RowScopeType.ALL)
    primary = _candidate('cand-merge-all-primary', referrer=None)
    dup = _candidate('cand-merge-all-dup', referrer=None)

    resp = client.post(
        '/api/v1/candidates/merge/',
        {'primary_id': primary.id, 'duplicate_ids': [dup.id]},
        format='json',
    )

    assert resp.status_code == 200, resp.content
    dup.refresh_from_db()
    assert dup.deleted_at is not None, '放行时合并应真的软删 duplicate'
