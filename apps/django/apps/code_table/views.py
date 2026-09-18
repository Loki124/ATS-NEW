"""码表库 (G46) 视图。

只读端点（码表数据由 import_code_tables 命令导入，不提供增删改）：
- GET /api/v1/code-tables/regions/     行政区划（支持 level / parent_code / keyword 过滤）
- GET /api/v1/code-tables/countries/   国家与地区
- GET /api/v1/code-tables/ethnicities/ 民族
- GET /api/v1/code-tables/languages/   语言

响应统一信封 {data: [...], pagination: {total}}，与项目列表约定一致。
镇乡级约 4.2 万条，故默认分页，避免一次性拉爆前端。
"""
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Q

from apps.core.permissions_v2 import V2Permission

from .models import Country, Ethnicity, Language, Region, BusinessCode
from .serializers import (
    CountrySerializer,
    EthnicitySerializer,
    LanguageSerializer,
    RegionSerializer,
    BusinessCodeSerializer,
)


class EnvelopeWriteMixin:
    """写操作统一包 ``{success, data}`` 信封（与 library.views.EnvelopeWriteMixin 同义）。

    本项目所有 read 接口手工包信封，前端一律读 ``r.data.data``；DRF 默认的
    create/update 直接返回序列化结果不包信封会导致前端拿到 undefined，故补上。
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'success': True, 'data': serializer.data}, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'success': True, 'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        return Response({'success': True, 'data': self.get_serializer(self.get_object()).data})


class CodeTablePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


def _paged_response(paginator: CodeTablePagination, queryset, request, serializer_cls) -> Response:
    """分页并返回统一信封。"""
    page = paginator.paginate_queryset(queryset, request, view=None)
    if page is not None:
        return Response({
            'data': serializer_cls(page, many=True).data,
            'pagination': {'total': paginator.page.paginator.count},
        })
    return Response({
        'data': serializer_cls(queryset, many=True).data,
        'pagination': {'total': queryset.count()},
    })


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


class BusinessCodeViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    """业务码表（自定义枚举）—— 标准码表保持只读，本视图提供完整增改删。

    - list 支持 ``?category=``（枚举类别）与 ``?keyword=``（名称/编码）过滤，返回
      ``{success, data}`` 信封（与院校库/专业库一致，前端统一读 ``r.data.data``）。
    - 新建/编辑经 ``perform_create/update`` 置 ``is_customized=True``（用户自建标记）。
    - 删除走软删（保留历史引用），非物理删除。
    """

    queryset = BusinessCode.objects.all()
    serializer_class = BusinessCodeSerializer
    permission_classes = [V2Permission]
    pagination_class = None

    def get_queryset(self):
        qs = BusinessCode.objects.all()
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        keyword = self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(Q(name__icontains=keyword) | Q(code__icontains=keyword))
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset()).order_by('category', 'sort_order', 'code')
        serializer = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})

    def perform_create(self, serializer):
        serializer.save(is_customized=True)

    def perform_update(self, serializer):
        serializer.save(is_customized=True)

    def destroy(self, request, *args, **kwargs):
        """软删除：枚举值可能被候选人/职位数据引用，物理删除会断引用。"""
        obj = self.get_object()
        obj.soft_delete()
        return Response({'success': True, 'data': {'id': obj.id}})
