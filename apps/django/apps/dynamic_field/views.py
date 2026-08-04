from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import DynamicField
from .serializers import DynamicFieldSerializer


class DynamicFieldViewSet(viewsets.ModelViewSet):
    """动态字段定义 CRUD — 按 resource 过滤"""
    serializer_class = DynamicFieldSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DynamicField.objects.filter(deleted_at__isnull=True)

    def list(self, request, *args, **kwargs):
        """GET /dynamic-fields/<resource>/fields/ — 返回指定 resource 的字段列表"""
        resource = self.kwargs.get('resource')
        queryset = self.get_queryset().filter(resource=resource).order_by('order_index')
        serializer = self.get_serializer(queryset, many=True)
        return Response({'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        """GET /dynamic-fields/<resource>/fields/<key>/ — 按 field_key 查"""
        resource = self.kwargs.get('resource')
        key = self.kwargs.get('pk')
        obj = self.get_queryset().get(resource=resource, field_key=key)
        serializer = self.get_serializer(obj)
        return Response({'data': serializer.data})

    def perform_create(self, serializer):
        resource = self.kwargs.get('resource')
        serializer.save(resource=resource)

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=False, methods=['post'])
    def reorder(self, request, resource=None):
        """POST /dynamic-fields/<resource>/fields/reorder/ — 重新排序"""
        ordered_ids = request.data.get('orderedIds', [])
        for idx, fid in enumerate(ordered_ids):
            DynamicField.objects.filter(id=fid, resource=resource).update(order_index=idx)
        return Response({'success': True})
