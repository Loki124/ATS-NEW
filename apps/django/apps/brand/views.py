"""品牌信息管理 (G43) 视图。

单例配置端点 ``/api/v1/brand/``:
  - GET   返回当前品牌信息(不存在则惰性创建默认一条)
  - PUT   全量更新
  - PATCH 部分更新

所有响应统一包裹为 ``{'data': ...}``, 与前端 ``external-sync.ts`` /
``dynamic-field.ts`` 的 ``.then(r => r.data.data)`` 消费方式对齐。
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BrandInfo
from .serializers import BrandInfoSerializer


class BrandInfoView(APIView):
    """雇主品牌信息 单例 CRUD 视图。"""

    permission_classes = [IsAuthenticated]

    def _get_or_create(self) -> BrandInfo:
        """取唯一一行; 不存在则惰性创建(首次访问即给一份默认值)。"""
        obj = BrandInfo.objects.first()
        if obj is None:
            obj = BrandInfo.objects.create()
        return obj

    def get(self, request, *args, **kwargs) -> Response:
        obj = self._get_or_create()
        return Response({'data': BrandInfoSerializer(obj).data})

    def _update(self, request, *, partial: bool) -> Response:
        obj = self._get_or_create()
        serializer = BrandInfoSerializer(obj, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'data': serializer.data})

    def put(self, request, *args, **kwargs) -> Response:
        return self._update(request, partial=False)

    def patch(self, request, *args, **kwargs) -> Response:
        return self._update(request, partial=True)
