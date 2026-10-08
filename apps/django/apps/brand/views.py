"""品牌信息管理 (G43) 视图。

单例配置端点 ``/api/v1/brand/``:
  - GET   返回当前品牌信息(不存在则惰性创建默认一条)
  - PUT   全量更新
  - PATCH 部分更新

Logo 上传端点 ``/api/v1/brand/logo/``:
  - POST  multipart/form-data, 接收 file, 落 media/brand/logos/, 返回可访问 URL

所有响应统一包裹为 ``{'data': ...}``, 与前端 ``external-sync.ts`` /
``dynamic-field.ts`` 的 ``.then(r => r.data.data)`` 消费方式对齐。
"""
import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.response import success_response

from .models import BrandInfo
from .serializers import BrandInfoSerializer

# Logo 仅允许图片类型, 单文件上限 2MB
# 2026-10-08 (#17 / S-07): 移除 .svg —— SVG 是 XML, 可内嵌 <script> 成为持久型 XSS
#   存储/分发点, 且魔数校验拦不住 (SVG 无稳定二进制头)。只允许位图 + WebP。
ALLOWED_LOGO_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
MAX_LOGO_SIZE = 2 * 1024 * 1024


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
        return success_response(BrandInfoSerializer(obj).data)

    def _update(self, request, *, partial: bool) -> Response:
        obj = self._get_or_create()
        serializer = BrandInfoSerializer(obj, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data)

    def put(self, request, *args, **kwargs) -> Response:
        return self._update(request, partial=False)

    def patch(self, request, *args, **kwargs) -> Response:
        return self._update(request, partial=True)


class BrandLogoUploadView(APIView):
    """POST /api/v1/brand/logo/ — 上传品牌 Logo 图片, 返回可访问 URL。

    复用 ``default_storage`` 落盘到 ``media/brand/logos/``, 由 dev(DEBUG) 的
    ``static(MEDIA_URL)`` 或生产 web 服务器提供访问。前端拿到 URL 后写入
    ``BrandInfo.logo_url`` 字段(PUT /api/v1/brand/)。
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs) -> Response:
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'detail': '未收到文件', 'code': 'NO_FILE'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_LOGO_EXT:
            return Response(
                {
                    'detail': f'不支持的图片类型「{ext or "未知"}」, 仅允许 PNG/JPG/WebP/GIF',
                    'code': 'UNSUPPORTED_TYPE',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if getattr(file, 'size', 0) <= 0:
            return Response(
                {'detail': '文件内容为空', 'code': 'EMPTY_FILE'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file.size > MAX_LOGO_SIZE:
            return Response(
                {
                    'detail': f'文件大小 {file.size // 1024}KB 超过 {MAX_LOGO_SIZE // 1024}KB 上限',
                    'code': 'FILE_TOO_LARGE',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # 2026-10-08 (#17): 魔数校验, 防伪造扩展名上传 (.gif 伪装成 .png 等)
        try:
            from apps.common.storage import check_magic_bytes
            check_magic_bytes(ext, file)
        except ValueError as e:
            return Response(
                {'detail': str(e), 'code': 'BAD_MAGIC'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rel_path = f'brand/logos/{uuid.uuid4().hex}{ext}'
        saved = default_storage.save(rel_path, file)
        # 与 announcement 附件一致: 返回 MEDIA_URL + 相对路径 的可访问 URL
        url = settings.MEDIA_URL + saved
        return success_response({'url': url}, status_code=status.HTTP_201_CREATED)
