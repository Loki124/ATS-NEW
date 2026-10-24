"""restore 端点的行级可见范围 + 月报评分状态机（2026-10-24 整改）。

**缺陷 1（越权恢复）**：`SoftDeleteRestoreMixin` 在 restore 动作里把取数来源换成
`model.all_objects`（含软删行），**只**保留 `scope_queryset()` 这一层过滤；
可见范围若只写在 `get_queryset()` 里 → restore 路径上被整层丢弃 →
带教导师只要拿到 id 就能复活**别人（可见范围外）**的软删行。
正确语义：**只能恢复本用户可见范围内的软删行**，范围外一律 404（不泄露存在性）。

**缺陷 2（评分时机）**：契约 §2.2「POST monthly-reports/{id}/score/ → 写 MonthlyReportScore
并回算 final_score，status=scored」—— 原实现要两个角色都评了才置 `scored`。
现改为**评分落库即置 `scored`**；另一角色未评时其权重项不参与回算（不是「打了 0 分」），
响应里 `pending` / `role_scores` 标出未评分的角色。

**缺陷 4（属性名）**：契约 §1.2 写 `permission_map`，仓库运行时读 `permission_required_map`
→ 两个属性都要有，且值必须一致。
"""
from datetime import date

import pytest

from apps.campus_assessment.models import (
    FeedbackRecord,
    FiveForceScore,
    MonthlyAssessment,
    MonthlyReport,
    MonthlyReportScore,
)
from apps.campus_assessment.tests import (
    BASE,
    admin_user,
    client_for,
    make_person,
    make_user,
)
from apps.campus_assessment.views import (
    AssessmentTemplateViewSet,
    AttendanceMonthlyViewSet,
    AttendanceRecordViewSet,
    FeedbackRecordViewSet,
    FiveForceScoreViewSet,
    MonthlyAssessmentViewSet,
    MonthlyReportViewSet,
    ProbationViewSet,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# 装置
# ---------------------------------------------------------------------------
@pytest.fixture
def mentor_a():
    """导师 A（V2 角色 MENTOR + 本域资源码授权）。"""
    return make_user(role_code='MENTOR')


@pytest.fixture
def mentor_b():
    """导师 B —— 用来造「A 看不见的人」。"""
    return make_user(role_code='MENTOR')


def _soft_deleted_feedback(person, content='带教反馈'):
    """一条已软删的反馈记录（直接落库，绕开写端点的可见范围校验）。"""
    row = FeedbackRecord.objects.create(
        person=person,
        date=date(2026, 7, 1),
        content=content,
    )
    row.soft_delete()
    return row


# ---------------------------------------------------------------------------
# 缺陷 1：restore 越权
# ---------------------------------------------------------------------------
class TestRestore可见范围:
    """restore 只能恢复「本用户可见范围内」的软删行。"""

    def test_导师不能恢复可见范围外的软删反馈(self, mentor_a, mentor_b):
        """A 恢复「B 的徒弟」的软删反馈 → 404（不是 200），且行保持软删。"""
        client = client_for(mentor_a)
        person_b = make_person(name='B的徒弟', mentor=mentor_b)
        row = _soft_deleted_feedback(person_b)

        resp = client.post(f'{BASE}/feedback-records/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 404, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is not None, '越权恢复后软删标记被清掉了'

    def test_导师能恢复自己范围内的软删反馈(self, mentor_a):
        """A 恢复自己徒弟的软删反馈 → 200，行被复活。"""
        client = client_for(mentor_a)
        person = make_person(name='我的徒弟', mentor=mentor_a)
        row = _soft_deleted_feedback(person)

        resp = client.post(f'{BASE}/feedback-records/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 200, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is None

    def test_可见范围外的月度考核同样不可恢复(self, mentor_a, mentor_b):
        """不只反馈记录：所有带人员维度的考核表都受同一收口约束。"""
        client = client_for(mentor_a)
        person_b = make_person(name='B的徒弟2', mentor=mentor_b)
        row = MonthlyAssessment.objects.create(person=person_b, ym='2026-07', kpi=90, exam=80)
        row.soft_delete()

        resp = client.post(f'{BASE}/monthly-assessments/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 404, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is not None

    def test_自己范围内的月度考核可恢复(self, mentor_a):
        client = client_for(mentor_a)
        person = make_person(name='我的徒弟2', mentor=mentor_a)
        row = MonthlyAssessment.objects.create(person=person, ym='2026-07', kpi=90, exam=80)
        row.soft_delete()

        resp = client.post(f'{BASE}/monthly-assessments/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 200, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is None

    def test_超管可恢复任意软删行(self, mentor_b):
        """超管不受可见范围收窄（可见范围助手对超管放行）。"""
        client = client_for(admin_user())
        person_b = make_person(name='B的徒弟3', mentor=mentor_b)
        row = _soft_deleted_feedback(person_b)

        resp = client.post(f'{BASE}/feedback-records/{row.id}/restore/', {}, format='json')
        assert resp.status_code == 200, resp.content.decode()

        row.refresh_from_db()
        assert row.deleted_at is None


# ---------------------------------------------------------------------------
# 缺陷 2：月报评分置 scored 的时机
# ---------------------------------------------------------------------------
BUSINESS = {'case': 4, 'insight': 3, 'problem': 2, 'clarity': 1, 'executable': 0}
GROWTH = {'case': 2, 'insight': 2, 'problem': 2, 'clarity': 2, 'executable': 2}


def _create_report(client, person, ym='2026-07'):
    resp = client.post(
        f'{BASE}/monthly-reports/', {'person': person.id, 'ym': ym}, format='json',
    )
    assert resp.status_code == 201, resp.content.decode()
    return resp.json()['data']


def _score(client, report_id, role, items, comment=''):
    payload = {'role': role, 'comment': comment}
    payload.update(items)
    return client.post(f'{BASE}/monthly-reports/{report_id}/score/', payload, format='json')


class Test月报评分状态机:
    """契约 §2.2：评分落库即 `status=scored`，final_score 按已有侧回算。"""

    def test_单角色评分即置已评分(self):
        """只评业务导师 → 状态置 scored，综合分按业务侧折算（10×0.7 = 7.0）。"""
        client = client_for(admin_user())
        person = make_person(name='张三')
        report = _create_report(client, person)
        client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')

        resp = _score(client, report['id'], 'business', BUSINESS, comment='案例扎实')
        assert resp.status_code == 200, resp.content.decode()
        data = resp.json()['data']

        # 契约字面口径：评分即 scored
        assert data['report']['status'] == 'scored'
        # 另一角色未评 → 其权重项不参与回算（业务 10 分 → 10×0.7 = 7.0）
        assert float(data['report']['finalScore']) == 7.0
        assert float(data['report']['businessScore']) == 10.0
        # 未评分的角色用 None 表达「未评」，不是 0 分
        # （API 边界统一 camelCase，故键名是 roleScores）
        assert data['pending'] == ['growth']
        assert data['roleScores']['business'] == 10.0
        assert data['roleScores']['growth'] is None

        stored = MonthlyReport.objects.get(pk=report['id'])
        assert stored.status == MonthlyReport.Status.SCORED
        assert float(stored.final_score) == 7.0

    def test_另一角色补评后按七三完整重算(self):
        """成长导师补评 → final_score = 10×0.7 + 10×0.3 = 10.0。"""
        client = client_for(admin_user())
        person = make_person(name='李四')
        report = _create_report(client, person)
        client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')

        _score(client, report['id'], 'business', BUSINESS)
        resp = _score(client, report['id'], 'growth', GROWTH)
        assert resp.status_code == 200, resp.content.decode()
        data = resp.json()['data']

        assert data['report']['status'] == 'scored'
        assert data['pending'] == []
        assert float(data['report']['finalScore']) == 10.0
        assert data['roleScores'] == {'business': 10.0, 'growth': 10.0}

        stored = MonthlyReport.objects.get(pk=report['id'])
        assert stored.status == MonthlyReport.Status.SCORED
        assert float(stored.final_score) == 10.0

    def test_只评成长导师时按成长侧折算(self):
        """缺业务导师时：综合分 = 成长总分×0.3（未评分角色的权重项不参与）。"""
        client = client_for(admin_user())
        person = make_person(name='王五')
        report = _create_report(client, person)
        client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')

        resp = _score(client, report['id'], 'growth', GROWTH)
        assert resp.status_code == 200, resp.content.decode()
        data = resp.json()['data']

        assert data['report']['status'] == 'scored'
        assert float(data['report']['finalScore']) == 3.0  # 10×0.3
        assert data['pending'] == ['business']
        assert data['roleScores']['business'] is None

    def test_评分明细仍只落一条角色记录(self):
        client = client_for(admin_user())
        person = make_person(name='赵六')
        report = _create_report(client, person)
        client.post(f'{BASE}/monthly-reports/{report["id"]}/submit/', {}, format='json')

        _score(client, report['id'], 'business', BUSINESS)
        assert MonthlyReportScore.objects.filter(report_id=report['id']).count() == 1
        row = MonthlyReportScore.objects.get(report_id=report['id'])
        assert row.role == MonthlyReportScore.Role.BUSINESS
        assert float(row.total) == 10.0


# ---------------------------------------------------------------------------
# 缺陷 4：permission_map 属性名别名
# ---------------------------------------------------------------------------
class Test权限映射别名:
    """契约 §1.2 写 `permission_map`，仓库运行时读 `permission_required_map` → 两者都要在。"""

    def test_每个ViewSet都有与运行时一致的permission_map别名(self):
        viewsets = [
            MonthlyAssessmentViewSet,
            AssessmentTemplateViewSet,
            FiveForceScoreViewSet,
            AttendanceRecordViewSet,
            AttendanceMonthlyViewSet,
            FeedbackRecordViewSet,
            MonthlyReportViewSet,
            ProbationViewSet,
        ]
        for view in viewsets:
            assert hasattr(view, 'permission_map'), f'{view.__name__} 缺 permission_map 别名'
            assert view.permission_map == view.permission_required_map, (
                f'{view.__name__} 的 permission_map 与 permission_required_map 不一致'
            )
