"""学习域回归测试（课程 / 学习进度 / 学习记录 / 学习龙虎榜）。

覆盖契约 §3.3 的三项要求：
1. **进度累加** —— `learn-progress/{id}/record/` 累加 progress 与 minutes，
   progress 封顶 100，`done_at` 首次满 100 时写入（之后不刷新）；
2. **唯一约束** —— LearnProgress 一人 × 一门课只能一行（person + course）；
3. **学习龙虎榜** —— 每人聚合 { minutes, done, avgProg, total }，按 minutes 降序，
   **排除已离职人员**。

另含「可见范围」回归：导师只看得见自己带教的人的学习进度（契约 §1.3）。
"""
import pytest
from django.db import IntegrityError, transaction

from apps.campus_learning.models import Course, LearnProgress, LearnRecord

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-learning'


@pytest.fixture
def course(db):
    return Course.objects.create(code='C001', name='校招必修课', duration_min=60)


@pytest.fixture
def course2(db):
    return Course.objects.create(code='C002', name='校招选修课', duration_min=120)


# ---------------------------------------------------------------------------
# 进度累加
# ---------------------------------------------------------------------------
def test_record_accumulates_progress_and_minutes(auth_client, course, make_person):
    """记一次学习记录 → progress 与 minutes 都累加。"""
    person = make_person('甲同学')
    lp = LearnProgress.objects.create(person=person, course=course, progress=0, minutes=0)

    resp = auth_client.post(
        f'{BASE}/learn-progress/{lp.id}/record/',
        {'minutes': 30, 'progress': 40},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    lp.refresh_from_db()
    assert lp.progress == 40
    assert lp.minutes == 30

    resp = auth_client.post(
        f'{BASE}/learn-progress/{lp.id}/record/',
        {'minutes': 20, 'progress': 15},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    lp.refresh_from_db()
    assert lp.progress == 55
    assert lp.minutes == 50


def test_record_caps_progress_at_100(auth_client, course, make_person):
    """progress 封顶 100 —— 累加到 95 后再记 40 仍是 100，不是 135。"""
    person = make_person('乙同学')
    lp = LearnProgress.objects.create(person=person, course=course, progress=95, minutes=0)

    resp = auth_client.post(
        f'{BASE}/learn-progress/{lp.id}/record/',
        {'minutes': 30, 'progress': 40},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    lp.refresh_from_db()
    assert lp.progress == 100


def test_done_at_set_only_on_first_reaching_100(auth_client, course, make_person):
    """done_at 在**首次**满 100 时写入；之后再学习不刷新完成时间。"""
    person = make_person('丙同学')
    lp = LearnProgress.objects.create(person=person, course=course, progress=90, minutes=0)

    resp = auth_client.post(
        f'{BASE}/learn-progress/{lp.id}/record/',
        {'minutes': 30, 'progress': 40},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    lp.refresh_from_db()
    assert lp.progress == 100
    assert lp.done_at is not None
    first_done_at = lp.done_at

    resp = auth_client.post(
        f'{BASE}/learn-progress/{lp.id}/record/',
        {'minutes': 10, 'progress': 5},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    lp.refresh_from_db()
    assert lp.progress == 100
    assert lp.minutes == 40
    assert lp.done_at == first_done_at


def test_record_creates_learn_record_row(auth_client, course, make_person):
    """记学习记录同时写一条 LearnRecord 流水（人 / 课 / 分钟 / 备注）。"""
    person = make_person('丁同学')
    lp = LearnProgress.objects.create(person=person, course=course)

    resp = auth_client.post(
        f'{BASE}/learn-progress/{lp.id}/record/',
        {'minutes': 45, 'remark': '第 1 讲'},
        format='json',
    )
    assert resp.status_code == 200, resp.content

    assert LearnRecord.objects.count() == 1
    record = LearnRecord.objects.get()
    assert record.person_id == person.id
    assert record.course_id == course.id
    assert record.minutes == 45
    assert record.remark == '第 1 讲'


def test_record_rejects_non_positive_minutes(auth_client, course, make_person):
    """minutes 必填且必须为正 —— 静默失败是最贵的失败方式，必须 400。"""
    person = make_person('戊同学')
    lp = LearnProgress.objects.create(person=person, course=course)

    resp = auth_client.post(
        f'{BASE}/learn-progress/{lp.id}/record/', {'minutes': 0}, format='json',
    )
    assert resp.status_code == 400, resp.content
    assert LearnRecord.objects.count() == 0


# ---------------------------------------------------------------------------
# 唯一约束
# ---------------------------------------------------------------------------
def test_learn_progress_unique_person_course(course, make_person):
    """一人 × 一门课只能一行 —— 数据库唯一约束兜底。"""
    person = make_person('己同学')
    LearnProgress.objects.create(person=person, course=course)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LearnProgress.objects.create(person=person, course=course)


def test_learn_progress_duplicate_via_api_returns_400(auth_client, course, make_person):
    """重复建同一人同一门课 → 接口 400（不是 500）。"""
    person = make_person('庚同学')
    payload = {'person': person.id, 'course': course.id, 'progress': 10, 'minutes': 5}
    resp = auth_client.post(f'{BASE}/learn-progress/', payload, format='json')
    assert resp.status_code == 201, resp.content

    resp2 = auth_client.post(f'{BASE}/learn-progress/', payload, format='json')
    assert resp2.status_code == 400, resp2.content


# ---------------------------------------------------------------------------
# 学习龙虎榜
# ---------------------------------------------------------------------------
def test_learn_board_aggregates_per_person(auth_client, course, course2, make_person):
    """龙虎榜聚合：minutes / done / avgProg / total，且按 minutes 降序。"""
    p_a = make_person('甲')
    p_b = make_person('乙')
    p_c = make_person('丙')

    # 甲：2 门课，累计 60 分钟，均值 50%，完成 1 门
    LearnProgress.objects.create(person=p_a, course=course, progress=100, minutes=40)
    LearnProgress.objects.create(person=p_a, course=course2, progress=0, minutes=20)
    # 乙：1 门课，累计 100 分钟，均值 30%，完成 0 门
    LearnProgress.objects.create(person=p_b, course=course, progress=30, minutes=100)
    # 丙：没有任何学习记录 → 不上榜

    resp = auth_client.get(f'{BASE}/stats/learn-board/')
    assert resp.status_code == 200, resp.content
    rows = resp.json()['data']

    assert [r['name'] for r in rows] == ['乙', '甲']

    row_a = next(r for r in rows if r['name'] == '甲')
    assert row_a['id'] == p_a.id
    assert row_a['minutes'] == 60
    assert row_a['done'] == 1
    assert row_a['total'] == 2
    assert row_a['avgProg'] == 50.0

    row_b = next(r for r in rows if r['name'] == '乙')
    assert row_b['minutes'] == 100
    assert row_b['done'] == 0
    assert row_b['total'] == 1
    assert row_b['avgProg'] == 30.0


def test_learn_board_excludes_departed_person(auth_client, course, make_person):
    """**排除已离职人员** —— 离职者不在培养中，不上龙虎榜。"""
    stayed = make_person('在职同学')
    left = make_person('离职同学', status='离职')
    LearnProgress.objects.create(person=stayed, course=course, progress=100, minutes=60)
    LearnProgress.objects.create(person=left, course=course, progress=100, minutes=999)

    resp = auth_client.get(f'{BASE}/stats/learn-board/')
    assert resp.status_code == 200, resp.content
    rows = resp.json()['data']

    assert [r['name'] for r in rows] == ['在职同学']
    assert left.id not in [r['id'] for r in rows]


def test_learn_board_empty_when_no_records(auth_client):
    """无学习记录 → 空列表（不是 404）。"""
    resp = auth_client.get(f'{BASE}/stats/learn-board/')
    assert resp.status_code == 200, resp.content
    assert resp.json()['data'] == []


# ---------------------------------------------------------------------------
# 可见范围（契约 §1.3）
# ---------------------------------------------------------------------------
def test_learn_progress_scoped_to_visible_persons(mentor_client, mentor_user, course, make_person):
    """导师只看得见自己带教的人的学习进度。"""
    mine = make_person('我的徒弟', mentor=mentor_user)
    other = make_person('别人的徒弟')
    lp_mine = LearnProgress.objects.create(person=mine, course=course, minutes=10)
    LearnProgress.objects.create(person=other, course=course, minutes=20)

    resp = mentor_client.get(f'{BASE}/learn-progress/')
    assert resp.status_code == 200, resp.content
    ids = [r['id'] for r in resp.json()['data']]
    assert ids == [lp_mine.id]


def test_mentor_cannot_read_other_person_progress_by_id(mentor_client, mentor_user, course, make_person):
    """带 id 也读不到别人的进度 —— get_object() 复用 get_queryset() → 同样收窄。"""
    other = make_person('别人的徒弟')
    lp_other = LearnProgress.objects.create(person=other, course=course, minutes=20)

    resp = mentor_client.get(f'{BASE}/learn-progress/{lp_other.id}/')
    assert resp.status_code == 404, resp.content


def test_cannot_create_progress_for_invisible_person(mentor_client, course, make_person):
    """导师不能给「看不见的人」建学习记录（写入口也要收窄）。"""
    other = make_person('别人的徒弟')

    resp = mentor_client.post(
        f'{BASE}/learn-progress/',
        {'person': other.id, 'course': course.id, 'progress': 10, 'minutes': 5},
        format='json',
    )
    assert resp.status_code == 400, resp.content
