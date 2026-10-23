"""反馈记录护栏（契约 §2.4：创建/办结状态机、可见范围、关键词过滤）。

口径来源：逆向清单 §4.3「反馈记录」页签 ——
- 4 卡：总数 / 处理中 / 已解决·已闭环 / 含证据记录；
- 页签：全部 / 问题·情况记录 / 导师带教反馈；搜索姓名·内容·分类；
- 状态机：`处理中` → `已解决` / `已闭环`；
- **mentor 可见范围 = 自己带的徒弟**。
"""
import pytest

from apps.campus_assessment.models import FeedbackRecord
from apps.campus_assessment.tests import (
    BASE,
    admin_user,
    client_for,
    list_rows,
    make_person,
    make_user,
)

pytestmark = pytest.mark.django_db


def _create_feedback(client, person, **kwargs):
    payload = {
        'person': person.id,
        'date': '2026-07-01',
        'category': 'issue',
        'type': '进度滞后',
        'content': '本月任务完成度偏低',
    }
    payload.update(kwargs)
    return client.post(f'{BASE}/feedback-records/', payload, format='json')


# ---------------------------------------------------------------------------
# 创建
# ---------------------------------------------------------------------------
def test_create_feedback_defaults_to_processing():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')

    resp = _create_feedback(client, person)
    assert resp.status_code == 201, resp.content.decode()
    row = resp.json()['data']
    assert row['status'] == '处理中'
    assert row['person'] == person.id
    assert row['personName'] == '张三'
    assert row['hasEvidence'] is False
    assert FeedbackRecord.objects.get(pk=row['id']).status == FeedbackRecord.Status.PROCESSING


def test_create_feedback_with_evidence_is_counted_as_has_evidence():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')

    resp = _create_feedback(client, person, attachments=['工单#123'])
    assert resp.status_code == 201
    assert resp.json()['data']['hasEvidence'] is True


def test_create_feedback_rejects_person_out_of_visible_scope():
    """写端点也必须收窄可见范围 —— 否则「看不到却能改」是更严重的越权。"""
    mentor = make_user(role_code='MENTOR')
    client = client_for(mentor)
    mine = make_person(name='徒弟', mentor=mentor)
    other = make_person(name='别人的徒弟')

    resp = _create_feedback(client, other)
    assert resp.status_code == 400, resp.content.decode()
    assert '可见范围' in str(resp.json())
    assert FeedbackRecord.objects.count() == 0

    assert _create_feedback(client, mine).status_code == 201


# ---------------------------------------------------------------------------
# 办结状态机
# ---------------------------------------------------------------------------
def test_resolve_moves_processing_to_resolved_with_handler():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    created = _create_feedback(client, person).json()['data']

    resp = client.post(f'{BASE}/feedback-records/{created["id"]}/resolve/', {}, format='json')
    assert resp.status_code == 200, resp.content.decode()
    row = resp.json()['data']
    assert row['status'] == '已解决'
    assert row['handler'] == admin.id
    assert row['handledAt']

    stored = FeedbackRecord.objects.get(pk=created['id'])
    assert stored.status == FeedbackRecord.Status.RESOLVED
    assert stored.handler_id == admin.id
    assert stored.handled_at is not None


def test_resolve_on_closed_record_is_rejected():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    created = _create_feedback(client, person).json()['data']

    FeedbackRecord.objects.filter(pk=created['id']).update(status=FeedbackRecord.Status.CLOSED)
    resp = client.post(f'{BASE}/feedback-records/{created["id"]}/resolve/', {}, format='json')
    assert resp.status_code == 400
    assert '闭环' in str(resp.json())


# ---------------------------------------------------------------------------
# 可见范围：导师只见徒弟
# ---------------------------------------------------------------------------
def test_mentor_sees_only_own_mentees_feedbacks():
    mentor = make_user(role_code='MENTOR')
    client = client_for(mentor)
    mine = make_person(name='徒弟', mentor=mentor)
    other = make_person(name='别人的徒弟')

    # 「别人的」记录由超管建 —— 导师自己建会被写端点的可见范围校验拒掉
    admin_client = client_for(admin_user())
    _create_feedback(admin_client, mine, content='我的徒弟的问题')
    _create_feedback(admin_client, other, content='别人的问题')

    resp = client.get(f'{BASE}/feedback-records/', {'page_size': 100})
    assert resp.status_code == 200, resp.content.decode()
    rows = list_rows(resp.json())
    assert len(rows) == 1
    assert rows[0]['personName'] == '徒弟'


# ---------------------------------------------------------------------------
# 过滤：分类 / 状态 / 关键词
# ---------------------------------------------------------------------------
def test_filters_by_category_and_status():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    _create_feedback(client, person, category='issue', type='进度滞后')
    _create_feedback(client, person, category='mentor', type='带教建议')

    resp = client.get(f'{BASE}/feedback-records/', {'category': 'mentor'})
    rows = list_rows(resp.json())
    assert len(rows) == 1
    assert rows[0]['category'] == 'mentor'

    resp = client.get(f'{BASE}/feedback-records/', {'status': '处理中'})
    assert len(list_rows(resp.json())) == 2


def test_keyword_search_matches_name_content_and_type():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    other = make_person(name='李四')
    _create_feedback(client, person, content='本月任务完成度偏低')
    _create_feedback(client, other, type='考勤异常', content='迟到三次')

    # 内容命中
    resp = client.get(f'{BASE}/feedback-records/', {'kw': '完成度'})
    rows = list_rows(resp.json())
    assert len(rows) == 1
    assert rows[0]['content'] == '本月任务完成度偏低'

    # 类型命中
    resp = client.get(f'{BASE}/feedback-records/', {'kw': '考勤'})
    rows = list_rows(resp.json())
    assert len(rows) == 1
    assert rows[0]['type'] == '考勤异常'

    # 姓名命中（跨人）
    resp = client.get(f'{BASE}/feedback-records/', {'kw': '李四'})
    rows = list_rows(resp.json())
    assert len(rows) == 1
    assert rows[0]['personName'] == '李四'


# ---------------------------------------------------------------------------
# 统计概览：4 卡
# ---------------------------------------------------------------------------
def test_stats_overview_counts_four_cards_and_attendance():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')

    _create_feedback(client, person, attachments=['证据A'])
    _create_feedback(client, person, attachments=[])
    resolved = _create_feedback(client, person).json()['data']
    client.post(f'{BASE}/feedback-records/{resolved["id"]}/resolve/', {}, format='json')

    from apps.campus_assessment.models import AttendanceMonthly
    AttendanceMonthly.objects.create(
        person=person, ym='2026-07', attend_days=20, late_count=2, leave_days=1,
    )

    resp = client.get(f'{BASE}/stats/overview/')
    assert resp.status_code == 200, resp.content.decode()
    data = resp.json()['data']
    assert data['feedback']['total'] == 3
    assert data['feedback']['processing'] == 2
    assert data['feedback']['resolvedTotal'] == 1
    assert data['feedback']['withEvidence'] == 1
    assert data['attendance']['attendDays'] == 20
    assert data['attendance']['lateCount'] == 2
    assert data['attendance']['leaveDays'] == 1


def test_feedback_date_is_indexed_field():
    """date 字段是 db_index（契约 §2.1）—— 列表默认按日期倒序。"""
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    _create_feedback(client, person, date='2026-06-01')
    _create_feedback(client, person, date='2026-07-01')

    resp = client.get(f'{BASE}/feedback-records/', {'page_size': 100})
    rows = list_rows(resp.json())
    assert [row['date'] for row in rows] == ['2026-07-01', '2026-06-01']
    assert FeedbackRecord._meta.get_field('date').db_index is True
    assert FeedbackRecord._meta.get_field('date').null is False
