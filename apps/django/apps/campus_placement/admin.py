"""校招定岗与结算域 Admin 注册（便于后台核对撮合状态与结算台账）。"""
from django.contrib import admin

from .models import (
    Bill,
    PlacementAssessment,
    PlacementGoal,
    PlacementMetric,
    PlacementRecord,
    PositionApplication,
    PositionDemand,
    PriceBid,
    PriceScheme,
    RevenueRecord,
    SelectionFlow,
)


@admin.register(PositionDemand)
class PositionDemandAdmin(admin.ModelAdmin):
    list_display = ['name', 'dept', 'business_dept', 'headcount', 'need_status', 'open_enabled']
    list_filter = ['need_status', 'scope_type', 'open_enabled']
    search_fields = ['name', 'dept', 'business_dept']


@admin.register(PositionApplication)
class PositionApplicationAdmin(admin.ModelAdmin):
    list_display = ['person', 'position', 'order', 'channel', 'status', 'pushed_at', 'decided_at']
    list_filter = ['status', 'channel']
    search_fields = ['person__name', 'person__code', 'position__name']


@admin.register(SelectionFlow)
class SelectionFlowAdmin(admin.ModelAdmin):
    list_display = ['batch', 'started', 'start_time', 'wish_limit', 'published', 'published_at']
    list_filter = ['started', 'published']


@admin.register(PlacementRecord)
class PlacementRecordAdmin(admin.ModelAdmin):
    list_display = ['person', 'dept', 'position_name', 'place_date', 'track_years', 'status']
    list_filter = ['status', 'dept']
    search_fields = ['person__name', 'position_name']


admin.site.register(PlacementGoal)
admin.site.register(PlacementMetric)
admin.site.register(PlacementAssessment)
admin.site.register(PriceScheme)
admin.site.register(PriceBid)
admin.site.register(RevenueRecord)
admin.site.register(Bill)
