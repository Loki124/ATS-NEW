"""班级成员明细穿透端点契约（2026-10-21）。

背景：前端班级管理页点「校招人数」报
  GET /api/v1/campus-rotation/class-rooms/MOCK_CR_01/members/ 404
本文件锁住**端点本身的契约**，把「404 是后端对不存在 id 的正确语义、
不是端点缺失」这一点固定下来，避免后续误判：

  - 真实班级 id  -> 200，且只返回该班级的校招生；
  - 不存在的 id  -> 404（REST 语义：资源不存在）；
  - 前端示例数据（MOCK_ 前缀假 id）**不应**发起该请求 ——
    那是前端守卫问题（useCampusMock.isMock 派生 + 各页二次守卫），
    前端回归见 web/app/src/composables/__tests__/useCampusMock.guard.test.ts。

注意：真实 id 用真实 UUID，断言只认「状态码 + 成员数」，不依赖具体 id 值。
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.campus_control.models import Person
from apps.campus_rotation.models import ClassRoom

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-rotation'


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _admin_client() -> APIClient:
    user = get_user_model().objects.create_user(
        username=_uid('cls_mem_admin'), password='Test@1234', is_superuser=True, is_active=True,
    )
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return client


def _class_room() -> ClassRoom:
    return ClassRoom.objects.create(code=_uid('CL'), name=_uid('班'))


def _person(class_room: ClassRoom, name: str) -> Person:
    return Person.objects.create(
        code=_uid('C'), name=name, bu='能电BG', school='985', sex='男',
        major='工学', month='1月', status='在职', class_room=class_room,
    )


def test_members_endpoint_returns_members_of_real_class_room():
    """真实班级 id -> 200，且成员恰为该班级的校招生。"""
    client = _admin_client()
    room = _class_room()
    p_in = _person(room, '班内甲')
    p_other_room = _person(_class_room(), '班外乙')

    resp = client.get(f'{BASE}/class-rooms/{room.id}/members/')
    assert resp.status_code == 200, resp.content.decode()
    body = resp.json()
    assert body.get('success') is True
    ids = {row['id'] for row in body['data']}
    assert p_in.id in ids, '本班校招生应在成员明细中'
    assert p_other_room.id not in ids, '他班校招生不应出现'


def test_members_endpoint_404s_for_unknown_id():
    """不存在的 id -> 404（REST 语义）。前端示例假 id 属此类，故须由前端守卫拦下。"""
    client = _admin_client()
    resp = client.get(f'{BASE}/class-rooms/MOCK_CR_01/members/')
    assert resp.status_code == 404, resp.content.decode()
