from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.views import EnvelopeWriteMixin
from apps.common.response import success_response
from apps.core.permissions_v2 import V2Permission

from django.db.models import Q

from .models import School, Company, Major
from .serializers import SchoolSerializer, CompanySerializer, MajorSerializer


class MajorViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    """专业库 — 院校库「专业」Tab。

    支持 keyword（专业名/代码）、discipline（门类）、category（专业类）、
    educationLevel（学历层次）过滤；facets 返回门类/专业类/学历层次可选项。

    人工编辑过的记录置 ``is_customized=True``，``import_majors`` 默认跳过。
    """

    queryset = Major.objects.all()
    serializer_class = MajorSerializer
    permission_classes = [V2Permission]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        keyword = request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(Q(name__icontains=keyword) | Q(code__icontains=keyword))
        discipline = request.query_params.get('discipline')
        if discipline:
            qs = qs.filter(discipline=discipline)
        category = request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        edu = request.query_params.get('educationLevel')
        if edu:
            qs = qs.filter(education_level=edu)
        serializer = self.get_serializer(qs, many=True)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def facets(self, request):
        """返回门类 / 专业类 / 学历层次的可选值（供前端下拉筛选用）。"""
        return Response({
            'success': True,
            'data': {
                'disciplines': [
                    d for d in Major.objects.values_list('discipline', flat=True).distinct() if d
                ],
                'categories': [
                    c for c in Major.objects.values_list('category', flat=True).distinct() if c
                ],
                'educationLevels': [
                    e for e in Major.objects.values_list('education_level', flat=True).distinct() if e
                ],
            },
        })

    def perform_create(self, serializer):
        serializer.save(is_customized=True)

    def perform_update(self, serializer):
        serializer.save(is_customized=True)

    def destroy(self, request, *args, **kwargs):
        """软删除：专业是基础数据，不做物理删除。"""
        obj = self.get_object()
        obj.soft_delete()
        return success_response({'id': obj.id})


class SchoolViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    """院校库 — 以只读查询为主，同时支持人工维护（新建 / 编辑 / 软删）。

    过滤参数：keyword（名称/代码/地址/曾用名）、educationLevel、schoolType、
    schoolCategory（公办/民办）、province、tag（校准标签 contains）。

    人工在页面上编辑过的记录会置 ``is_customized=True``，``import_schools``
    默认跳过这些记录，避免下次导入把人工修改覆盖掉（可用 --force 强制覆盖）。
    """

    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
    pagination_class = None  # FE 用 n-data-table 客户端分页

    def list(self, request, *args, **kwargs):
        """FE library.ts 期望 {success, data:[...]} 信封 (非 DRF 裸数组), 否则 rows 变 undefined 崩溃."""
        qs = self.get_queryset()
        keyword = request.query_params.get('keyword')
        if keyword:
            # 曾用名也要能被搜到：候选人简历上写的往往是更名前的校名
            qs = qs.filter(
                Q(name__icontains=keyword)
                | Q(code__icontains=keyword)
                | Q(location__icontains=keyword)
                | Q(former_names__icontains=keyword)
            )
        edu = request.query_params.get('educationLevel')
        if edu:
            qs = qs.filter(education_level=edu)
        stype = request.query_params.get('schoolType')
        if stype:
            qs = qs.filter(school_type=stype)
        category = request.query_params.get('schoolCategory')
        if category:
            qs = qs.filter(school_category=category)
        province = request.query_params.get('province')
        if province:
            qs = qs.filter(province=province)
        tag = request.query_params.get('tag')
        if tag:
            qs = qs.filter(tags__contains=tag)
        serializer = self.get_serializer(qs, many=True)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def provinces(self, request):
        """返所有不重复省份"""
        qs = School.objects.values_list('province', flat=True).distinct()
        return Response({'success': True, 'data': [p for p in qs if p]})

    @action(detail=False, methods=['get'])
    def facets(self, request):
        """返回院校类型 / 办学性质 / 教育层次 / 省份 / 标签 的可选值（供前端下拉筛选用）。

        标签在库里是 '|' 分隔字符串，这里展开成去重后的单值列表。
        """
        tag_set: set[str] = set()
        for raw in School.objects.exclude(tags='').values_list('tags', flat=True):
            tag_set.update(t for t in raw.split('|') if t)
        return Response({
            'success': True,
            'data': {
                'schoolTypes': self._distinct('school_type'),
                'schoolCategories': self._distinct('school_category'),
                'educationLevels': self._distinct('education_level'),
                'provinces': self._distinct('province'),
                'tags': sorted(tag_set),
            },
        })

    @staticmethod
    def _distinct(field: str) -> 'list[str]':
        return [v for v in School.objects.values_list(field, flat=True).distinct() if v]

    def perform_create(self, serializer):
        serializer.save(is_customized=True)

    def perform_update(self, serializer):
        serializer.save(is_customized=True)

    def destroy(self, request, *args, **kwargs):
        """软删除：院校是基础数据，不做物理删除（保留历史引用）。"""
        obj = self.get_object()
        obj.soft_delete()
        return success_response({'id': obj.id})


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    """公司 - 2026-06-29 stub"""
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    # T01.2 (2026-08-04 寇豆码): 由裸 IsAuthenticated 改为 V2Permission, 显式声明避免 deny-by-default.
    permission_classes = [V2Permission]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        """FE library.ts 期望 {success, data:[...]} 信封; 承接 keyword/industry/scale 过滤."""
        qs = self.get_queryset()
        keyword = request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(name__icontains=keyword) | qs.filter(code__icontains=keyword)
        industry = request.query_params.get('industry')
        if industry:
            qs = qs.filter(industry=industry)
        scale = request.query_params.get('scale')
        if scale:
            qs = qs.filter(scale=scale)
        serializer = self.get_serializer(qs, many=True)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def industries(self, request):
        qs = Company.objects.values_list('industry', flat=True).distinct()
        return Response({'success': True, 'data': [i for i in qs if i]})
