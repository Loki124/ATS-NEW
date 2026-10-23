"""campus_assessment 后台管理（轻量，便于运营核对与补录）。"""
from django.contrib import admin

from .models import (
    AssessmentTemplate,
    AssessmentTemplateItem,
    AttendanceMonthly,
    AttendanceRecord,
    FeedbackRecord,
    FiveForceScore,
    MonthlyAssessment,
    MonthlyReport,
    MonthlyReportScore,
    Probation,
)


@admin.register(AssessmentTemplate)
class AssessmentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'scope_type', 'stage', 'period_type', 'enabled')
    list_filter = ('scope_type', 'stage', 'period_type', 'enabled')
    search_fields = ('name',)


@admin.register(AssessmentTemplateItem)
class AssessmentTemplateItemAdmin(admin.ModelAdmin):
    list_display = ('template', 'name', 'weight', 'target')
    list_filter = ('template',)
    search_fields = ('name',)


@admin.register(MonthlyAssessment)
class MonthlyAssessmentAdmin(admin.ModelAdmin):
    list_display = ('person', 'ym', 'kpi', 'exam', 'adjust', 'status')
    list_filter = ('status', 'ym')
    search_fields = ('person__name',)


@admin.register(FiveForceScore)
class FiveForceScoreAdmin(admin.ModelAdmin):
    list_display = ('person', 'learning', 'execution', 'collaboration', 'innovation',
                    'resilience', 'scored_at')
    list_filter = ('scored_at',)
    search_fields = ('person__name',)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('person', 'date', 'punch_time', 'status')
    list_filter = ('status', 'date')
    search_fields = ('person__name',)


@admin.register(AttendanceMonthly)
class AttendanceMonthlyAdmin(admin.ModelAdmin):
    list_display = ('person', 'ym', 'attend_days', 'late_count', 'leave_days', 'status')
    list_filter = ('status', 'ym')
    search_fields = ('person__name',)


@admin.register(FeedbackRecord)
class FeedbackRecordAdmin(admin.ModelAdmin):
    list_display = ('person', 'date', 'category', 'type', 'status', 'handler')
    list_filter = ('category', 'status')
    search_fields = ('person__name', 'content')


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = ('person', 'ym', 'status', 'business_score', 'growth_score', 'final_score')
    list_filter = ('status', 'ym')
    search_fields = ('person__name',)


@admin.register(MonthlyReportScore)
class MonthlyReportScoreAdmin(admin.ModelAdmin):
    list_display = ('report', 'role', 'case', 'insight', 'problem', 'clarity',
                    'executable', 'total', 'scorer')
    list_filter = ('role',)
    search_fields = ('report__person__name',)


@admin.register(Probation)
class ProbationAdmin(admin.ModelAdmin):
    list_display = ('person', 'rotation_result', 'rotation_level', 'p3m_kpi',
                    'p3m_competency', 'decision', 'decided_by')
    list_filter = ('decision',)
    search_fields = ('person__name',)
