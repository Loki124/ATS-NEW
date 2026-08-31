"""统一规则引擎 admin 注册（Phase 0）。"""
from django.contrib import admin

from .models import Action, Condition, Rule, RuleExecutionLog


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'source_app', 'trigger_type',
                   'priority', 'status', 'enabled', 'created_at')
    list_filter = ('category', 'trigger_type', 'priority', 'status', 'enabled')
    search_fields = ('name', 'source_app')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('id', 'rule', 'seq', 'condition_type', 'field', 'operator')
    list_filter = ('condition_type', 'operator')
    search_fields = ('field',)


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'rule', 'seq', 'action_type', 'enabled')
    list_filter = ('action_type', 'enabled')


@admin.register(RuleExecutionLog)
class RuleExecutionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'rule', 'rule_category', 'trigger_type',
                   'evaluate_result', 'execution_ms', 'triggered_at')
    list_filter = ('rule_category', 'trigger_type', 'evaluate_result')
