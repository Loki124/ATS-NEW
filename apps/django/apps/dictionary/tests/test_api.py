"""阶段类型校验测试 (系统内置枚举, 不再经数据字典).

锁定的契约
==========
1. GET /api/v1/stages/stage-types/
   → 200, 返回 7 个固定阶段类型 [{value, label}], 系统级默认数据.
2. RecruitmentStageSerializer 校验 stage_type 必须是 StageType 枚举值, 否则 400.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.process.models import RecruitmentStage
from apps.process.serializers import RecruitmentStageSerializer

STAGE_TYPES_URL = '/api/v1/stages/stage-types/'
EXPECTED_VALUES = {
    'START_END', 'SCREEN', 'INVITATION', 'INTERVIEW', 'ASSESSMENT', 'OFFER', 'OTHER',
}

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client(db):
    user = get_user_model().objects.create_user(
        username='dict_test_user', password='Test@1234', employee_id='EDT001'
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_stage_types_endpoint_requires_auth():
    """未登录读 → 401。"""
    resp = APIClient().get(STAGE_TYPES_URL)
    assert resp.status_code == 401


def test_stage_types_endpoint_returns_7_enums(auth_client):
    """阶段类型系统内置枚举齐全, 字段形态符合前端契约 [{value, label}]。"""
    resp = auth_client.get(STAGE_TYPES_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 7
    values = {it['value'] for it in data}
    assert values == EXPECTED_VALUES
    for it in data:
        assert 'label' in it and it['label']


def test_invalid_stage_type_rejected():
    """非法阶段类型 (不在 StageType 枚举中) → serializer 校验失败。"""
    ser = RecruitmentStageSerializer(
        data={'name': 'X阶段', 'stage_type': 'NOT_A_REAL_TYPE'}
    )
    assert not ser.is_valid()
    assert 'stage_type' in ser.errors


def test_valid_stage_type_passes():
    """合法阶段类型 (StageType 枚举中存在) → 校验通过。"""
    ser = RecruitmentStageSerializer(data={'name': '筛选阶段', 'stage_type': 'SCREEN'})
    assert ser.is_valid(), ser.errors
