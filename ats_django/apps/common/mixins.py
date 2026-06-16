"""通用 ViewSet Mixins"""
from rest_framework import status
from rest_framework.response import Response


class BulkCreateMixin:
    """批量创建 Mixin"""
    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_bulk_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def perform_bulk_create(self, serializer):
        serializer.save()


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
