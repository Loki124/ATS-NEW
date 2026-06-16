"""自定义过滤器"""
from django_filters import rest_framework as filters


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """支持 ?field=a,b,c 多值查询"""
    pass


class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    """支持 ?field=1,2,3 多值查询"""
    pass
