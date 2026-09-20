"""Reason Library filters (T03).

django_filters FilterSet - 列表接口用。
"""
from __future__ import annotations

import django_filters

from .models import ReasonTag, SceneRule


class ReasonTagFilter(django_filters.FilterSet):
    """Tag 列表筛选: type / enabled / 搜索 name+en_name。"""

    type = django_filters.ChoiceFilter(choices=[('system', 'system'), ('custom', 'custom')])
    enabled = django_filters.BooleanFilter()
    search = django_filters.CharFilter(method='filter_search', label='搜索 name/en_name')

    class Meta:
        model = ReasonTag
        fields = ['type', 'enabled']

    def filter_search(self, queryset, name, value: str):
        if not value:
            return queryset
        return queryset.filter(name__icontains=value) | queryset.filter(en_name__icontains=value)


class SceneRuleFilter(django_filters.FilterSet):
    """Rule 列表筛选: search(name) / enabled / is_system。"""

    search = django_filters.CharFilter(field_name='name', lookup_expr='icontains', label='搜索 name')
    enabled = django_filters.BooleanFilter()
    is_system = django_filters.BooleanFilter()

    class Meta:
        model = SceneRule
        fields = ['enabled', 'is_system']
