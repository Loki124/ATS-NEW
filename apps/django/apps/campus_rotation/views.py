"""campus_rotation 视图集。

三张表的 CRUD，统一范式（冻结方案 §3）：
- EnvelopeWriteMixin：写操作包 {success, data} 信封；
- V2Permission：资源级权限（按 action 派生读/写码）；
- CampusCRUDMixin：软删 + restore（复用 FullAuditModel.deleted_at）；
- permission_required / permission_required_map 严格按 §3.2–3.4 / §4.1。

绝不效仿 campus/views.py 的裸 IsAuthenticated 坏范式。
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions_v2 import V2Permission
from apps.core.views_permission_v2 import EnvelopeWriteMixin
from django.db import IntegrityError

from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import ClassRoom, LiveRoom, RotationArrangement
from .serializers import (
    ClassRoomSerializer,
    LiveRoomSerializer,
    RotationArrangementSerializer,
)
from .validators import user_has_campus_role


class CampusCRUDMixin:
    """写操作统一兜底：带入当前用户；软删（instance.soft_delete）。

    照搬 campus_control.views.CampusCRUDMixin（apps/campus_control/views.py:126）。
    """

    def perform_create(self, serializer):
        try:
            serializer.save(created_by=self.request.user, updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})

    def perform_update(self, serializer):
        try:
            serializer.save(updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})

    def perform_destroy(self, instance):
        instance.soft_delete()


# ---------------------------------------------------------------------------
# RotationArrangement
# ---------------------------------------------------------------------------
class RotationArrangementViewSet(EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = RotationArrangement.objects.all()
    serializer_class = RotationArrangementSerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:rotation:list'
    permission_required_map = {
        'create': 'recruit:campus:rotation:create',
        'update': 'recruit:campus:rotation:edit',
        'partial_update': 'recruit:campus:rotation:edit',
        'destroy': 'recruit:campus:rotation:delete',
        'restore': 'recruit:campus:rotation:edit',
        'batch_assign': 'recruit:campus:rotation:edit',
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = RotationArrangement.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        stage = params.get('stage')
        if stage:
            qs = qs.filter(stage=stage)
        current_dept = params.get('current_dept')
        if current_dept:
            qs = qs.filter(current_dept_id=current_dept)
        mentor = params.get('mentor')
        if mentor:
            qs = qs.filter(mentor_id=mentor)
        head_teacher = params.get('head_teacher')
        if head_teacher:
            qs = qs.filter(head_teacher_id=head_teacher)
        class_room = params.get('class_room')
        if class_room:
            qs = qs.filter(class_room_id=class_room)
        direct_manager = params.get('direct_manager')
        if direct_manager:
            qs = qs.filter(direct_manager_id=direct_manager)
        person_id = params.get('person_id')
        if person_id:
            qs = qs.filter(person_id=person_id)
        search = params.get('search')
        if search:
            qs = qs.filter(note__icontains=search)
        return qs

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删的轮岗安排。

        软删后 get_queryset() 已过滤 deleted_at，故直接走默认 manager 取对象（含已删），
        否则对软删记录 restore 会 404（对齐 campus_control 原实现意图）。
        """
        instance = self.queryset.model.objects.filter(pk=pk).first()
        if instance is None:
            return Response({'success': False, 'message': '轮岗安排不存在'}, status=404)
        instance.restore()
        return Response({'success': True, 'id': str(instance.id)})

    @action(detail=False, methods=['post'], url_path='batch-assign')
    def batch_assign(self, request):
        """批量调整阶段/部门/班主任。

        入参: {ids: [...], stage?, current_dept?, head_teacher?}
        """
        data = request.data or {}
        ids = data.get('ids') or []
        if not ids:
            return Response(
                {'success': False, 'message': 'ids 必填'},
                status=400,
            )
        updates = {}
        stage = data.get('stage')
        if stage is not None:
            updates['stage'] = stage
        current_dept = data.get('current_dept')
        if current_dept is not None:
            updates['current_dept_id'] = current_dept
        head_teacher = data.get('head_teacher')
        if head_teacher is not None:
            if not user_has_campus_role(head_teacher, 'HEAD_TEACHER'):
                return Response(
                    {'success': False, 'message': '班主任须具备 HEAD_TEACHER 身份'},
                    status=400,
                )
            updates['head_teacher_id'] = head_teacher
        if not updates:
            return Response(
                {'success': False, 'message': '至少提供一个更新字段（stage/current_dept/head_teacher）'},
                status=400,
            )
        updates['updated_by_id'] = request.user.id
        count = RotationArrangement.objects.filter(
            id__in=ids, deleted_at__isnull=True,
        ).update(**updates)
        return Response({'success': True, 'data': {'updated': count}})


# ---------------------------------------------------------------------------
# LiveRoom
# ---------------------------------------------------------------------------
class LiveRoomViewSet(EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = LiveRoom.objects.all()
    serializer_class = LiveRoomSerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:resource:list'
    permission_required_map = {
        'create': 'recruit:campus:resource:create',
        'update': 'recruit:campus:resource:edit',
        'partial_update': 'recruit:campus:resource:edit',
        'destroy': 'recruit:campus:resource:delete',
        'restore': 'recruit:campus:resource:edit',
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = LiveRoom.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        department = params.get('department')
        if department:
            qs = qs.filter(department_id=department)
        bu = params.get('bu')
        if bu:
            qs = qs.filter(bu_id=bu)
        platform = params.get('platform')
        if platform:
            qs = qs.filter(platform=platform)
        is_active = params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=(is_active == 'true' or is_active == '1'))
        search = params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删的直播间（含已软删对象，见 RotationArrangementViewSet.restore）。"""
        instance = self.queryset.model.objects.filter(pk=pk).first()
        if instance is None:
            return Response({'success': False, 'message': '直播间不存在'}, status=404)
        instance.restore()
        return Response({'success': True, 'id': str(instance.id)})


# ---------------------------------------------------------------------------
# ClassRoom
# ---------------------------------------------------------------------------
class ClassRoomViewSet(EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ClassRoom.objects.all()
    serializer_class = ClassRoomSerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:class:list'
    permission_required_map = {
        'create': 'recruit:campus:class:create',
        'update': 'recruit:campus:class:edit',
        'partial_update': 'recruit:campus:class:edit',
        'destroy': 'recruit:campus:class:delete',
        'restore': 'recruit:campus:class:edit',
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ClassRoom.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        head_teacher = params.get('head_teacher')
        if head_teacher:
            qs = qs.filter(head_teacher_id=head_teacher)
        batch = params.get('batch')
        if batch:
            qs = qs.filter(batch=batch)
        search = params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删的班级（含已软删对象，见 RotationArrangementViewSet.restore）。"""
        instance = self.queryset.model.objects.filter(pk=pk).first()
        if instance is None:
            return Response({'success': False, 'message': '班级不存在'}, status=404)
        instance.restore()
        return Response({'success': True, 'id': str(instance.id)})
