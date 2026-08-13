"""制度公告视图 — 招聘专家查看 / HR 及以上维护。"""
import os
from uuid import uuid4

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import AuditMixin, SoftDeleteViewSetMixin
from apps.core.role_v2_query import HR_TIER, user_has_any_role

from .models import Announcement, AnnouncementAttachment, AnnouncementConfig
from .serializers import (
    AnnouncementSerializer,
    AnnouncementWriteSerializer,
    AnnouncementAttachmentSerializer,
    AnnouncementConfigSerializer,
)

ALLOWED_EXT = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.png', '.jpg', '.jpeg', '.gif', '.zip',
}
MAX_UPLOAD = 10 * 1024 * 1024  # 10MB


class IsHRAbove(BasePermission):
    """HR 及以上（SUPER_ADMIN / HRBP / HR）可维护制度公告。"""

    def has_permission(self, request, view):
        return user_has_any_role(request.user, HR_TIER)


class AnnouncementViewSet(SoftDeleteViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    """制度公告 ViewSet。

    - 读（list/retrieve）：登录即可（招聘专家在 dashboard 查看）。
    - 写（create/update/partial_update/destroy）：需 HR 及以上。
    - 列表默认仅返回上架(is_active=True)；管理页传 ``show_inactive=true`` 含下架项。
    - 软删除（与 FullAuditModel 约定一致）。
    """

    queryset = Announcement.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = None  # dashboard / 管理页均自行控制条数，不走分页信封

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsHRAbove()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AnnouncementWriteSerializer
        return AnnouncementSerializer

    def get_queryset(self):
        qs = Announcement.objects.all().filter(deleted_at__isnull=True).prefetch_related('attachments')
        # 管理后台传 show_inactive=true 时连下架项一并展示（供重新上架）。
        if not self.request.query_params.get('show_inactive'):
            qs = qs.filter(is_active=True)
        return qs

    def list(self, request, *args, **kwargs):
        """覆盖 list 以返回 {success, data} 信封（与其它端点一致）。"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})

    # ===== 模块级配置：工作台展示开关 =====
    @action(detail=False, methods=['get', 'put'], url_path='config')
    def config(self, request, pk=None):
        """GET 读取工作台展示开关（登录即可）；PUT 更新（HR 及以上）。

        配置为单例行(pk=1)，由 AnnouncementConfig.get_or_create_default 保证存在。
        """
        if request.method == 'PUT' and not user_has_any_role(request.user, HR_TIER):
            return Response({'detail': '无权限修改公告配置'}, status=status.HTTP_403_FORBIDDEN)
        cfg, _ = AnnouncementConfig.objects.get_or_create(pk=1, defaults={'show_on_workbench': True})
        if request.method == 'PUT':
            raw = request.data.get('show_on_workbench', cfg.show_on_workbench)
            if isinstance(raw, str):
                raw = raw.strip().lower() in ('1', 'true', 'yes', 'on', '是')
            cfg.show_on_workbench = bool(raw)
            cfg.save(update_fields=['show_on_workbench', 'updated_at'])
        out = AnnouncementConfigSerializer(cfg)
        return Response({'success': True, 'data': out.data})

    def create(self, request, *args, **kwargs):
        """创建后返回完整读序列化器（含 id），便于前端管理页刷新。"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        out = AnnouncementSerializer(serializer.instance, context={'request': request})
        return Response({'success': True, 'data': out.data}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新后返回完整读序列化器（含 id）。"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        out = AnnouncementSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})

    # ===== 附件：上传 / 删除（HR 及以上）=====
    @action(detail=True, methods=['post'], url_path='attachments')
    def upload_attachment(self, request, pk=None):
        """POST /api/v1/announcements/{id}/attachments/ — 上传单个附件。"""
        if not user_has_any_role(request.user, HR_TIER):
            return Response({'detail': '无权限上传附件'}, status=status.HTTP_403_FORBIDDEN)
        announcement = self.get_object()
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '未收到文件'}, status=status.HTTP_400_BAD_REQUEST)
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_EXT:
            return Response(
                {'detail': f'不支持的文件类型「{ext or "未知"}」，仅允许 PDF/Word/Excel/PPT/图片/压缩包'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file.size > MAX_UPLOAD:
            return Response(
                {'detail': f'文件大小 {file.size // 1024}KB 超过 {MAX_UPLOAD // 1024}KB 上限'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rel_path = f'announcements/{timezone.now():%Y%m%d}/{uuid4().hex}{ext}'
        saved = default_storage.save(rel_path, file)
        att = AnnouncementAttachment.objects.create(
            announcement=announcement,
            file=saved,
            original_name=file.name,
            file_size=file.size,
            content_type=file.content_type or '',
        )
        out = AnnouncementAttachmentSerializer(att, context={'request': request})
        return Response({'success': True, 'data': out.data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='attachments/(?P<attachment_id>[^/.]+)')
    def delete_attachment(self, request, pk=None, attachment_id=None):
        """DELETE /api/v1/announcements/{id}/attachments/{attachment_id}/ — 删除附件。"""
        if not user_has_any_role(request.user, HR_TIER):
            return Response({'detail': '无权限删除附件'}, status=status.HTTP_403_FORBIDDEN)
        announcement = self.get_object()
        att = AnnouncementAttachment.objects.filter(
            announcement=announcement, id=attachment_id, deleted_at__isnull=True
        ).first()
        if not att:
            return Response({'detail': '附件不存在'}, status=status.HTTP_404_NOT_FOUND)
        # 删除物理文件 + 软删 DB 行（与 FullAuditModel 约定一致）。
        try:
            att.file.delete(save=False)
        except Exception:
            pass
        att.soft_delete()
        return Response({'success': True})
