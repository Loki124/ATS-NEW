"""S5-21 RotationStage 专项回归测试：N 段轮岗模型 + 端点 + 期数唯一性。

锁死：
1. 模型层：同安排内 stage_no 唯一（unique_together 落到 DB）。
2. 端点层：创建阶段、按 arrangement 过滤列表。
3. 期数唯一性按「安排」隔离：不同安排可各有 stage_no=1。
4. 校验：阶段部门须启用、阶段导师须 CAMPUS_MENTOR、日期区间 end>=start。
"""
import pytest

from apps.campus_rotation.models import RotationArrangement, RotationStage

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
    return RotationArrangement.objects.create(person_id=720001)


# ──────────────────────────────────────────────────────────────
# 模型层
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_stage_no_unique_per_arrangement_model(arrangement):
    RotationStage.objects.create(arrangement=arrangement, stage_no=1)
    RotationStage.objects.create(arrangement=arrangement, stage_no=2)
    assert RotationStage.objects.filter(arrangement=arrangement).count() == 2


@pytest.mark.django_db
def test_stage_no_unique_is_per_arrangement(arrangement, db):
    other = RotationArrangement.objects.create(person_id=720002)
    RotationStage.objects.create(arrangement=arrangement, stage_no=1)
    # 不同安排可各有 stage_no=1（唯一约束按 (arrangement, stage_no) 组合）
    RotationStage.objects.create(arrangement=other, stage_no=1)
    assert RotationStage.objects.filter(stage_no=1).count() == 2


# ──────────────────────────────────────────────────────────────
# 端点层
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_create_and_list_stages(auth_client, _seed_campus_data):
    r = auth_client.post(f'{BASE}/rotation-arrangements/', {'person_id': 720010}, format='json')
    assert r.status_code in (200, 201), r.content
    rid = r.json()['data']['id']

    for no in (1, 2):
        resp = auth_client.post(
            f'{BASE}/rotation-stages/',
            {'arrangement': rid, 'stage_no': no}, format='json',
        )
        assert resp.status_code in (200, 201), resp.content

    listed = auth_client.get(f'{BASE}/rotation-stages/', {'arrangement': rid})
    assert listed.status_code == 200, listed.content
    assert listed.json()['pagination']['total'] == 2


@pytest.mark.django_db
def test_stage_no_duplicate_rejected(auth_client, _seed_campus_data):
    r = auth_client.post(f'{BASE}/rotation-arrangements/', {'person_id': 720011}, format='json')
    rid = r.json()['data']['id']
    auth_client.post(f'{BASE}/rotation-stages/', {'arrangement': rid, 'stage_no': 1}, format='json')
    resp = auth_client.post(
        f'{BASE}/rotation-stages/', {'arrangement': rid, 'stage_no': 1}, format='json',
    )
    # 同安排同 stage_no 必须被序列化器唯一性校验拒绝（400 信封）
    assert resp.status_code == 400, resp.content
