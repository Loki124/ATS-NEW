"""公共端点 (2026-09-16, 兵哥: 动态字段附件 / 组合字段图片通用上传)。"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from apps.common.storage import save_upload


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
