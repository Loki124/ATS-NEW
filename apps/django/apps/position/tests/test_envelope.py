"""信封契约 — PositionViewSet (信封收口 Batch 8, 后端-only + bug 修复).

PositionViewSet 含自定义 create/update(views.py:67/75), 原 _detail_response 返回裸
Response(out.data) → FE extractOne 读 .data 得 undefined → createPosition/updatePosition
**当前返回 null**(潜在 bug). 本批: 加 EnvelopeWriteMixin(覆盖 retrieve) + _detail_response
改 success_response 包裹(create/update 经此统一信封). transition/open_positions @action 已信封,
perform_destroy(软删) 不动.

FE 影响面核查: position.ts 的 extractOne/extractList 已 envelope-aware(读 .data), 故本批零 FE 改动,
且恰好修复 createPosition/updatePosition 返回 null 的缺陷.

权限: V2Permission + ScopeQuerysetMixin(recruit_type 对所有用户默认 'social' 过滤, 但 Position
默认 recruit_type=SOCIAL, 匹配; super_user 经 is_super_admin 短路), 用 super_user(auth_client).
"""
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.core.models import Department
from apps.position.models import Position
from apps.process.models import RecruitmentProcess

pytestmark = pytest.mark.django_db(transaction=True)

LIST = '/api/v1/positions/'


def _uid(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


@pytest.fixture
def scenario(db):
    User = get_user_model()
    user = User.objects.create_user(username=_uid('hr'), password='Test@1234')
    dept = Department.objects.create(id=_uid('dept'), name='信封BG', code=_uid('NED'))
    process = RecruitmentProcess.objects.create(
        code=_uid('PROC'), name='信封流程', current_version='V1.0',
        version_seq=1, is_latest=True,
    )
    position = Position.objects.create(
        code=f'P{uuid.uuid4().hex[:8].upper()}',
        title='信封职位', department=dept,
        hiring_manager=user, owner=user, process=process,
    )
    return {
        'user': user, 'dept': dept, 'process': process, 'position': position,
    }


def test_position_retrieve_envelope(auth_client, scenario):
    resp = auth_client.get(f'{LIST}{scenario["position"].id}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['data']['id'] == str(scenario['position'].id)


def test_position_update_envelope(auth_client, scenario):
    # PATCH location 走 PositionViewSet.update → _detail_response(success_response) → 信封.
    resp = auth_client.patch(
        f'{LIST}{scenario["position"].id}/',
        {'location': '北京'}, format='json')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    # Position.state 是 FSMField(protected=True), 禁止 refresh_from_db; 从响应信封断言.
    assert resp.data['data']['location'] == '北京'


def test_position_list_envelope(auth_client, scenario):
    resp = auth_client.get(LIST)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert isinstance(resp.data['data'], list)


def test_position_create_envelope(auth_client, scenario):
    # 验证修复: 后端 create 现返回 {success,data}, FE extractOne 能取到 PositionRow(code 已注入).
    payload = {
        'title': '新建职位',
        'department': str(scenario['dept'].id),
        'hiring_manager': str(scenario['user'].id),
        'owner': str(scenario['user'].id),
        'process': str(scenario['process'].id),
    }
    before = Position.objects.count()
    resp = auth_client.post(LIST, payload, format='json')
    assert resp.status_code == 201
    assert resp.data['success'] is True
    # 关键: data 内含 id 与自动注入的 code, 否则 FE extractOne 取不到(PATCH 前为 null bug).
    assert 'id' in resp.data['data']
    assert resp.data['data']['code']  # 非空, perform_create 注入
    assert resp.data['data']['title'] == '新建职位'
    assert Position.objects.count() == before + 1
