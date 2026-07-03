"""通用 ViewSet Mixins"""
import logging

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class BulkCreateMixin:
    """批量创建 Mixin

    2026-07-02: 每行独立事务, 失败不阻塞其它行, 返回 207 多状态响应。
    之前一行失败全 roll back, 客户端拿不到哪条出错。
    """
    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            results = self.perform_bulk_create(serializer)
            return Response(results, status=status.HTTP_207_MULTI_STATUS)
        return super().create(request, *args, **kwargs)

    def perform_bulk_create(self, serializer):
        results = []
        for item in serializer.validated_data:
            try:
                with transaction.atomic():
                    instance = serializer.child.create(item)
                    results.append({
                        'success': True,
                        'data': serializer.child.to_representation(instance),
                    })
            except IntegrityError as e:
                logger.warning('Bulk create integrity error: %s', e)
                results.append({
                    'success': False,
                    'error': 'INTEGRITY_ERROR',
                    'detail': str(e),
                })
            except Exception as e:
                logger.exception('Bulk create row failed: %s', e)
                results.append({
                    'success': False,
                    'error': 'CREATE_FAILED',
                    'detail': str(e),
                })
        return results


class SoftDeleteViewSetMixin:
    """软删除 ViewSet Mixin"""
    def perform_destroy(self, instance):
        instance.soft_delete()


class AuditMixin:
    """审计 Mixin - 自动记录创建人/修改人"""
    def perform_create(self, serializer):
        request_user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=request_user, updated_by=request_user)

    def perform_update(self, serializer):
        request_user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(updated_by=request_user)
