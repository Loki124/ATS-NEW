"""campus_learning 后台管理（轻量，便于运营录入课程 / 考试 / 活动 / 板块）。"""
from django.contrib import admin

from .models import (
    Activity,
    ActivityScore,
    Course,
    Exam,
    ExamScore,
    ForumBoard,
    ForumPost,
    LearnProgress,
    LearnRecord,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'form', 'duration_min', 'category', 'type', 'exam_required', 'enabled')
    list_filter = ('form', 'type', 'exam_required', 'enabled')
    search_fields = ('code', 'name', 'category')


@admin.register(LearnProgress)
class LearnProgressAdmin(admin.ModelAdmin):
    list_display = ('person', 'course', 'progress', 'minutes', 'done_at', 'last_at')
    list_filter = ('course',)
    search_fields = ('person__name', 'course__name')


@admin.register(LearnRecord)
class LearnRecordAdmin(admin.ModelAdmin):
    list_display = ('person', 'course', 'date', 'start', 'minutes')
    list_filter = ('date', 'course')
    search_fields = ('person__name', 'course__name')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'form', 'full_score', 'pass_score', 'course', 'enabled')
    list_filter = ('form', 'enabled')
    search_fields = ('name',)


@admin.register(ExamScore)
class ExamScoreAdmin(admin.ModelAdmin):
    list_display = ('exam', 'person', 'score', 'passed')
    list_filter = ('passed', 'exam')
    search_fields = ('person__name', 'exam__name')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'date', 'status', 'reward', 'enabled')
    list_filter = ('status', 'type', 'enabled')
    search_fields = ('name',)


@admin.register(ActivityScore)
class ActivityScoreAdmin(admin.ModelAdmin):
    list_display = ('activity', 'person', 'score', 'reward', 'rank')
    list_filter = ('activity',)
    search_fields = ('person__name', 'activity__name')


@admin.register(ForumBoard)
class ForumBoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'sort', 'enabled')
    list_filter = ('enabled',)
    search_fields = ('name',)


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'board', 'author', 'reply_count', 'pinned', 'created_at')
    list_filter = ('board', 'pinned')
    search_fields = ('title', 'content')
