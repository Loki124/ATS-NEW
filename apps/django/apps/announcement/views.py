"""制度公告视图 — 招聘专家查看 / HR 及以上维护。"""
import logging
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

from apps.core.models import User
from apps.notification.models import NotificationLog
from apps.notification.services import NotificationService, SendNotificationData

from .models import Announcement, AnnouncementAttachment, AnnouncementConfig, AnnouncementPushRecord
from .serializers import (
    AnnouncementSerializer,
    AnnouncementWriteSerializer,
    AnnouncementAttachmentSerializer,
    AnnouncementConfigSerializer,
    AnnouncementPushRecordSerializer,
)

logger = logging.getLogger(__name__)

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
        # 列表默认仅上架; 详情/编辑/删除等动作需能操作下架项(否则下架记录无法重新上架/删除, 会 404)。
        # 管理后台传 show_inactive=true 时列表连下架项一并展示。
        if self.action == 'list' and not self.request.query_params.get('show_inactive'):
            qs = qs.filter(is_active=True)
        return qs

    def list(self, request, *args, **kwargs):
        """覆盖 list 以返回 {success, data} 信封（与其它端点一致）。"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        """覆盖 retrieve 以返回 {success, data} 信封（与 list 一致）。"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return Response({'success': True, 'data': serializer.data})

    # ===== 模块级配置：工作台展示开关（总开关）=====
    @action(detail=False, methods=['get', 'put'], url_path='config')
    def config(self, request, pk=None):
        """GET 读取工作台模块开关（登录即可）；PUT 更新（HR 及以上）。

        配置为单例行(pk=1)，由 AnnouncementConfig.get_or_create_default 保证存在。
        单条公告的展示位置（工作台卡片 / 更多入口）由公告自身字段控制，不在此处。
        """
        if request.method == 'PUT' and not user_has_any_role(request.user, HR_TIER):
            return Response({'detail': '无权限修改公告配置'}, status=status.HTTP_403_FORBIDDEN)
        cfg, _ = AnnouncementConfig.objects.get_or_create(pk=1, defaults={'show_on_workbench': True})
        if request.method == 'PUT':
            wb = request.data.get('show_on_workbench', cfg.show_on_workbench)
            if isinstance(wb, str):
                wb = wb.strip().lower() in ('1', 'true', 'yes', 'on', '是')
            cfg.show_on_workbench = bool(wb)
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
            logger.warning('物理文件删除失败（DB 软删仍生效）attachment=%s', att.id, exc_info=True)
        att.soft_delete()
        return Response({'success': True})

    # ===== 推送记录 =====
    def _audience_users(self, announcement: Announcement):
        """返回公告受众对应的活跃用户 queryset。"""
        qs = User.objects.filter(is_active=True, deleted_at__isnull=True)
        if announcement.audience == 'ALL':
            return qs
        # RECRUIT_EXPERT 暂按 HR/HRBP/SUPER_ADMIN 兜底（系统尚无独立 RECRUITER 角色码）
        recruit_role_codes = ('HR', 'HRBP', 'SUPER_ADMIN')
        from apps.core.models_permission_v2 import UserRoleV2
        user_ids = UserRoleV2.objects.filter(
            role_code__in=recruit_role_codes, system_code='recruit',
        ).values_list('user_id', flat=True)
        return qs.filter(id__in=user_ids)

    def _send_push_notifications(self, request, announcement: Announcement, channel: str):
        """向受众批量发送通知，并创建推送记录。"""
        users = list(self._audience_users(announcement))
        total = len(users)
        if total == 0:
            return None, '当前受众范围内没有可推送用户'

        record = AnnouncementPushRecord.objects.create(
            announcement=announcement,
            pushed_by=request.user if request.user.is_authenticated else None,
            total_count=total,
            channel=channel,
            context={},
            created_by=request.user if request.user.is_authenticated else None,
            updated_by=request.user if request.user.is_authenticated else None,
        )

        link = f'/announcements/{announcement.id}'
        log_ids = []
        for user in users:
            try:
                result = NotificationService.send_notification(SendNotificationData(
                    recipient_id=str(user.id),
                    title=f'《{announcement.title}》已发布',
                    content=f'请查看新{announcement.get_category_display()}《{announcement.title}》。',
                    link=link,
                    source='ANNOUNCEMENT',
                    source_id=str(announcement.id),
                    channel=channel,
                ))
                if result.get('sent'):
                    log_ids.append(result.get('log_id'))
            except Exception:
                # 单用户发送失败不影响整体流程，记录中不含该失败日志
                logger.warning('公告单用户发送失败 announcement=%s user=%s', announcement.id, user.id, exc_info=True)
                continue

        record.context = {'log_ids': log_ids}
        record.save(update_fields=['context'])
        return record, None

    @action(detail=True, methods=['post'], url_path='push')
    def push(self, request, pk=None):
        """POST /api/v1/announcements/{id}/push/ — 推送公告给受众。"""
        if not user_has_any_role(request.user, HR_TIER):
            return Response({'detail': '无权限推送'}, status=status.HTTP_403_FORBIDDEN)
        announcement = self.get_object()
        channel = request.data.get('channel', 'IN_APP')
        if channel not in ('IN_APP', 'WECOM'):
            channel = 'IN_APP'
        record, error = self._send_push_notifications(request, announcement, channel)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        out = AnnouncementPushRecordSerializer(record, context={'request': request})
        return Response({'success': True, 'data': out.data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='push/(?P<push_id>[^/.]+)/notify-unread')
    def notify_unread(self, request, pk=None, push_id=None):
        """POST /api/v1/announcements/{id}/push/{push_id}/notify-unread/ — 再次通知未读人员。"""
        if not user_has_any_role(request.user, HR_TIER):
            return Response({'detail': '无权限操作'}, status=status.HTTP_403_FORBIDDEN)
        announcement = self.get_object()
        record = AnnouncementPushRecord.objects.filter(
            announcement=announcement, id=push_id, deleted_at__isnull=True,
        ).first()
        if not record:
            return Response({'detail': '推送记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        log_ids = record.log_ids
        if not log_ids:
            return Response({'detail': '没有可通知的用户'}, status=status.HTTP_400_BAD_REQUEST)

        unread_logs = list(NotificationLog.objects.filter(
            id__in=log_ids, read_at__isnull=True, deleted_at__isnull=True,
        ).select_related('recipient'))
        if not unread_logs:
            return Response({'detail': '已无未读人员'}, status=status.HTTP_400_BAD_REQUEST)

        link = f'/announcements/{announcement.id}'
        notified = 0
        for log in unread_logs:
            if not log.recipient:
                continue
            try:
                NotificationService.send_notification(SendNotificationData(
                    recipient_id=str(log.recipient_id),
                    title=f'提醒：您还未阅读《{announcement.title}》',
                    content=f'请及时查看新{announcement.get_category_display()}《{announcement.title}》。',
                    link=link,
                    source='ANNOUNCEMENT_REMIND',
                    source_id=str(announcement.id),
                    channel=record.channel,
                ))
                notified += 1
            except Exception:
                logger.warning('公告提醒单用户发送失败 announcement=%s recipient=%s', announcement.id, log.recipient_id, exc_info=True)
                continue

        return Response({'success': True, 'data': {'notified': notified}})
