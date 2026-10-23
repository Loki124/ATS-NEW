"""校招学习与社区路由（挂在 /api/v1/campus-learning/ 下）。

端点（契约 §3.2）：
  GET/POST   /courses/                    课程列表 / 新建
  GET/PUT/DELETE /courses/{id}/           详情 / 改 / 软删
  POST       /courses/{id}/restore/       恢复软删

  GET/POST   /learn-progress/             学习进度列表 / 新建（?person=&course=）
  POST       /learn-progress/{id}/record/ 记学习记录（写 LearnRecord + 累加进度/分钟）

  GET/POST   /learn-records/              学习记录流水
  GET/POST   /exams/                     考试
  GET        /exams/{id}/ranking/         考试排名（分数降序 + 通过判定 + 得分条）
  GET/POST   /exam-scores/               考试成绩（passed 服务端回算）
  GET/POST   /activities/                活动
  GET/POST   /activity-scores/           活动评分（reward 文本 → reward_points）
  GET/POST   /forum-boards/              论坛板块
  GET/POST   /forum-posts/               论坛帖（?board=&kw=）
  GET        /stats/learn-board/         学习龙虎榜

⚠️ 自定义路径必须排在 **router.urls 之前**：
    DRF router 会生成 `exams/(?P<pk>[^/.]+)/` 的详情路由，而 pk 的正则
    `[^/.]+` **能匹配 "stats" / "learn-board"** —— 一旦 router.urls 在前，
    `stats/learn-board/` 这类自定义端点会被详情路由抢先命中 → 404
    （症状极具迷惑性：前端 try/catch 兜底到示例数据，页面看着正常，
    但真实数据**从来没取到过**）。
    约定：自定义子路径一律放在 router.urls 之前（同 apps/campus_rotation/urls.py）。
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityScoreViewSet,
    ActivityViewSet,
    CourseViewSet,
    ExamScoreViewSet,
    ExamViewSet,
    ForumBoardViewSet,
    ForumPostViewSet,
    LearnBoardStatsView,
    LearnProgressViewSet,
    LearnRecordViewSet,
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='campus-learning-course')
router.register(r'learn-progress', LearnProgressViewSet, basename='campus-learning-learn-progress')
router.register(r'learn-records', LearnRecordViewSet, basename='campus-learning-learn-record')
router.register(r'exams', ExamViewSet, basename='campus-learning-exam')
router.register(r'exam-scores', ExamScoreViewSet, basename='campus-learning-exam-score')
router.register(r'activities', ActivityViewSet, basename='campus-learning-activity')
router.register(r'activity-scores', ActivityScoreViewSet, basename='campus-learning-activity-score')
router.register(r'forum-boards', ForumBoardViewSet, basename='campus-learning-forum-board')
router.register(r'forum-posts', ForumPostViewSet, basename='campus-learning-forum-post')

urlpatterns = [
    # 学习龙虎榜（契约 §3.2）—— 必须排在 router.urls 之前，理由见模块 docstring
    path('stats/learn-board/', LearnBoardStatsView.as_view(), name='campus-learning-learn-board'),
] + router.urls
