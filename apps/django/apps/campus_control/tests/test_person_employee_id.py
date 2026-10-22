"""校招生档案 · 工号 / 入职日期 / 预计入职日期 口径回归测试（2026-10-21 兵哥指令）

业务口径（唯一真源：`apps/campus_control/constants.py` 的 PENDING_STATUSES / EMPLOYED_STATUSES）：

1. **工号 = 8 位纯数字**，非空时全校唯一（存量 36 条在职数据已是 `25080001 …`，零重复）。
2. **未入职**（待入职）：无工号、无实际入职日期，**有预计入职日期**。
3. **已入职**（在职 / 离职）：有工号、有实际入职日期。

未入职状态下若带了工号 / 实际入职日期，服务端**自动清空**（而非报错）——
「待入职本来就没有工号」，前端切状态残留的值不该变成一次失败保存。
"""
import uuid

import pytest

from apps.campus_control.models import Person

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus'


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _payload(**kwargs):
    data = {
        'name': '张三',
        'bu': '能电BG',
        'school': '985',
        'sex': '男',
        'major': '工学',
        'month': '8月',
        'status': '待入职',
        'expected_entry_date': '2026-09-01',
    }
    data.update(kwargs)
    return data


def _data(resp):
    """拆信封：{success, data} → data。"""
    body = resp.json()
    return body.get('data', body)


# ===================== 工号格式 =====================

def test_employee_id_must_be_8_digits(auth_client):
    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(status='在职', employee_id='123', actual_entry_date='2026-09-01'),
        format='json',
    )
    assert resp.status_code == 400, resp.json()
    assert '8 位纯数字' in str(resp.json())


def test_employee_id_must_be_numeric_only(auth_client):
    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(status='在职', employee_id='CS2026001', actual_entry_date='2026-09-01'),
        format='json',
    )
    assert resp.status_code == 400, resp.json()
    assert '8 位纯数字' in str(resp.json())


def test_employee_id_can_be_blank_for_pending(auth_client):
    """待入职人员不带工号 → 允许（口径：无工号）。"""
    resp = auth_client.post(f'{BASE}/persons/', _payload(), format='json')
    assert resp.status_code == 201, resp.json()
    assert _data(resp)['employeeId'] == ''


def test_employee_id_unique(auth_client):
    """工号重复 → 400（认错人的防线）。"""
    first = auth_client.post(
        f'{BASE}/persons/',
        _payload(status='在职', employee_id='25089999', actual_entry_date='2026-09-01'),
        format='json',
    )
    assert first.status_code == 201, first.json()
    dup = auth_client.post(
        f'{BASE}/persons/',
        _payload(status='在职', employee_id='25089999', actual_entry_date='2026-09-02'),
        format='json',
    )
    assert dup.status_code == 400, dup.json()
    assert '工号' in str(dup.json())


# ===================== 未入职：无工号 / 无入职日期 =====================

@pytest.mark.parametrize('status', ['待入职'])
def test_pending_status_clears_employee_id_and_actual_date(auth_client, status):
    """待入职：即便传了工号 + 实际入职日期，服务端也自动清空。"""
    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(
            status=status,
            employee_id='25081234',
            actual_entry_date='2026-09-01',
        ),
        format='json',
    )
    assert resp.status_code == 201, resp.json()
    data = _data(resp)
    assert data['employeeId'] == ''
    assert not data['actualEntryDate']
    assert data['expectedEntryDate'] == '2026-09-01'


def test_pending_status_requires_expected_entry_date(auth_client):
    """待入职：预计入职日期必填（存量 20/20 都有，与历史兼容）。"""
    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(status='待入职', expected_entry_date=None),
        format='json',
    )
    assert resp.status_code == 400, resp.json()
    assert '预计入职日期' in str(resp.json())


# ===================== 已入职：工号 + 入职日期必填 =====================

@pytest.mark.parametrize('status', ['在职', '离职'])
def test_employed_status_requires_employee_id(auth_client, status):
    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(status=status, actual_entry_date='2026-09-01'),
        format='json',
    )
    assert resp.status_code == 400, resp.json()
    assert '工号' in str(resp.json())


@pytest.mark.parametrize('status', ['在职', '离职'])
def test_employed_status_requires_actual_entry_date(auth_client, status):
    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(status=status, employee_id='25080011'),
        format='json',
    )
    assert resp.status_code == 400, resp.json()
    assert '入职日期' in str(resp.json())


@pytest.mark.parametrize('status', ['在职', '离职'])
def test_employed_status_accepts_full_payload(auth_client, status):
    """在职 / 离职：工号 + 入职日期 + 预计入职日期 齐全 → 落库成功。"""
    resp = auth_client.post(
        f'{BASE}/persons/',
        _payload(
            status=status,
            employee_id='25080011',
            actual_entry_date='2026-09-01',
            expected_entry_date='2026-08-25',
        ),
        format='json',
    )
    assert resp.status_code == 201, resp.json()
    data = _data(resp)
    assert data['employeeId'] == '25080011'
    assert data['actualEntryDate'] == '2026-09-01'
    assert data['expectedEntryDate'] == '2026-08-25'


# ===================== 状态流转 =====================

def test_switch_pending_to_employed_requires_filling(auth_client):
    """待入职 → 在职：必须补工号与实际入职日期，否则拒绝。"""
    created = auth_client.post(f'{BASE}/persons/', _payload(), format='json')
    assert created.status_code == 201, created.json()
    pid = _data(created)['id']

    bad = auth_client.patch(
        f'{BASE}/persons/{pid}/',
        {'status': '在职'},
        format='json',
    )
    assert bad.status_code == 400, bad.json()

    ok = auth_client.patch(
        f'{BASE}/persons/{pid}/',
        {'status': '在职', 'employee_id': '25080022', 'actual_entry_date': '2026-09-01'},
        format='json',
    )
    assert ok.status_code == 200, ok.json()
    assert _data(ok)['employeeId'] == '25080022'


def test_switch_employed_to_pending_clears_fields(auth_client):
    """在职 → 待入职：工号与实际入职日期被自动清空（口径：待入职没有工号）。"""
    created = auth_client.post(
        f'{BASE}/persons/',
        _payload(status='在职', employee_id='25080033', actual_entry_date='2026-09-01'),
        format='json',
    )
    assert created.status_code == 201, created.json()
    pid = _data(created)['id']

    resp = auth_client.patch(f'{BASE}/persons/{pid}/', {'status': '待入职'}, format='json')
    assert resp.status_code == 200, resp.json()
    person = Person.objects.get(pk=pid)
    assert person.employee_id == ''
    assert person.actual_entry_date is None
