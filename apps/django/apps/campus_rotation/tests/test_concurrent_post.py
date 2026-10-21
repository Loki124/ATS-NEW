"""S5-25 / S5-26 兼岗记录 + 摩卡同步钩子 专项测试。

锁死：
1. 模型层：兼岗记录落库、sync_status 默认 PENDING、软删不污染。
2. 端点层：创建/列出/按 person·arrangement 过滤；同步字段客户端不可直写。
3. 摩卡钩子契约（S5-26）：
   - 数据不完整 → SKIPPED，返回 False
   - 通道未启用（本期桩）→ 保持 PENDING，返回 False，**不伪造 SYNCED**
   - 推送失败 → FAILED + sync_error，返回 False，**不抛异常**（不阻塞主流程）
   - 推送成功 → SYNCED + 回写 sync_request_id + synced_at
"""
from datetime import date

import pytest

from apps.campus_control.models import Person
from apps.campus_rotation.models import ConcurrentPostRecord, RotationArrangement
from apps.campus_rotation.services import moka_sync

BASE = '/api/v1/campus-rotation'


@pytest.fixture
def _seed_campus_data(db):
    from apps.campus_rotation.seeds import (
        seed_campus_roles,
        seed_live_room_platform_type,
        seed_location_type,
    )
    seed_campus_roles()
    seed_live_room_platform_type()
    seed_location_type()


@pytest.fixture
def person(db):
    return Person.objects.create(
        code='CP-730001', name='兼岗测试人', bu='能电BG', school='985',
        sex='男', major='工学', month='2026-07', status='在职',
        employee_id='E730001',
    )


@pytest.fixture
def arrangement(db):
    return RotationArrangement.objects.create(person_id=730001)


@pytest.fixture
def record(person, arrangement):
    return ConcurrentPostRecord.objects.create(
        person=person, arrangement=arrangement,
        post_type='兼岗客服', effective_from=date(2026, 7, 1),
    )


# ──────────────────────────────────────────────────────────────
# 模型层
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_record_defaults_to_pending(record):
    assert record.sync_status == 'PENDING'
    assert record.sync_request_id == ''
    assert record.sync_error == ''
    assert record.synced_at is None


# ──────────────────────────────────────────────────────────────
# 端点层
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_create_and_list_records(auth_client, _seed_campus_data, person, arrangement):
    r = auth_client.post(
        f'{BASE}/concurrent-post-records/',
        {
            'person': str(person.id), 'arrangement': str(arrangement.id),
            'post_type': '兼岗主播', 'effective_from': '2026-07-01',
        },
        format='json',
    )
    assert r.status_code in (200, 201), r.content
    rid = r.json()['data']['id']

    listed = auth_client.get(f'{BASE}/concurrent-post-records/')
    assert listed.status_code == 200, listed.content
    assert listed.json()['pagination']['total'] == 1

    by_person = auth_client.get(
        f'{BASE}/concurrent-post-records/', {'person': str(person.id)},
    )
    assert by_person.json()['pagination']['total'] == 1

    by_arr = auth_client.get(
        f'{BASE}/concurrent-post-records/', {'arrangement': str(arrangement.id)},
    )
    assert by_arr.json()['pagination']['total'] == 1
    assert rid


@pytest.mark.django_db
def test_sync_fields_not_client_writable(auth_client, _seed_campus_data, person, arrangement):
    """同步状态字段由 moka_sync 独占写入，客户端直写须被拒。"""
    r = auth_client.post(
        f'{BASE}/concurrent-post-records/',
        {
            'person': str(person.id), 'arrangement': str(arrangement.id),
            'post_type': '兼岗客服', 'effective_from': '2026-07-01',
            'sync_status': 'SYNCED', 'sync_request_id': 'FAKE-123',
        },
        format='json',
    )
    assert r.status_code in (200, 201), r.content
    data = r.json()['data']
    # 响应键为 camelCase（项目统一封装）
    assert data['syncStatus'] == 'PENDING'
    assert data['syncRequestId'] == ''


@pytest.mark.django_db
def test_effective_to_before_from_rejected(auth_client, _seed_campus_data, person):
    r = auth_client.post(
        f'{BASE}/concurrent-post-records/',
        {
            'person': str(person.id), 'post_type': '兼岗客服',
            'effective_from': '2026-07-01', 'effective_to': '2026-06-01',
        },
        format='json',
    )
    assert r.status_code == 400, r.content


# ──────────────────────────────────────────────────────────────
# 摩卡同步契约（S5-26）
# ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_sync_skips_when_data_incomplete(arrangement):
    """缺人员 → SKIPPED，返回 False。"""
    rec = ConcurrentPostRecord.objects.create(
        arrangement=arrangement, post_type='兼岗客服',
        effective_from=date(2026, 7, 1),
    )
    assert moka_sync.sync_concurrent_post(rec) is False
    rec.refresh_from_db()
    assert rec.sync_status == 'SKIPPED'
    assert '数据不完整' in rec.sync_error


@pytest.mark.django_db
def test_sync_keeps_pending_when_channel_disabled(record, monkeypatch):
    """本期桩：通道未启用 → 保持 PENDING，**绝不伪造 SYNCED**。"""
    ok = moka_sync.sync_concurrent_post(record)
    assert ok is False
    record.refresh_from_db()
    assert record.sync_status == 'PENDING'
    assert record.sync_request_id == ''
    assert '未授权' in record.sync_error


@pytest.mark.django_db
def test_sync_failure_marks_failed_and_does_not_raise(record, monkeypatch):
    """推送抛异常 → FAILED + sync_error，函数不向上抛（不阻塞主流程）。"""
    def boom(payload):
        raise RuntimeError('摩卡网关 503')
    monkeypatch.setattr(moka_sync, '_push_to_moka', boom)

    ok = moka_sync.sync_concurrent_post(record)
    assert ok is False
    record.refresh_from_db()
    assert record.sync_status == 'FAILED'
    assert '503' in record.sync_error


@pytest.mark.django_db
def test_sync_success_writes_request_id(record, monkeypatch):
    """推送成功 → SYNCED + 回写 sync_request_id + synced_at。"""
    monkeypatch.setattr(moka_sync, '_push_to_moka', lambda payload: 'MOKA-8888')

    ok = moka_sync.sync_concurrent_post(record)
    assert ok is True
    record.refresh_from_db()
    assert record.sync_status == 'SYNCED'
    assert record.sync_request_id == 'MOKA-8888'
    assert record.sync_error == ''
    assert record.synced_at is not None


@pytest.mark.django_db
def test_sync_endpoint_returns_200_even_when_failed(auth_client, _seed_campus_data, record):
    """sync 端点：失败不阻塞，恒返 200 + 当前状态。"""
    r = auth_client.post(f'{BASE}/concurrent-post-records/{record.id}/sync/')
    assert r.status_code == 200, r.content
    data = r.json()['data']
    assert data['syncStatus'] in ('PENDING', 'FAILED', 'SKIPPED')
    assert data['syncStatus'] != 'SYNCED'
