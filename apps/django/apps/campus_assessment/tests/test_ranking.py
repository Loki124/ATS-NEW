"""排名算法护栏（契约 §2.4：5 个公式各 ≥1 例 + 边界；逆向清单 §5 A1~A9）。

本文件把**公式本身**与**端点取数**分开验证：

1. 纯公式层（`apps.campus_assessment.ranking`）—— 逐条锁死 A1~A9 的数值；
   其中包含若干**能区分 Python 银行家舍入与 JS Math.round** 的用例
   （原始实现是 JS，.5 一律向 +∞ 进位，Python round() 是「银行家舍入」，
   两者在 88.5 / 80.5 / 20.25 这类值上结果不同 —— 必须锁死 JS 语义）。
2. 端点层（`ranking/composite/`、`ranking/teacher/`）—— 真跑数据，断言名次与维度值。
"""
from datetime import date
from decimal import Decimal

import pytest

from apps.campus_assessment import ranking as R
from apps.campus_assessment.models import (
    AttendanceMonthly,
    FiveForceScore,
    MonthlyAssessment,
)
from apps.campus_assessment.tests import (
    BASE,
    admin_user,
    client_for,
    make_classroom,
    make_person,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# A1 月度总分 = round(KPI×0.6 + 考试×0.4) + 加减分
# ---------------------------------------------------------------------------
class TestA1MonthlyTotal:
    def test_basic(self):
        assert R.monthly_total_score(90, 90, 0) == Decimal(90)
        assert R.monthly_total_score(85, 90, 3) == Decimal(90)
        assert R.monthly_total_score(80, 70, -1) == Decimal(75)

    def test_js_rounding_semantics(self):
        """88.5 → 89（JS Math.round），Python round() 会给 88 —— 必须锁死 JS 语义。"""
        assert R.monthly_total_score(Decimal('87.5'), 90, 0) == Decimal(89)

    def test_adjust_is_added_after_rounding(self):
        """加减分是整数分，不参与加权分的小数进位。"""
        assert R.monthly_total_score(90, 90, 2) == Decimal(92)


# ---------------------------------------------------------------------------
# A2 累计综合均分 = 所有月度 totalScore 的算术平均（1 位）
# ---------------------------------------------------------------------------
class TestA2AvgTotal:
    def test_basic(self):
        assert R.avg_total([90, 80, 85]) == Decimal('85.0')
        assert R.avg_total([Decimal('90'), Decimal('81')]) == Decimal('85.5')

    def test_empty_returns_none(self):
        """无数据返回 None（不是 0 —— 「没考核过」≠「考了 0 分」）。"""
        assert R.avg_total([]) is None


# ---------------------------------------------------------------------------
# KPI 维度 = round(所有月度 kpi 的算术平均)
# ---------------------------------------------------------------------------
class TestDimKpi:
    def test_basic(self):
        assert R.dim_kpi([80, 85, 90]) == Decimal(85)

    def test_js_rounding_semantics(self):
        """80.5 → 81（JS），Python round() 会给 80。"""
        assert R.dim_kpi([80, 81]) == Decimal(81)

    def test_empty_returns_none(self):
        assert R.dim_kpi([]) is None


# ---------------------------------------------------------------------------
# A4 学习成长 = round(mean(课程进度均值, 考试得分均值))（有哪项算哪项）
# ---------------------------------------------------------------------------
class TestA4DimLearn:
    def test_both_sources(self):
        assert R.dim_learn(80, 90) == Decimal(85)

    def test_only_one_source(self):
        assert R.dim_learn(80, None) == Decimal(80)
        assert R.dim_learn(None, 90) == Decimal(90)

    def test_no_source_returns_none(self):
        assert R.dim_learn(None, None) is None


# ---------------------------------------------------------------------------
# A5 五行五力 = 5 维均值
# ---------------------------------------------------------------------------
class TestA5DimForce:
    def test_basic(self):
        assert R.dim_force([90, 90, 90, 90, 90]) == Decimal(90)
        assert R.dim_force([80, 90, 70, 85, 75]) == Decimal(80)

    def test_empty_returns_none(self):
        assert R.dim_force([]) is None


# ---------------------------------------------------------------------------
# A6 附加分 = Σ活动奖励分值 + Σ历月加减分
# ---------------------------------------------------------------------------
class TestA6DimAdd:
    def test_reward_text_parsing(self):
        assert R.parse_reward('+3 分') == 3
        assert R.parse_reward('-2分') == -2
        assert R.parse_reward('无奖励') == 0
        assert R.parse_reward(None) == 0

    def test_sum(self):
        assert R.dim_add(['+3 分'], [2, -1]) == Decimal(4)
        assert R.dim_add([], []) == Decimal(0)


# ---------------------------------------------------------------------------
# A3 综合得分 = round(KPI×0.5) + round(学习成长×0.3) + round(五行五力×0.2) + 附加分
# ---------------------------------------------------------------------------
class TestA3Composite:
    def test_basic(self):
        # round(40) + round(27) + round(14) + 5 = 86
        assert R.composite_score(80, 90, 70, 5) == Decimal(86)

    def test_missing_dimension_counts_zero(self):
        """缺学习数据 → 该项按 0 计（无数据既不加分也不额外惩罚）。"""
        assert R.composite_score(90, None, 90, 0) == Decimal(63)

    def test_each_term_rounded_separately(self):
        """逐项取整后相加（不是先加权求和再取整）—— 契约 §2.3 的写法。

        81×0.5 = 40.5 → JS 取 41（Python 银行家舍入会给 40），
        81×0.3 = 24.3 → 24，81×0.2 = 16.2 → 16 → 合计 81。
        """
        assert R.composite_score(81, 81, 81, 0) == Decimal(81)


# ---------------------------------------------------------------------------
# A9 考勤维度 = round(Σ(出勤 − 迟到×0.5) / 月数, 1)
# ---------------------------------------------------------------------------
class TestA9AttendanceDim:
    def test_basic(self):
        # ((20-1) + (22-0.5)) / 2 = 20.25 → 20.3（JS 语义）
        assert R.attendance_dim([
            {'attend_days': 20, 'late_count': 2},
            {'attend_days': 22, 'late_count': 1},
        ]) == Decimal('20.3')

    def test_empty_returns_none(self):
        assert R.attendance_dim([]) is None


# ---------------------------------------------------------------------------
# A7 月报综合得分
# ---------------------------------------------------------------------------
class TestA7MonthlyReport:
    def test_role_total_is_sum_of_five_items(self):
        assert R.report_role_total(1, 2, 3, 4, 5) == Decimal(15)
        assert R.report_role_total(0, 0, 0, 0, 0) == Decimal(0)

    def test_final_score_weighted_70_30(self):
        assert R.report_final_score(80, 90) == Decimal('83.0')
        # 59.5 + 27.75 = 87.25 → 87.3（JS 语义；Python round 给 87.2）
        assert R.report_final_score(85, Decimal('92.5')) == Decimal('87.3')


# ---------------------------------------------------------------------------
# A8 班主任排名 + 并列名次
# ---------------------------------------------------------------------------
class TestA8TeacherRanking:
    def test_avg_total_and_rank_avg(self):
        assert R.teacher_avg_total([80, 90]) == Decimal('85.0')
        assert R.teacher_rank_avg([1, 2]) == Decimal('1.5')
        assert R.teacher_avg_total([]) is None

    def test_tied_ranks_use_1224(self):
        """并列名次：同分同名次，后续名次跳过占位（1,1,3）。"""
        assert R.competition_ranks([10, 10, 8]) == [1, 1, 3]
        assert R.competition_ranks([10, 9, 8]) == [1, 2, 3]


# ---------------------------------------------------------------------------
# 端点层：综合排名
# ---------------------------------------------------------------------------
def _make_checked_assessment(person, ym, kpi, exam, adjust=0):
    return MonthlyAssessment.objects.create(
        person=person, ym=ym, kpi=kpi, exam=exam, adjust=adjust,
        status=MonthlyAssessment.Status.CHECKED,
    )


def _make_five_force(person, value, scored_at=date(2026, 7, 15)):
    return FiveForceScore.objects.create(
        person=person, learning=value, execution=value, collaboration=value,
        innovation=value, resilience=value, scored_at=scored_at,
    )


def test_composite_ranking_endpoint_orders_and_computes():
    """综合排名端点：名次 + 各维度实际值 + 折算得分。"""
    admin = admin_user()
    client = client_for(admin)

    person_a = make_person(name='甲')
    person_b = make_person(name='乙')
    _make_checked_assessment(person_a, '2026-07', 90, 90)
    _make_checked_assessment(person_b, '2026-07', 80, 80)
    _make_five_force(person_a, 90)
    _make_five_force(person_b, 80)
    AttendanceMonthly.objects.create(
        person=person_a, ym='2026-07', attend_days=20, late_count=2,
    )
    AttendanceMonthly.objects.create(
        person=person_b, ym='2026-07', attend_days=22, late_count=1,
    )

    resp = client.get(f'{BASE}/ranking/composite/', {'dim': 'comp'})
    assert resp.status_code == 200, resp.content.decode()
    rows = resp.json()['data']['list']
    assert len(rows) == 2

    top = rows[0]
    assert top['name'] == '甲'
    assert top['rank'] == 1
    # 端点是自造 JSON，Decimal 由 JSON 编码器转成数字（不是 DRF DecimalField 的字符串）
    assert top['total'] == 90.0            # A1 → A2
    assert top['kpi'] == 90                # KPI 维度
    assert top['exam'] == 90.0             # 月度考试均值
    assert top['force'] == 90              # A5
    assert top['add'] == 0                 # A6
    assert top['attend'] == 19.0           # A9：(20 - 2×0.5)
    # A3：round(90×0.5) + round(0×0.3) + round(90×0.2) + 0 = 45 + 0 + 18
    assert top['comp'] == 63
    assert rows[1]['name'] == '乙'
    assert rows[1]['rank'] == 2
    assert rows[1]['comp'] == 56


def test_composite_ranking_dim_switch_orders_by_actual_value():
    """切维度 → 按该维度实际值降序（折算得分同步变化）。"""
    admin = admin_user()
    client = client_for(admin)

    person_a = make_person(name='甲')
    person_b = make_person(name='乙')
    # A 的 KPI 高、B 的附加分高：comp 维度下 A 领先，add 维度下 B 领先
    _make_checked_assessment(person_a, '2026-07', 100, 100, adjust=0)
    _make_checked_assessment(person_b, '2026-07', 60, 60, adjust=10)

    resp = client.get(f'{BASE}/ranking/composite/', {'dim': 'add'})
    assert resp.status_code == 200
    rows = resp.json()['data']['list']
    assert rows[0]['name'] == '乙'
    assert rows[0]['add'] == 10
    assert rows[0]['dimValue'] == 10
    assert rows[1]['name'] == '甲'
    assert rows[1]['rank'] == 2


def test_composite_ranking_excludes_resigned_and_keeps_tied_ranks():
    """排名范围 = 全体可见**在校**人员（排除已离职）；并列名次同名次。"""
    admin = admin_user()
    client = client_for(admin)

    p1 = make_person(name='甲')
    p2 = make_person(name='乙')
    resigned = make_person(name='丙', status='离职')
    _make_checked_assessment(p1, '2026-07', 90, 90)
    _make_checked_assessment(p2, '2026-07', 90, 90)
    _make_checked_assessment(resigned, '2026-07', 99, 99)

    resp = client.get(f'{BASE}/ranking/composite/', {'dim': 'comp'})
    assert resp.status_code == 200
    rows = resp.json()['data']['list']
    names = [row['name'] for row in rows]
    assert '丙' not in names, '已离职人员不应进入排名'
    assert [row['rank'] for row in rows] == [1, 1], '并列名次应同名次'


def test_composite_ranking_without_any_data():
    """无任何考核数据 → 空列表（不 500、不报 500 错）。"""
    admin = admin_user()
    client = client_for(admin)
    make_person(name='甲')
    resp = client.get(f'{BASE}/ranking/composite/', {'dim': 'comp'})
    assert resp.status_code == 200
    rows = resp.json()['data']['list']
    assert len(rows) == 1
    assert rows[0]['total'] is None
    assert rows[0]['comp'] == 0


def test_composite_ranking_filters_by_ym_and_class():
    """?ym= 与 ?class= 收窄取数范围。"""
    admin = admin_user()
    client = client_for(admin)

    classroom = make_classroom()
    person_a = make_person(name='甲', class_room=classroom)
    person_b = make_person(name='乙')
    _make_checked_assessment(person_a, '2026-07', 90, 90)
    _make_checked_assessment(person_b, '2026-07', 80, 80)
    _make_checked_assessment(person_a, '2026-06', 70, 70)

    resp = client.get(f'{BASE}/ranking/composite/', {'ym': '2026-07'})
    rows = resp.json()['data']['list']
    assert rows[0]['kpi'] == 90, 'ym 过滤后只算 2026-07 的考核'

    resp = client.get(f'{BASE}/ranking/composite/', {'class': classroom.code})
    rows = resp.json()['data']['list']
    assert len(rows) == 1
    assert rows[0]['name'] == '甲'


# ---------------------------------------------------------------------------
# 端点层：班主任排名
# ---------------------------------------------------------------------------
def test_teacher_ranking_endpoint():
    """班主任排名：avgTotal + 五维平均名次 + 学生分项名次明细。"""
    from apps.campus_assessment.tests import make_user

    admin = admin_user()
    client = client_for(admin)
    teacher = make_user(role_code='HEAD_TEACHER')

    student_a = make_person(name='甲', head_teacher=teacher)
    student_b = make_person(name='乙', head_teacher=teacher)
    _make_checked_assessment(student_a, '2026-07', 90, 90)
    _make_checked_assessment(student_b, '2026-07', 80, 80)
    AttendanceMonthly.objects.create(
        person=student_a, ym='2026-07', attend_days=20, late_count=0,
    )
    AttendanceMonthly.objects.create(
        person=student_b, ym='2026-07', attend_days=22, late_count=1,
    )

    resp = client.get(f'{BASE}/ranking/teacher/')
    assert resp.status_code == 200, resp.content.decode()
    data = resp.json()['data']

    assert data['dims'] == [
        {'key': 'total', 'label': '综合'}, {'key': 'kpi', 'label': 'KPI'},
        {'key': 'exam', 'label': '考试'}, {'key': 'learn', 'label': '学习'},
        {'key': 'attend', 'label': '考勤'},
    ]
    teacher_rows = [t for t in data['teachers'] if t['teacherId'] == teacher.pk]
    assert len(teacher_rows) == 1
    row = teacher_rows[0]
    assert row['studentCount'] == 2
    # 所带学生 avgTotal 的算术平均：(90.0 + 80.0) / 2 = 85.0
    assert row['avgTotal'] == 85.0
    # 综合名次：甲 1 / 乙 2 → 平均 1.5
    assert row['rankAvg']['total'] == 1.5
    assert row['rankAvg']['kpi'] == 1.5
    # 考勤：乙(21.5) 第 1、甲(20.0) 第 2 → 平均 1.5
    assert row['rankAvg']['attend'] == 1.5

    students = data['students']
    assert len(students) == 2
    top = [s for s in students if s['name'] == '甲'][0]
    assert top['ranks']['total'] == 1
    assert top['ranks']['attend'] == 2


def test_teacher_ranking_hidden_for_out_of_scope_students():
    """可见范围收窄：导师只看得到自己徒弟所在班的聚合。"""
    from apps.campus_assessment.tests import make_user

    mentor = make_user(role_code='MENTOR')
    client = client_for(mentor)

    teacher = make_user(role_code='HEAD_TEACHER')
    mine = make_person(name='徒弟', mentor=mentor, head_teacher=teacher)
    other = make_person(name='别人的徒弟', head_teacher=teacher)

    _make_checked_assessment(mine, '2026-07', 90, 90)
    _make_checked_assessment(other, '2026-07', 60, 60)

    resp = client.get(f'{BASE}/ranking/teacher/')
    assert resp.status_code == 200
    data = resp.json()['data']
    names = [s['name'] for s in data['students']]
    assert names == ['徒弟'], '导师只应看到自己徒弟的名次明细'
    teacher_rows = [t for t in data['teachers'] if t['teacherId'] == teacher.pk]
    assert teacher_rows[0]['studentCount'] == 1
    assert teacher_rows[0]['avgTotal'] == 90.0
