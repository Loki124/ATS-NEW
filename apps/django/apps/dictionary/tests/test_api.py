"""数据字典 API + 阶段类型校验测试 (PR #69: 阶段类型数据字典化).

锁定的契约
==========
1. GET /api/v1/dictionary-items/?type_code=recruitment_stage_type
   → 200, 返回该类型下所有启用字典项, 按 sort_order 升序.
   每条含 key / value / sortOrder / typeCode (驼峰).
2. 阶段类型必须从数据字典读取:
   RecruitmentStageSerializer 校验 stage_type 必须存在于字典
   (recruitment_stage_type 下 is_active 的 key), 否则 400.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.process.models import RecruitmentStage
from apps.process.serializers import RecruitmentStageSerializer

STAGE_TYPE_URL = '/api/v1/dictionary-items/?type_code=recruitment_stage_type'
EXPECTED = [
    ('SCREEN', '筛选', 10),
    ('INVITATION', '邀约', 20),
    ('INTERVIEW', '面试', 30),
    ('OFFER', '录用', 40),
]

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client(db):
    user = get_user_model().objects.create_user(
        username='dict_test_user', password='Test@1234', employee_id='EDT001'
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_dict_endpoint_requires_auth():
    """未登录读 → 401。"""
    resp = APIClient().get(STAGE_TYPE_URL)
    assert resp.status_code == 401


def test_stage_type_dict_items(auth_client):
    """阶段类型字典项齐全且按 sort_order 升序, 字段形态符合前端契约。"""
    resp = auth_client.get(STAGE_TYPE_URL)
    assert resp.status_code == 200
    body = resp.json()
    items = body['data']
    assert isinstance(items, list) and len(items) >= 4

    keys = [it['key'] for it in items]
    for key, _value, _sort in EXPECTED:
        assert key in keys

    # 按 sort_order 升序 (前端 listDictionaryItems 也做了排序, 这里锁后端契约)
    orders = [it['sortOrder'] for it in items]
    assert orders == sorted(orders)

    # 前端依赖的字段形态: key / value / sortOrder / typeCode
    first = next(it for it in items if it['key'] == 'SCREEN')
    assert first['value'] == '筛选'
    assert first['typeCode'] == 'recruitment_stage_type'
    assert 'sortOrder' in first


def test_filter_by_other_type_returns_only_that_type(auth_client):
    """type_code 过滤只返回对应类型; 不存在的类型返回空列表。"""
    resp = auth_client.get(STAGE_TYPE_URL + 'x')  # 不存在的 code
    assert resp.status_code == 200
    assert resp.json()['data'] == []


def test_stage_type_must_exist_in_dict():
    """非法阶段类型 (不在字典中) → serializer 校验失败。"""
    ser = RecruitmentStageSerializer(
        data={'name': 'X阶段', 'stage_type': 'NOT_A_REAL_TYPE'}
    )
    assert not ser.is_valid()
    assert 'stage_type' in ser.errors


def test_valid_stage_type_passes_dict_check():
    """合法阶段类型 (字典中存在) → 校验通过。"""
    ser = RecruitmentStageSerializer(data={'name': '筛选阶段', 'stage_type': 'SCREEN'})
    assert ser.is_valid(), ser.errors
