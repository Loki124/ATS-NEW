"""校招考核路由（挂在 /api/v1/campus-assessment/ 下）。

端点（契约 §2.2 逐条对齐）：
  CRUD   /monthly-assessments/                  月度考核  ?ym=&person=&status=&class=
  POST   /monthly-assessments/{id}/check/       核对通过（锁定当月并计入排名）
  POST   /monthly-assessments/{id}/adjust/      加减分 {adjust, reason}
  CRUD   /assessment-templates/                 考核模板（含 items 嵌套写入）
  CRUD   /five-forces/                         五行五力  ?person=
  CRUD   /attendance-records/                   每日打卡  ?date_from=&date_to=&person=
  GET    /attendance-records/daily-ranking/     当日打卡排名（含「与第1名差距」）
  CRUD   /attendance-monthly/                   月度考勤汇总  ?ym=
  CRUD   /feedback-records/                     反馈记录  ?category=&status=&kw=&person=
  POST   /feedback-records/{id}/resolve/        办结（→ 已解决 + 处理人/时间）
  CRUD   /monthly-reports/                      月报  ?ym=&person=&status=
  POST   /monthly-reports/{id}/submit/          提交月报
  POST   /monthly-reports/{id}/score/           评分（回算 final_score = 70/30）
  CRUD   /probations/                           试用期  ?person=
  POST   /probations/{id}/decide/               试用期决策 {decision, note}
  GET    /ranking/composite/                    综合排名 ?dim=&ym=&class=
  GET    /ranking/teacher/                      班主任排名
  GET    /stats/overview/                       4 卡统计 + 考勤汇总
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AssessmentTemplateViewSet,
    AttendanceMonthlyViewSet,
    AttendanceRecordViewSet,
    CompositeRankingView,
    DailyAttendanceRankingView,
    FeedbackRecordViewSet,
    FiveForceScoreViewSet,
    MonthlyAssessmentViewSet,
    MonthlyReportViewSet,
    ProbationViewSet,
    StatsOverviewView,
    TeacherRankingView,
)

router = DefaultRouter()
router.register(
    r'monthly-assessments', MonthlyAssessmentViewSet,
    basename='campus-monthly-assessment',
)
router.register(
    r'assessment-templates', AssessmentTemplateViewSet,
    basename='campus-assessment-template',
)
router.register(
    r'five-forces', FiveForceScoreViewSet,
    basename='campus-five-force-score',
)
router.register(
    r'attendance-records', AttendanceRecordViewSet,
    basename='campus-attendance-record',
)
router.register(
    r'attendance-monthly', AttendanceMonthlyViewSet,
    basename='campus-attendance-monthly',
)
router.register(
    r'feedback-records', FeedbackRecordViewSet,
    basename='campus-feedback-record',
)
router.register(
    r'monthly-reports', MonthlyReportViewSet,
    basename='campus-monthly-report',
)
router.register(
    r'probations', ProbationViewSet,
    basename='campus-probation',
)

# ⚠️ 自定义路径必须排在 **router.urls 之前**：
#    DRF router 会生成 `attendance-records/(?P<pk>[^/.]+)/` 的详情路由，而 pk 的正则
#    `[^/.]+` **能匹配 "daily-ranking"** —— 一旦 router.urls 在前，这个自定义端点会被
#    详情路由抢先命中 → 404（"No AttendanceRecord matches the query"）。
#    同一个坑在 apps/campus_rotation/urls.py 的 `resources/bu-summary/` 已经踩过。
#    → 约定：自定义子路径一律放在 router.urls 之前。
urlpatterns = [
    path(
        'attendance-records/daily-ranking/',
        DailyAttendanceRankingView.as_view(),
        name='campus-attendance-daily-ranking',
    ),
    path(
        'ranking/composite/',
        CompositeRankingView.as_view(),
        name='campus-ranking-composite',
    ),
    path(
        'ranking/teacher/',
        TeacherRankingView.as_view(),
        name='campus-ranking-teacher',
    ),
    path(
        'stats/overview/',
        StatsOverviewView.as_view(),
        name='campus-stats-overview',
    ),
] + router.urls
