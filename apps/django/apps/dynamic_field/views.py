from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import Http404

from .models import DynamicField
from .serializers import DynamicFieldSerializer


class DynamicFieldViewSet(viewsets.ModelViewSet):
    """动态字段定义 CRUD — 按 resource 过滤, 按 field_key 寻址"""
    serializer_class = DynamicFieldSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DynamicField.objects.filter(deleted_at__isnull=True)

    def get_object(self):
        queryset = self.get_queryset()
        resource = self.kwargs.get('resource')
        key = self.kwargs.get('pk')
        try:
            return queryset.get(resource=resource, field_key=key)
        except DynamicField.DoesNotExist:
            raise Http404(f"字段 {resource}/{key} 不存在或已删除")

    def list(self, request, *args, **kwargs):
        resource = self.kwargs.get('resource')
        queryset = self.get_queryset().filter(resource=resource).order_by('order_index')
        serializer = self.get_serializer(queryset, many=True)
        return Response({'data': serializer.data})

    def perform_create(self, serializer):
        resource = self.kwargs.get('resource')
        serializer.save(resource=resource)

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request, resource=None):
        """POST /dynamic-fields/<resource>/fields/reorder/"""
        ordered_ids = request.data.get('orderedIds', [])
        for idx, fid in enumerate(ordered_ids):
            DynamicField.objects.filter(id=fid, resource=resource).update(order_index=idx)
        return Response({'success': True})
