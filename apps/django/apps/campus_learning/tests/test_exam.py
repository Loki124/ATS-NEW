"""考试域回归测试（考试 / 成绩录入 / 考试排名）。

覆盖契约 §3.3 的两项要求：
1. **成绩录入自动判定通过** —— `passed` 由服务端按 `score >= exam.pass_score`
   判定，**不信任前端传值**（前端传 passed=True 也会被忽略）；
2. **排名与得分条** —— `exams/{id}/ranking/` 按分数降序、同分同名次，
   并输出得分条百分比 `score / full_score * 100`。

另含唯一约束（exam + person）与排名可见范围回归。
"""
import datetime

import pytest
from django.db import IntegrityError, transaction

from apps.campus_learning.models import Exam, ExamScore

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-learning'


@pytest.fixture
def exam(db):
    """满分 100 / 及格 60 的考试（`date` 是必填字段 —— 考试必须有考试日期）。"""
    return Exam.objects.create(
        name='校招阶段一考试', date=datetime.date(2026, 10, 20),
        full_score=100, pass_score=60, form=Exam.Form.ONLINE,
    )


# ---------------------------------------------------------------------------
# 通过判定
# ---------------------------------------------------------------------------
def test_exam_score_passed_auto_computed(auth_client, exam, make_person):
    """低于及格分 → passed=False；达到及格分 → passed=True（服务端判定）。"""
    person = make_person('甲同学')

    resp = auth_client.post(
        f'{BASE}/exam-scores/',
        {'exam': exam.id, 'person': person.id, 'score': '59.00'},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['passed'] is False

    resp = auth_client.post(
        f'{BASE}/exam-scores/',
        {'exam': exam.id, 'person': person.id, 'score': '60.00'},
        format='json',
    )
    # 同一人同一场考试 → 唯一约束 400
    assert resp.status_code == 400, resp.content


def test_exam_score_ignores_client_passed_value(auth_client, exam, make_person):
    """前端传 passed=True 但分数不及格 → 服务端仍判 False（不信前端）。"""
    person = make_person('乙同学')

    resp = auth_client.post(
        f'{BASE}/exam-scores/',
        {'exam': exam.id, 'person': person.id, 'score': '10.00', 'passed': True},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['passed'] is False
    assert ExamScore.objects.get().passed is False


def test_exam_score_passed_recomputed_on_update(auth_client, exam, make_person):
    """改分后重新判定 —— 及格 → 不及格，passed 跟着变。"""
    person = make_person('丙同学')
    resp = auth_client.post(
        f'{BASE}/exam-scores/',
        {'exam': exam.id, 'person': person.id, 'score': '80.00'},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    score_id = resp.json()['data']['id']
    assert resp.json()['data']['passed'] is True

    resp = auth_client.patch(
        f'{BASE}/exam-scores/{score_id}/', {'score': '20.00'}, format='json',
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()['data']['passed'] is False


def test_exam_score_unique_exam_person(exam, make_person):
    """一人 × 一场考试只能一行 —— 数据库唯一约束兜底。"""
    person = make_person('丁同学')
    ExamScore.objects.create(exam=exam, person=person, score=70, passed=True)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ExamScore.objects.create(exam=exam, person=person, score=80, passed=True)


# ---------------------------------------------------------------------------
# 排名
# ---------------------------------------------------------------------------
def test_exam_ranking_orders_by_score_with_tied_ranks(auth_client, exam, make_person):
    """按分数降序；**同分同名次**（竞赛式：1, 2, 2）。"""
    p1 = make_person('甲')
    p2 = make_person('乙')
    p3 = make_person('丙')
    ExamScore.objects.create(exam=exam, person=p1, score=90, passed=True)
    ExamScore.objects.create(exam=exam, person=p2, score=75, passed=True)
    ExamScore.objects.create(exam=exam, person=p3, score=75, passed=True)

    resp = auth_client.get(f'{BASE}/exams/{exam.id}/ranking/')
    assert resp.status_code == 200, resp.content
    rows = resp.json()['data']

    assert [r['score'] for r in rows] == [90.0, 75.0, 75.0]
    assert [r['rank'] for r in rows] == [1, 2, 2]
    assert rows[0]['name'] == '甲'
    assert rows[0]['percent'] == 90.0
    assert rows[0]['passed'] is True


def test_exam_ranking_percent_and_passed_flag(auth_client, exam, make_person):
    """得分条百分比 = 得分 / 满分 × 100；未达及格分 passed=False。"""
    person = make_person('乙')
    ExamScore.objects.create(exam=exam, person=person, score=45.5, passed=False)

    resp = auth_client.get(f'{BASE}/exams/{exam.id}/ranking/')
    assert resp.status_code == 200, resp.content
    row = resp.json()['data'][0]
    assert row['percent'] == 45.5
    assert row['passed'] is False
    assert row['rank'] == 1


def test_exam_ranking_scoped_to_visible_persons(mentor_client, mentor_user, exam, make_person):
    """排名只含可见人员的成绩 —— 导师看不到别人徒弟的成绩。"""
    mine = make_person('我的徒弟', mentor=mentor_user)
    other = make_person('别人的徒弟')
    ExamScore.objects.create(exam=exam, person=mine, score=90, passed=True)
    ExamScore.objects.create(exam=exam, person=other, score=50, passed=False)

    resp = mentor_client.get(f'{BASE}/exams/{exam.id}/ranking/')
    assert resp.status_code == 200, resp.content
    rows = resp.json()['data']
    assert len(rows) == 1
    assert rows[0]['name'] == '我的徒弟'


def test_exam_crud_roundtrip(auth_client, exam, make_person):
    """考试 CRUD 基本链路（建 → 查 → 改 → 软删 → 列表不再出现）。"""
    resp = auth_client.get(f'{BASE}/exams/')
    assert resp.status_code == 200, resp.content
    assert any(r['id'] == exam.id for r in resp.json()['data'])

    resp = auth_client.patch(
        f'{BASE}/exams/{exam.id}/', {'name': '改名后的考试'}, format='json',
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()['data']['name'] == '改名后的考试'

    resp = auth_client.delete(f'{BASE}/exams/{exam.id}/')
    assert resp.status_code == 200, resp.content

    resp = auth_client.get(f'{BASE}/exams/')
    assert not any(r['id'] == exam.id for r in resp.json()['data'])
