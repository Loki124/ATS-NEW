"""公共端点 (2026-09-16, 兵哥: 动态字段附件 / 组合字段图片通用上传)。"""
import os

from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.response import success_response
from apps.common.storage import save_upload


class EnvelopeWriteMixin:
    """写操作 + retrieve 统一包 {success, data} 信封（DRF 默认直接返 serializer.data，会让前端拿到 undefined）。

    与 library.views.EnvelopeWriteMixin 行为一致，集中到 common 供各 app 复用（library 已改从此导入）。
    destroy 各模型语义不同（软删 / 硬删），由各 ViewSet 自行信封化，不在此统一。
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(serializer.data, status_code=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)


class EnvelopeReadOnlyMixin:
    """只读 ViewSet 仅需给 retrieve 包信封（list 已由 StandardResultsSetPagination 包 success）。"""

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)


class MediaUploadView(APIView):
    """POST /api/v1/media/upload/ — 通用文件上传, 返回 {id,name,url,size,content_type}。

    鉴权要求: 登录用户。请求体 multipart, 字段名 ``file``。
    存储后端: settings.STORAGE_PROVIDER (local / cos); 校验失败返回 400。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'success': False, 'message': '未收到文件'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = save_upload(file)
        except ValueError as e:
            return Response(
                {'success': False, 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'success': True, 'data': data}, status=status.HTTP_201_CREATED)


class MediaDownloadView(APIView):
    """GET /api/v1/media/secure/<path:path>/ — 经鉴权的文件下载 (2026-10-08 #17)。

    替代直接暴露 ``MEDIA_URL`` 静态服务: 任意已登录用户可下载 (上传场景多为
    内部 HR 互传附件); 生产应关闭 ``MEDIA_URL`` 静态路由, 统一走此端点。
    ``path`` 为 ``save_upload`` 返回的文件 id (相对路径), 防目录穿越。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, path: str):
        if not path or '..' in path or path.startswith('/') or path.startswith('\\'):
            return Response(
                {'success': False, 'message': '非法路径'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_storage.exists(path):
            return Response(
                {'success': False, 'message': '文件不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            fh = default_storage.open(path)
        except Exception:  # noqa: BLE001 - 兜底, 不泄露底层错误
            return Response(
                {'success': False, 'message': '文件无法打开'},
                status=status.HTTP_404_NOT_FOUND,
            )
        from django.http import FileResponse
        resp = FileResponse(fh, content_type='application/octet-stream')
        resp['Content-Disposition'] = f'attachment; filename="{os.path.basename(path)}"'
        return resp
