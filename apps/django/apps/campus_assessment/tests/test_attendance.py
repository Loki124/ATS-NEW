"""考勤护栏（契约 §2.4：每日排名 + 月度汇总 + 迟到口径）。

口径来源：逆向清单 §4.2「考勤管理」页签 + §5 A9 考勤维度
`round(Σ(出勤 − 迟到×0.5) / 月数, 1)`（views2.js:141）。
"""
import pytest

from apps.campus_assessment.models import AttendanceMonthly, AttendanceRecord
from apps.campus_assessment.tests import (
    BASE,
    admin_user,
    client_for,
    list_rows,
    make_person,
    make_user,
)

pytestmark = pytest.mark.django_db


def _make_record(person, day, punch, status=AttendanceRecord.Status.NORMAL):
    return AttendanceRecord.objects.create(
        person=person, date=day, punch_time=punch, status=status,
    )


# ---------------------------------------------------------------------------
# 每日打卡 CRUD 与过滤
# ---------------------------------------------------------------------------
def test_create_and_list_attendance_records_with_date_filters():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')

    resp = client.post(f'{BASE}/attendance-records/', {
        'person': person.id,
        'date': '2026-07-01',
        'punchTime': '08:55:00',
        'status': '正常',
    }, format='json')
    assert resp.status_code == 201, resp.content.decode()
    row = resp.json()['data']
    assert row['person'] == person.id
    assert row['punchTime'] == '08:55:00'
    assert row['status'] == '正常'

    _make_record(person, '2026-07-02', '09:10:00')
    _make_record(person, '2026-07-03', '09:20:00')

    resp = client.get(f'{BASE}/attendance-records/', {
        'date_from': '2026-07-02', 'date_to': '2026-07-03', 'page_size': 100,
    })
    assert resp.status_code == 200
    rows = list_rows(resp.json())
    assert len(rows) == 2
    assert sorted(r['date'] for r in rows) == ['2026-07-02', '2026-07-03']


def test_attendance_record_list_is_scoped_to_visible_persons():
    """导师只看得到自己徒弟的打卡记录。"""
    mentor = make_user(role_code='MENTOR')
    client = client_for(mentor)
    mine = make_person(name='徒弟', mentor=mentor)
    other = make_person(name='别人的徒弟')
    _make_record(mine, '2026-07-01', '08:55:00')
    _make_record(other, '2026-07-01', '08:55:00')

    resp = client.get(f'{BASE}/attendance-records/', {'page_size': 100})
    assert resp.status_code == 200
    rows = list_rows(resp.json())
    assert len(rows) == 1
    assert rows[0]['person'] == mine.id


# ---------------------------------------------------------------------------
# 当日打卡排名（含「与第1名差距」）
# ---------------------------------------------------------------------------
def test_daily_attendance_ranking_reports_gap_to_first():
    admin = admin_user()
    client = client_for(admin)
    early = make_person(name='甲')
    middle = make_person(name='乙')
    late = make_person(name='丙')

    _make_record(early, '2026-07-01', '08:55:00')
    _make_record(middle, '2026-07-01', '09:10:00')
    _make_record(late, '2026-07-01', '09:20:00')

    resp = client.get(f'{BASE}/attendance-records/daily-ranking/', {'date': '2026-07-01'})
    assert resp.status_code == 200, resp.content.decode()
    data = resp.json()['data']
    assert data['date'] == '2026-07-01'
    rows = data['list']
    assert [r['name'] for r in rows] == ['甲', '乙', '丙']
    assert [r['rank'] for r in rows] == [1, 2, 3]
    assert rows[0]['gapMinutes'] == 0
    assert rows[0]['gapText'] == '与第1名持平'
    assert rows[1]['gapMinutes'] == 15
    assert '15' in rows[1]['gapText']
    assert rows[2]['gapMinutes'] == 25


def test_daily_attendance_ranking_ties_share_rank():
    """打卡时间相同 → 并列名次（1224 口径）。"""
    admin = admin_user()
    client = client_for(admin)
    first = make_person(name='甲')
    second = make_person(name='乙')
    _make_record(first, '2026-07-01', '09:00:00')
    _make_record(second, '2026-07-01', '09:00:00')

    resp = client.get(f'{BASE}/attendance-records/daily-ranking/', {'date': '2026-07-01'})
    rows = resp.json()['data']['list']
    assert [r['rank'] for r in rows] == [1, 1]
    assert all(r['gapMinutes'] == 0 for r in rows)


def test_daily_attendance_ranking_endpoint_is_not_swallowed_by_detail_route():
    """自定义路径必须排在 router.urls 之前 —— 否则被 `attendance-records/<pk>/` 抢走。"""
    admin = admin_user()
    client = client_for(admin)
    resp = client.get(f'{BASE}/attendance-records/daily-ranking/', {'date': '2026-07-01'})
    assert resp.status_code == 200
    assert resp.json()['success'] is True


def test_daily_attendance_ranking_rejects_bad_date():
    admin = admin_user()
    client = client_for(admin)
    resp = client.get(f'{BASE}/attendance-records/daily-ranking/', {'date': '20260701'})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 月度考勤汇总 + A9 考勤维度
# ---------------------------------------------------------------------------
def test_monthly_attendance_summary_and_dimension_formula():
    """A9：round(Σ(出勤 − 迟到×0.5) / 月数, 1) —— 单月即 (20 − 2×0.5) = 19.0。"""
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')

    resp = client.post(f'{BASE}/attendance-monthly/', {
        'person': person.id,
        'ym': '2026-07',
        'attendDays': 20,
        'lateCount': 2,
        'leaveDays': 1,
        'status': '正常',
    }, format='json')
    assert resp.status_code == 201, resp.content.decode()
    row = resp.json()['data']
    assert row['ym'] == '2026-07'
    assert row['attendDays'] == 20
    assert row['lateCount'] == 2
    assert row['attendanceDim'] == 19.0

    stored = AttendanceMonthly.objects.get(pk=row['id'])
    assert stored.person_id == person.id
    assert stored.leave_days == 1


def test_monthly_attendance_list_filtered_by_ym():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    AttendanceMonthly.objects.create(person=person, ym='2026-06', attend_days=20, late_count=0)
    AttendanceMonthly.objects.create(person=person, ym='2026-07', attend_days=21, late_count=1)

    resp = client.get(f'{BASE}/attendance-monthly/', {'ym': '2026-07', 'page_size': 100})
    assert resp.status_code == 200
    rows = list_rows(resp.json())
    assert len(rows) == 1
    assert rows[0]['ym'] == '2026-07'
    # (21 − 1×0.5) = 20.5
    assert rows[0]['attendanceDim'] == 20.5


# ---------------------------------------------------------------------------
# 软删 + restore（契约 §1.1「列表默认过滤 deleted_at__isnull=True；提供 restore 动作」）
# ---------------------------------------------------------------------------
def test_delete_is_soft_and_restore_brings_it_back():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    record = _make_record(person, '2026-07-01', '08:55:00')

    resp = client.delete(f'{BASE}/attendance-records/{record.id}/')
    assert resp.status_code == 200, resp.content.decode()

    # 软删后列表里没有；行还在库里，但默认 manager（SoftDeleteManager）已过滤掉
    resp = client.get(f'{BASE}/attendance-records/', {'page_size': 100})
    assert resp.status_code == 200
    assert len(list_rows(resp.json())) == 0
    assert not AttendanceRecord.objects.filter(pk=record.id).exists()
    assert AttendanceRecord.all_objects.filter(pk=record.id).exists()
    assert AttendanceRecord.all_objects.get(pk=record.id).deleted_at is not None

    # restore 动作把它放回来
    resp = client.post(f'{BASE}/attendance-records/{record.id}/restore/', {}, format='json')
    assert resp.status_code == 200, resp.content.decode()
    resp = client.get(f'{BASE}/attendance-records/', {'page_size': 100})
    assert len(list_rows(resp.json())) == 1
