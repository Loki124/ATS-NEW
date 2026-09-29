"""码表库 (G46) 视图。

只读端点（码表数据由 import_code_tables 命令导入，不提供增删改）：
- GET /api/v1/code-tables/regions/     行政区划（支持 level / parent_code / keyword 过滤）
- GET /api/v1/code-tables/countries/   国家与地区
- GET /api/v1/code-tables/ethnicities/ 民族
- GET /api/v1/code-tables/languages/   语言
- GET /api/v1/code-tables/currencies/  币种（ISO 4217）
- GET /api/v1/code-tables/industries/  行业（GB/T 4754，支持 level / parent_code / keyword 过滤）

响应统一信封 {data: [...], pagination: {total}}，与项目列表约定一致。
镇乡级约 4.2 万条，故默认分页，避免一次性拉爆前端。
"""
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from apps.common.response import success_response
from apps.core.permissions_v2 import V2Permission

from .models import Country, Currency, Ethnicity, Industry, Language, Region
from .serializers import (
    CountrySerializer,
    CurrencySerializer,
    EthnicitySerializer,
    IndustrySerializer,
    LanguageSerializer,
    RegionSerializer,
)


class CodeTablePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


def _paged_response(paginator: CodeTablePagination, queryset, request, serializer_cls):
    """分页并返回统一信封（补齐 success 字段，与全局约定对齐；FE 只读 data/pagination，success 为增量）。"""
    page = paginator.paginate_queryset(queryset, request, view=None)
    if page is not None:
        return success_response(
            serializer_cls(page, many=True).data,
            pagination={'total': paginator.page.paginator.count},
        )
    return success_response(
        serializer_cls(queryset, many=True).data,
        pagination={'total': queryset.count()},
    )


class _BaseCodeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [V2Permission]
    pagination_class = CodeTablePagination

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        return _paged_response(self.pagination_class(), qs, request, self.get_serializer_class())

    def filter_queryset(self, queryset):
        return self.apply_filters(queryset)

    def apply_filters(self, queryset):
        return queryset


class RegionViewSet(_BaseCodeViewSet):
    """行政区划：按 level / parent_code / keyword 过滤，支持级联查询。"""

    queryset = Region.objects.all()
    serializer_class = RegionSerializer

    def apply_filters(self, queryset):
        params = self.request.query_params
        level = params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        parent = params.get('parent_code')
        if parent:
            queryset = queryset.filter(parent_code=parent)
        keyword = params.get('keyword')
        if keyword:
            queryset = queryset.filter(name__icontains=keyword) | queryset.filter(code__icontains=keyword)
        return queryset


class CountryViewSet(_BaseCodeViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer

    def apply_filters(self, queryset):
        keyword = self.request.query_params.get('keyword')
        if keyword:
            queryset = (
                queryset.filter(name_cn__icontains=keyword)
                | queryset.filter(name_en__icontains=keyword)
                | queryset.filter(phone_code__icontains=keyword)
            )
        return queryset


class EthnicityViewSet(_BaseCodeViewSet):
    queryset = Ethnicity.objects.all()
    serializer_class = EthnicitySerializer

    def apply_filters(self, queryset):
        keyword = self.request.query_params.get('keyword')
        if keyword:
            queryset = queryset.filter(name__icontains=keyword) | queryset.filter(code__icontains=keyword)
        return queryset


class LanguageViewSet(_BaseCodeViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer

    def apply_filters(self, queryset):
        keyword = self.request.query_params.get('keyword')
        if keyword:
            queryset = (
                queryset.filter(name_cn__icontains=keyword)
                | queryset.filter(name_en__icontains=keyword)
                | queryset.filter(code__icontains=keyword)
            )
        return queryset


class CurrencyViewSet(_BaseCodeViewSet):
    """币种（ISO 4217）：支持 keyword 过滤（中文名 / 英文名 / 代码）。"""

    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer

    def apply_filters(self, queryset):
        keyword = self.request.query_params.get('keyword')
        if keyword:
            queryset = (
                queryset.filter(name_cn__icontains=keyword)
                | queryset.filter(name_en__icontains=keyword)
                | queryset.filter(code__icontains=keyword)
                | queryset.filter(symbol__icontains=keyword)
            )
        return queryset


class IndustryViewSet(_BaseCodeViewSet):
    """行业（GB/T 4754）：支持 level / parent_code / keyword 过滤，支持树形级联查询。"""

    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer

    def apply_filters(self, queryset):
        params = self.request.query_params
        level = params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        parent = params.get('parent_code')
        if parent:
            queryset = queryset.filter(parent_code=parent)
        keyword = params.get('keyword')
        if keyword:
            queryset = queryset.filter(name__icontains=keyword) | queryset.filter(code__icontains=keyword)
        return queryset
