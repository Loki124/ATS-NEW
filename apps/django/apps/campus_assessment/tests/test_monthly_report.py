"""月报护栏（契约 §2.4：评分回算 70/30、提交状态机）。

口径来源：逆向清单 A7 / core.js:258 ——
`final_score = round(业务导师总分×0.7 + 成长导师总分×0.3, 1)`，
各角色总分 = case + insight + problem + clarity + executable 五子项之和。
"""
import pytest

from apps.campus_assessment.models import MonthlyReport, MonthlyReportScore
from apps.campus_assessment.tests import (
    BASE,
    admin_user,
    client_for,
    list_rows,
    make_person,
    make_user,
)

pytestmark = pytest.mark.django_db


def _create_report(client, person, ym='2026-07'):
    resp = client.post(f'{BASE}/monthly-reports/', {
        'person': person.id,
        'ym': ym,
    }, format='json')
    assert resp.status_code == 201, resp.content.decode()
    return resp.json()['data']


def _score(client, report_id, role, items, comment=''):
    payload = {'role': role, 'comment': comment}
    payload.update(items)
    return client.post(f'{BASE}/monthly-reports/{report_id}/score/', payload, format='json')


BUSINESS = {'case': 4, 'insight': 3, 'problem': 2, 'clarity': 1, 'executable': 0}
GROWTH = {'case': 2, 'insight': 2, 'problem': 2, 'clarity': 2, 'executable': 2}


# ---------------------------------------------------------------------------
# 提交状态机
# ---------------------------------------------------------------------------
def test_submit_moves_draft_to_submitted():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    report = _create_report(client, person)
    assert report['status'] == 'draft'

    resp = client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')
    assert resp.status_code == 200, resp.content.decode()
    row = resp.json()['data']
    assert row['status'] == 'submitted'
    assert row['submittedAt']

    stored = MonthlyReport.objects.get(pk=report['id'])
    assert stored.status == MonthlyReport.Status.SUBMITTED
    assert stored.submitted_at is not None


def test_submit_twice_is_rejected():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    report = _create_report(client, person)
    client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')
    resp = client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')
    assert resp.status_code == 400
    assert '草稿' in str(resp.json())


def test_scoring_draft_report_is_rejected():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    report = _create_report(client, person)
    resp = _score(client, report['id'], 'business', BUSINESS)
    assert resp.status_code == 400
    assert '提交' in str(resp.json())


# ---------------------------------------------------------------------------
# 「待评分」过滤（?pending=1）
# ---------------------------------------------------------------------------
def test_pending_filter_keeps_reports_with_missing_role():
    """待评分 = 两个角色都有评分明细才算评完（**不能**用 status 表达）。

    🔴 契约 §2.2「评分落库即置 scored」→ 只评了业务导师的月报状态**也是 scored**，
    但成长导师仍待评。若前端按 `status=submitted` 过滤「待评分」，这些月报会被筛掉
    ⇒ 后端提供 `?pending=1`，口径 = 「缺任一角色评分即待评分」。
    """
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')

    # 甲：只评业务导师 → 状态已 scored，但成长导师仍待评 ⇒ 应出现在待评分列表
    r1 = _create_report(client, person, ym='2026-07')
    client.post(f'{BASE}/monthly-reports/{r1["id"]}/submit/', {}, format='json')
    _score(client, r1['id'], 'business', BUSINESS)

    # 乙：两个角色都评完 → 不应出现在待评分列表
    r2 = _create_report(client, person, ym='2026-08')
    client.post(f'{BASE}/monthly-reports/{r2["id"]}/submit/', {}, format='json')
    _score(client, r2['id'], 'business', BUSINESS)
    _score(client, r2['id'], 'growth', GROWTH)

    resp = client.get(f'{BASE}/monthly-reports/', {'pending': '1'})
    assert resp.status_code == 200, resp.content.decode()
    ids = {row['id'] for row in list_rows(resp.json())}
    assert r1['id'] in ids, '只评了业务导师的月报仍属待评分'
    assert r2['id'] not in ids, '两个角色都评完的月报不应出现在待评分列表'

    # 甲的状态确实是 scored（证明「按 status 过滤会漏掉它」这一前提成立）
    assert MonthlyReport.objects.get(pk=r1['id']).status == MonthlyReport.Status.SCORED


# ---------------------------------------------------------------------------
# 评分回算（A7）
# ---------------------------------------------------------------------------
def test_score_writes_detail_and_recalculates_final_score_70_30():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    report = _create_report(client, person)
    client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')

    # 只评业务导师 → 契约 §2.2「评分落库即置 scored」；
    # 综合分按**已有侧 × 其权重**回算（缺成长导师 → 不打 0 分，只算业务侧 10×0.7 = 7.0）
    resp = _score(client, report['id'], 'business', BUSINESS, comment='案例扎实')
    assert resp.status_code == 200, resp.content.decode()
    data = resp.json()['data']
    assert data['pending'] == ['growth']
    assert data['report']['status'] == 'scored'
    assert float(data['report']['finalScore']) == 7.0
    assert float(data['score']['total']) == 10.0

    # 成长导师补齐 → 回算 final_score = 10×0.7 + 10×0.3 = 10.0，状态置 scored
    resp = _score(client, report['id'], 'growth', GROWTH)
    assert resp.status_code == 200
    data = resp.json()['data']
    assert data['pending'] == []
    assert data['report']['status'] == 'scored'
    assert float(data['report']['finalScore']) == 10.0
    assert float(data['report']['businessScore']) == 10.0
    assert float(data['report']['growthScore']) == 10.0

    stored = MonthlyReport.objects.get(pk=report['id'])
    assert stored.status == MonthlyReport.Status.SCORED
    assert float(stored.final_score) == 10.0

    scores = MonthlyReportScore.objects.filter(report_id=report['id'])
    assert scores.count() == 2
    business = scores.get(role=MonthlyReportScore.Role.BUSINESS)
    assert float(business.total) == 10.0
    assert business.scorer_id == admin.id
    assert business.comment == '案例扎实'
    assert business.scored_at is not None


def test_final_score_uses_70_30_weighting():
    """业务 15 分 + 成长 10 分 → 15×0.7 + 10×0.3 = 13.5。"""
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    report = _create_report(client, person)
    client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')

    _score(client, report['id'], 'business', {'case': 5, 'insight': 4, 'problem': 3,
                                               'clarity': 2, 'executable': 1})
    resp = _score(client, report['id'], 'growth', GROWTH)
    assert resp.status_code == 200
    data = resp.json()['data']
    assert float(data['report']['finalScore']) == 13.5


def test_scoring_same_role_twice_updates_instead_of_duplicating():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    report = _create_report(client, person)
    client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')

    _score(client, report['id'], 'business', BUSINESS)
    resp = _score(client, report['id'], 'business', {'case': 1, 'insight': 1, 'problem': 1,
                                                     'clarity': 1, 'executable': 1})
    assert resp.status_code == 200
    assert float(resp.json()['data']['score']['total']) == 5.0
    assert MonthlyReportScore.objects.filter(report_id=report['id']).count() == 1


def test_score_rejects_invalid_role():
    admin = admin_user()
    client = client_for(admin)
    person = make_person(name='张三')
    report = _create_report(client, person)
    client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')
    resp = _score(client, report['id'], 'unknown', BUSINESS)
    assert resp.status_code == 400
    assert 'role' in str(resp.json())


# ---------------------------------------------------------------------------
# 可见范围
# ---------------------------------------------------------------------------
def test_monthly_report_list_scoped_to_visible_persons():
    mentor = make_user(role_code='MENTOR')
    client = client_for(mentor)
    mine = make_person(name='徒弟', mentor=mentor)
    other = make_person(name='别人的徒弟')

    # 「别人的」记录由超管建（导师自己建会被写端点的可见范围校验拒掉 —— 见
    # test_create_feedback_rejects_person_out_of_visible_scope 同款守卫）
    admin_client = client_for(admin_user())
    _create_report(admin_client, mine)
    _create_report(admin_client, other)

    resp = client.get(f'{BASE}/monthly-reports/', {'page_size': 100})
    assert resp.status_code == 200
    rows = list_rows(resp.json())
    assert len(rows) == 1
    assert rows[0]['person'] == mine.id
