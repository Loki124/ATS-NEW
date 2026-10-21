"""S5-19 FSM 专项回归测试：RotationArrangement.stage 流程态流转约束。

锁死：
1. 合法流转 submit→approve→ONGOING / reject→PENDING / complete→DONE / terminate→TERMINATED
2. 非法 source 流转抛 TransitionNotAllowed（→ 端点 409）
3. terminate 守卫：同人不得有第二条 ONGOING（→ 409）；必须填原因（端点 400）
4. protected=True：已存在实例直写 stage 抛 AttributeError（通用 CRUD 不可绕过）
5. 端点层：非法 action 当前态不允许 → 409；未知 action → 400
6. DONE/TERMINATED 为硬终态，无任何出边
"""
import pytest
from django_fsm import TransitionNotAllowed

from apps.campus_rotation.models import RotationArrangement

BASE = '/api/v1/campus-rotation'


@pytest.fixture
def _seed_campus_data(db):
    """确保校招轮岗角色与字典种子就绪（测试库幂等）。"""
    from apps.campus_rotation.seeds import (
        seed_campus_roles,
        seed_live_room_platform_type,
        seed_location_type,
    )
    seed_campus_roles()
    seed_live_room_platform_type()
    seed_location_type()


@pytest.fixture
def arrangement(db):
    return RotationArrangement.objects.create(person_id=700001)


def _to_ongoing(obj):
    obj.submit()
    obj.approve()
    obj.save()


# ──────────────────────────────────────────────────────────────
# 模型层合法流转
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_submit_approve_reaches_ongoing(arrangement):
    assert arrangement.stage == 'PENDING'
    arrangement.submit()
    assert arrangement.stage == 'APPROVING'
    arrangement.approve()
    arrangement.save()
    assert arrangement.stage == 'ONGOING'


@pytest.mark.django_db
def test_reject_returns_to_pending(arrangement):
    arrangement.submit()
    arrangement.reject()
    arrangement.save()
    assert arrangement.stage == 'PENDING'


@pytest.mark.django_db
def test_complete_from_ongoing(arrangement):
    _to_ongoing(arrangement)
    arrangement.complete()
    arrangement.save()
    assert arrangement.stage == 'DONE'
    assert arrangement.rotation_end is not None


@pytest.mark.django_db
def test_terminate_from_ongoing(arrangement):
    _to_ongoing(arrangement)
    arrangement.terminate(reason='转正失败')
    arrangement.save()
    assert arrangement.stage == 'TERMINATED'
    assert '终止原因' in arrangement.note


# ──────────────────────────────────────────────────────────────
# 非法流转 / 守卫
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_approve_from_pending_illegal(arrangement):
    # PENDING 不能直接 approve（source=APPROVING 不匹配）
    with pytest.raises(TransitionNotAllowed):
        arrangement.approve()


@pytest.mark.django_db
def test_terminate_guard_no_other_ongoing(db):
    a1 = RotationArrangement.objects.create(person_id=700002)
    _to_ongoing(a1)
    a2 = RotationArrangement.objects.create(person_id=700002)
    _to_ongoing(a2)
    # 同人已存在其他 ONGOING，terminate 守卫必须拒绝
    with pytest.raises(TransitionNotAllowed):
        a2.terminate(reason='x')


@pytest.mark.django_db
def test_protected_blocks_direct_write(db):
    obj = RotationArrangement.objects.create(person_id=700004)
    obj.submit()
    obj.save()
    obj.refresh_from_db()
    # 已存在实例（已加载当前态）直写 stage 必须被 FSMField 拦截
    with pytest.raises(AttributeError):
        obj.stage = 'ONGOING'


@pytest.mark.django_db
def test_terminal_states_no_outgoing(db):
    obj = RotationArrangement.objects.create(person_id=700005)
    _to_ongoing(obj)
    obj.complete()
    obj.save()
    # DONE 为硬终态，任何出边都不允许
    for action in ('submit', 'approve', 'reject', 'complete', 'terminate'):
        with pytest.raises(TransitionNotAllowed):
            getattr(obj, action)()


# ──────────────────────────────────────────────────────────────
# 端点层（经 FSM 契约）
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_transition_endpoint_409_invalid_source(auth_client, _seed_campus_data):
    r = auth_client.post(f'{BASE}/rotation-arrangements/', {'person_id': 710001}, format='json')
    rid = r.json()['data']['id']
    # 直接从 PENDING approve -> 非法 source -> 409
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/{rid}/transition/',
        {'action': 'approve'}, format='json',
    )
    assert resp.status_code == 409, resp.content


@pytest.mark.django_db
def test_transition_endpoint_400_unknown_action(auth_client, _seed_campus_data):
    r = auth_client.post(f'{BASE}/rotation-arrangements/', {'person_id': 710002}, format='json')
    rid = r.json()['data']['id']
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/{rid}/transition/',
        {'action': 'frobnicate'}, format='json',
    )
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_transition_endpoint_terminate_requires_reason(auth_client, _seed_campus_data):
    r = auth_client.post(f'{BASE}/rotation-arrangements/', {'person_id': 710003}, format='json')
    rid = r.json()['data']['id']
    auth_client.post(
        f'{BASE}/rotation-arrangements/{rid}/transition/',
        {'action': 'submit'}, format='json',
    )
    auth_client.post(
        f'{BASE}/rotation-arrangements/{rid}/transition/',
        {'action': 'approve'}, format='json',
    )
    # terminate 无 reason -> 400
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/{rid}/transition/',
        {'action': 'terminate'}, format='json',
    )
    assert resp.status_code == 400, resp.content
    # 带 reason -> 200
    resp2 = auth_client.post(
        f'{BASE}/rotation-arrangements/{rid}/transition/',
        {'action': 'terminate', 'reason': '离职'}, format='json',
    )
    assert resp2.status_code == 200, resp2.content
    assert resp2.json()['data']['stage'] == 'TERMINATED'


@pytest.mark.django_db
def test_transition_endpoint_happy_path(auth_client, _seed_campus_data):
    r = auth_client.post(f'{BASE}/rotation-arrangements/', {'person_id': 710004}, format='json')
    rid = r.json()['data']['id']
    for action in ('submit', 'approve'):
        resp = auth_client.post(
            f'{BASE}/rotation-arrangements/{rid}/transition/',
            {'action': action}, format='json',
        )
        assert resp.status_code == 200, resp.content
    assert resp.json()['data']['stage'] == 'ONGOING'
