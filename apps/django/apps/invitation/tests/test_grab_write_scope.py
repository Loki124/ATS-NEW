"""M07 写范围守卫：InvitationViewSet.grab 的端点级行为验证。

背景
====
``ApplicationViewSet.grab`` 早已接 ``ensure_writable(action='claim')``, 但
``InvitationViewSet.grab`` 漏了 —— 它同样是**抢单池抢占**动作, 同样
``get_object()`` 后直接改 ``grabbed_by`` / ``grabbed_at``, 却只靠功能权限码
``recruit:invitation:edit`` 把关: **看得见就能抢**。抢单是零和资源分配,
越权后果比普通字段编辑直接得多(把别人的邀约抢走)。

三个必须绕开的坑（都实际踩过）
=================================
1. **受测用户必须非超管** —— ``write_scope_q`` 对 ``is_super_admin`` 直接返回
   None(恒放行), 用超管测写范围等于什么都没测。
2. **必须授资源码** —— 否则 V2Permission 在功能权限层就 403, 请求进不到业务代码。
3. **必须让邀约进入读范围** —— 本 ViewSet **没有** ``data_perm_entity``(邀约不在
   数据权限向导模块清单内, 只有 candidate/demand/position/process/talent),
   所以配 ``row_access=READ`` 规则是**无效的**(``scope_filter_q`` 收 entity 参数,
   entity 为空时根本不查角色规则)。读范围只由 ``resolve_scope`` 的 L1-L4 决定。
   故这里给角色配 ``default_data_scope_type='DEPT'`` 并让用户与职位同部门,
   经 ``scope_field='application__position__department'`` 让邀约可见,
   请求才能真正走到写范围判定分支。
"""
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.application.models import Application
from apps.candidate.models import Candidate
from apps.core.models import Department
from apps.core.models_permission_v2 import (
    PermissionResource, RolePermissionV2, RoleV2, UserRoleV2,
)
from apps.data_permission.enforcement import is_writable, write_scope_q
from apps.data_permission.models import DataPermissionRule, RowScopeAccess, RowScopeType
from apps.invitation.models import Invitation
from apps.position.models import Position
from apps.process.models import RecruitmentProcess

pytestmark = pytest.mark.django_db

GRAB = '/api/v1/invitations/{id}/grab/'
ROLE_CODE = 'M07_INVITATION_GRAB_ROLE'

# InvitationViewSet.permission_required = 'recruit:invitation:list',
# grab 是自定义 POST -> 派生 recruit:invitation:edit
RESOURCE_CODES = ('recruit:invitation:list', 'recruit:invitation:edit')


def _uid(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


def _write_rule(scope_type):
    return DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value=ROLE_CODE, level='ROW',
        row_access=RowScopeAccess.WRITE, entity='invitation',
        scope_type=scope_type, status=1,
    )


@pytest.fixture
def actor():
    """非超管 + 持自定义角色 + 有资源码 + DEPT 读范围(能看见本部门邀约)。"""
    User = get_user_model()
    RoleV2.objects.get_or_create(
        system_code='recruit', role_code=ROLE_CODE,
        defaults={'role_name': 'M07 邀约抢单角色', 'status': 1},
    )
    # DEPT 数据范围: 让 actor 能看见 actor 所在部门的职位下的邀约
    RoleV2.objects.filter(role_code=ROLE_CODE, system_code='recruit').update(
        default_data_scope_type='DEPT')
    for code in RESOURCE_CODES:
        PermissionResource.objects.get_or_create(
            resource_code=code,
            defaults={'resource_name': code, 'resource_type': 'BUTTON',
                      'system_code': 'recruit', 'status': 1},
        )
        RolePermissionV2.objects.get_or_create(
            role_code=ROLE_CODE, resource_code=code,
            defaults={'system_code': 'recruit'},
        )
    from apps.core.permissions_v2 import invalidate_known_codes
    invalidate_known_codes()

    dept = Department.objects.create(id=_uid('dept'), name='M07 邀约BG', code=_uid('NED'))
    user = User.objects.create_user(
        username=_uid('hr'), password='Test@1234', department=dept)
    UserRoleV2.objects.get_or_create(
        user_id=user.pk, role_code=ROLE_CODE, system_code='recruit')
    c = APIClient()
    c.force_authenticate(user=user)
    return user, c, dept


@pytest.fixture
def invitation_in_actor_dept(db, actor):
    """一条处于抢单池、状态 INVITING、且职位部门 == actor 部门的邀约(故 actor 可见)。"""
    _, _, dept = actor
    User = get_user_model()
    inviter = User.objects.create_user(
        username=_uid('inviter'), password='Test@1234', department=dept)
    process = RecruitmentProcess.objects.create(
        code=_uid('PROC'), name='M07 邀约流程', current_version='V1.0',
        version_seq=1, is_latest=True,
    )
    position = Position.objects.create(
        code=_uid('POS'), title='M07 邀约职位', department=dept,
        hiring_manager=inviter, owner=inviter, process=process,
    )
    candidate = Candidate.objects.create(
        name='M07 邀约候选人', phone=_uid('138'), gender='男',
    )
    application = Application.objects.create(
        code=_uid('APP'), candidate=candidate, position=position,
        process=process, workflow_version='V1.0',
    )
    return Invitation.objects.create(
        application=application, inviter=inviter,
        expire_at=timezone.now() + timedelta(days=90),
        state='INVITING', is_grab_pool=True,
        created_by=inviter, updated_by=inviter,
    )


def test_fixture_precondition_invitation_is_visible(actor, invitation_in_actor_dept):
    """前置断言：actor 确实**看得见**这条邀约。

    没有这条, 下面的 403/200 都可能只是 404 换了个马甲 —— 必须先证明
    「可见但不可写」这个前提成立, 测的才是写范围守卫。
    """
    from apps.core.entity_scope import entity_scope_q

    user, _, _ = actor
    q = entity_scope_q(_FakeRequest(user), 'invitation')
    assert Invitation.objects.filter(q, pk=invitation_in_actor_dept.pk).exists(), \
        '测试前提失效: actor 看不见邀约, 后续断言只会测到 404'


def test_grab_blocked_by_none_write_scope(actor, invitation_in_actor_dept):
    """NONE 写范围 -> 403, 且 grabbed_by 保持为空(没被抢走)。"""
    user, client, _ = actor
    _write_rule(RowScopeType.NONE)
    assert not is_writable(user, 'invitation', invitation_in_actor_dept, action='claim'), \
        '前置失效: NONE 写范围下应判不可写'

    resp = client.post(GRAB.format(id=invitation_in_actor_dept.id), {}, format='json')
    assert resp.status_code == 403, resp.content

    st = _grab_state(invitation_in_actor_dept.id)
    assert st['grabbed_by_id'] is None, \
        '被写守卫拦下的抢单不得真的把邀约抢走'


def test_grab_allowed_with_all_write_scope(actor, invitation_in_actor_dept):
    """ALL 写范围 -> 200 且真的抢到(正向对照, 证明 403 不是接口本身坏了)。"""
    user, client, _ = actor
    _write_rule(RowScopeType.ALL)
    assert is_writable(user, 'invitation', invitation_in_actor_dept, action='claim')

    resp = client.post(GRAB.format(id=invitation_in_actor_dept.id), {}, format='json')
    assert resp.status_code == 200, resp.content

    st = _grab_state(invitation_in_actor_dept.id)
    assert st['grabbed_by_id'] == user.pk
    assert st['grabbed_at'] is not None


def test_grab_fail_open_without_write_rule(actor, invitation_in_actor_dept):
    """未配置 WRITE 规则 -> 放行(opt-in fail-open, 不因新增守卫锁死既有抢单流程)。"""
    user, client, _ = actor
    assert write_scope_q(user, 'invitation', action='claim') is None, \
        '前置失效: 无 WRITE 规则时写范围应为 None'

    resp = client.post(GRAB.format(id=invitation_in_actor_dept.id), {}, format='json')
    assert resp.status_code == 200, resp.content

    st = _grab_state(invitation_in_actor_dept.id)
    assert st['grabbed_by_id'] == user.pk


def test_grab_rejects_non_grab_pool_before_touching_data(actor, db):
    """非抢单池的邀约仍按业务规则 400, 且守卫不改变这个既有语义。"""
    user, client, dept = actor
    _write_rule(RowScopeType.ALL)

    User = get_user_model()
    inviter = User.objects.create_user(
        username=_uid('inv2'), password='Test@1234', department=dept)
    process = RecruitmentProcess.objects.create(
        code=_uid('P2'), name='非池流程', current_version='V1.0',
        version_seq=1, is_latest=True,
    )
    position = Position.objects.create(
        code=_uid('PO2'), title='非池职位', department=dept,
        hiring_manager=inviter, owner=inviter, process=process,
    )
    candidate = Candidate.objects.create(name='非池候选人', phone=_uid('138'))
    application = Application.objects.create(
        code=_uid('A2'), candidate=candidate, position=position,
        process=process, workflow_version='V1.0',
    )
    inv = Invitation.objects.create(
        application=application, inviter=inviter,
        expire_at=timezone.now() + timedelta(days=90),
        state='INVITING', is_grab_pool=False,
        created_by=inviter, updated_by=inviter,
    )

    resp = client.post(GRAB.format(id=inv.id), {}, format='json')
    assert resp.status_code == 400, resp.content
    assert _grab_state(inv.id)['grabbed_by_id'] is None


def _grab_state(invitation_id):
    """读库拿 grabbed_by_id / grabbed_at, **不实例化模型**。

    Invitation.state 是受保护的 FSMField, ``refresh_from_db()`` 会走
    FSMField.__set__ 抛 AttributeError('Direct state modification is not allowed')
    (仓库既有 test_envelope.py / test_time_limit_integration.py 均已记录此坑)。
    用 values().get() 只取需要的列, 绕开 FSM 实例化。
    """
    return Invitation.objects.filter(pk=invitation_id).values(
        'grabbed_by_id', 'grabbed_at').first()


class _FakeRequest:
    """最小 request 替身: entity_scope_q 只需要 .user 与 .recruit_type。"""

    def __init__(self, user):
        self.user = user
        self.recruit_type = 'social'
