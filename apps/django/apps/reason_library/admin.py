"""Reason Library Django Admin."""
from django.contrib import admin

from .models import (
    CategoryAssignment,
    ReasonTag,
    RuleCategory,
    RuleSceneAssignment,
    SceneRule,
)


@admin.register(ReasonTag)
class ReasonTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'en_name', 'type', 'enabled', 'created_at', 'deleted_at')
    list_filter = ('type', 'enabled', 'deleted_at')
    search_fields = ('name', 'en_name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(SceneRule)
class SceneRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_system', 'enabled', 'created_at')
    list_filter = ('is_system', 'enabled')
    search_fields = ('name', 'description')


@admin.register(RuleCategory)
class RuleCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'rule', 'parent', 'level', 'order', 'allow_custom')
    list_filter = ('rule', 'level', 'allow_custom')
    search_fields = ('name',)


@admin.register(CategoryAssignment)
class CategoryAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'tag', 'order')
    list_filter = ('category__rule',)
    search_fields = ('tag__name',)


@admin.register(RuleSceneAssignment)
class RuleSceneAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'rule', 'scene')
    list_filter = ('rule',)
