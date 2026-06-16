"""统一分页"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """标准分页"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'data': data,
            'pagination': {
                'page': self.page.number,
                'page_size': self.page.paginator.per_page,
                'total': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            }
        })


class LargeResultsSetPagination(PageNumberPagination):
    """大数据集分页（候选人、申请等）"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


class StandardLimitOffsetPagination(LimitOffsetPagination):
    """Limit/Offset 风格分页"""
    default_limit = 20
    max_limit = 200
    limit_query_param = 'limit'
    offset_query_param = 'offset'
