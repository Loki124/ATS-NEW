"""campus_rotation 视图集。

三张表的 CRUD，统一范式（冻结方案 §3）：
- EnvelopeWriteMixin：写操作包 {success, data} 信封；
- V2Permission：资源级权限（按 action 派生读/写码）；
- CampusCRUDMixin：软删 + restore（复用 FullAuditModel.deleted_at）；
- ScopeQuerysetMixin：行级数据隔离（2026-10-19 S5-03 接入，需求 1-2）；
- permission_required / permission_required_map 严格按 §3.2–3.4 / §4.1。

绝不效仿 campus/views.py 的裸 IsAuthenticated 坏范式。

🔴 行级隔离接入口径（S5-03，勿改）：
    本模块三个 ViewSet 的 get_queryset() **对所有 action 统一套 scope**，不是只对 list。
    原因：DRF 的 get_object() 复用 get_queryset()，若按 `if self.action != 'list': return qs`
    提前返回全表（campus_control.PersonViewSet 的既有写法），则 retrieve/update/delete
    会**完全绕过行级隔离** —— 带教导师只要猜到 id 就能改别人的轮岗安排，属越权。
    需求 1-2「各个角色数据相互隔离」要求读写同源，故此处一律不提前返回。
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions_v2 import ScopeQuerysetMixin, V2Permission
from apps.core.views_permission_v2 import EnvelopeWriteMixin
from django.db import IntegrityError

from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import ClassRoom, LiveRoom, RotationArrangement, ServiceDept
from .serializers import (
    ClassRoomSerializer,
    LiveRoomSerializer,
    RotationArrangementSerializer,
    ServiceDeptSerializer,
)
from .validators import user_has_campus_role


class CampusCRUDMixin:
    """写操作统一兜底：带入当前用户；软删（instance.soft_delete）；审计埋点（需求 5-6）。

    照搬 campus_control.views.CampusCRUDMixin（apps/campus_control/views.py:126）并补审计。
    """

    def _audit_entity(self) -> str:
        """审计实体标识：优先用子类声明的 audit_entity，否则回退模型名。"""
        return getattr(self, 'audit_entity', self.queryset.model.__name__)

    def perform_create(self, serializer):
        try:
            instance = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})
        from apps.common.audit_helper import log_action
        log_action(self.request, 'create', self._audit_entity(), instance.pk)

    def perform_update(self, serializer):
        try:
            instance = serializer.save(updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})
        from apps.common.audit_helper import log_action
        log_action(self.request, 'update', self._audit_entity(), instance.pk)

    def perform_destroy(self, instance):
        pk = instance.pk
        instance.soft_delete()
        from apps.common.audit_helper import log_action
        log_action(self.request, 'delete', self._audit_entity(), pk)


# ---------------------------------------------------------------------------
# RotationArrangement
# ---------------------------------------------------------------------------
class RotationArrangementViewSet(
    EnvelopeWriteMixin, CampusCRUDMixin, ScopeQuerysetMixin, viewsets.ModelViewSet
):
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
    # 行级隔离配置（与 core/entity_scope.py 的 ENTITY_SCOPE 逐项对应，
    # tests/test_entity_scope.py 会断言两者不漂移）
    scope_field = 'current_dept'
    scope_creator_field = 'created_by'
    data_perm_entity = 'campus_arrangement'

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
        service_dept = params.get('service_dept')
        if service_dept:
            qs = qs.filter(service_dept_id=service_dept)
        direct_manager = params.get('direct_manager')
        if direct_manager:
            qs = qs.filter(direct_manager_id=direct_manager)
        person_id = params.get('person_id')
        if person_id:
            qs = qs.filter(person_id=person_id)
        search = params.get('search')
        if search:
            qs = qs.filter(note__icontains=search)
        # 行级隔离收口：不分 action，读写同源（见模块 docstring 🔴 说明）
        return self.scope_queryset(qs)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删的轮岗安排。

        软删后 get_queryset() 已过滤 deleted_at，故直接走默认 manager 取对象（含已删），
        否则对软删记录 restore 会 404（对齐 campus_control 原实现意图）。

        🔴 S5-03：取对象必须**重新套一遍行级隔离**。原实现直接
        `self.queryset.model.objects.filter(pk=pk)` 完全绕开 get_queryset()，
        意味着任何有 restore 权限的账号都能凭 id 恢复（复活）他人部门下的
        软删记录 —— 行级隔离对 restore 形同虚设。此处复用 scope_queryset。
        """
        qs = self.scope_queryset(self.queryset.model.objects.filter(pk=pk))
        instance = qs.first()
        if instance is None:
            return Response({'success': False, 'message': '轮岗安排不存在'}, status=404)
        instance.restore()
        from apps.common.audit_helper import log_action
        log_action(self.request, 'restore', 'RotationArrangement', instance.pk)
        return Response({'success': True, 'id': str(instance.id)})

    @action(detail=False, methods=['post'], url_path='batch-assign')
    def batch_assign(self, request):
        """批量调整阶段/部门/班主任。

        入参: {ids: [...], stage?, current_dept?, head_teacher?}

        🔴 S5-03：原实现 `.filter(id__in=ids).update(...)` 直接查默认 manager，
        绕过 get_queryset() 的 deleted_at 与行级隔离双重过滤 —— 传入他人部门的
        id 即可跨范围改数据。此处改为走 scope_queryset（scope_queryset 内部已含
        deleted_at 过滤，因为本类 get_queryset 首行即 filter(deleted_at__isnull=True)，
        这里需显式补上）。
        ⚠️ 另：批量更新的字段白名单、事务包裹与审计日志属需求 5-3（S5-18），本批不含。
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
        # 🔴 S5-03：批量更新必须走 scope_queryset 收口，否则传入他人部门的 id
        #    即可跨范围改数据（行级隔离对 batch_assign 形同虚设）。
        #    scope_queryset 内部不含 deleted_at 过滤，故外层先 filter(deleted_at__isnull=True)。
        count = self.scope_queryset(
            RotationArrangement.objects.filter(id__in=ids, deleted_at__isnull=True)
        ).update(**updates)
        from apps.common.audit_helper import log_action
        log_action(
            self.request, 'batch_assign', 'RotationArrangement',
            f'ids={",".join(str(i) for i in ids)}', new_value=str(updates),
        )
        return Response({'success': True, 'data': {'updated': count}})


# ---------------------------------------------------------------------------
# LiveRoom
# ---------------------------------------------------------------------------
class LiveRoomViewSet(
    EnvelopeWriteMixin, CampusCRUDMixin, ScopeQuerysetMixin, viewsets.ModelViewSet
):
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
    # 行级隔离配置（与 core/entity_scope.py 的 ENTITY_SCOPE['campus_resource'] 对应）
    scope_field = 'bu'
    scope_creator_field = 'created_by'
    data_perm_entity = 'campus_resource'

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
        # 行级隔离收口：不分 action，读写同源（见模块 docstring 🔴 说明）
        return self.scope_queryset(qs)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删的直播间。

        🔴 S5-03：取对象必须重新套行级隔离（否则凭 id 复活他人部门资源）。
        """
        qs = self.scope_queryset(self.queryset.model.objects.filter(pk=pk))
        instance = qs.first()
        if instance is None:
            return Response({'success': False, 'message': '直播间不存在'}, status=404)
        instance.restore()
        from apps.common.audit_helper import log_action
        log_action(self.request, 'restore', 'LiveRoom', instance.pk)
        return Response({'success': True, 'id': str(instance.id)})


# ---------------------------------------------------------------------------
# ServiceDept
# ---------------------------------------------------------------------------
class ServiceDeptViewSet(
    EnvelopeWriteMixin, CampusCRUDMixin, ScopeQuerysetMixin, viewsets.ModelViewSet
):
    """客服部门（轮岗资源）。

    与直播间同域（campus_resource）：复用 recruit:campus:resource:* 权限码，
    行级隔离 scope_field='bu'，data_perm_entity='campus_resource'（与直播间一致）。
    """

    queryset = ServiceDept.objects.all()
    serializer_class = ServiceDeptSerializer
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
    # 与直播间同域：归属 BU 作行级隔离字段（见 entity_scope.py campus_resource）
    scope_field = 'bu'
    scope_creator_field = 'created_by'
    data_perm_entity = 'campus_resource'
    audit_entity = 'ServiceDept'

    def get_queryset(self):
        qs = ServiceDept.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        department = params.get('department')
        if department:
            qs = qs.filter(department_id=department)
        bu = params.get('bu')
        if bu:
            qs = qs.filter(bu_id=bu)
        is_active = params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=(is_active == 'true' or is_active == '1'))
        search = params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        # 行级隔离收口：不分 action，读写同源（见模块 docstring 🔴 说明）
        return self.scope_queryset(qs)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删的客服部门。

        🔴 S5-03：取对象必须重新套行级隔离（否则凭 id 复活他人部门资源）。
        """
        qs = self.scope_queryset(self.queryset.model.objects.filter(pk=pk))
        instance = qs.first()
        if instance is None:
            return Response({'success': False, 'message': '客服部门不存在'}, status=404)
        instance.restore()
        from apps.common.audit_helper import log_action
        log_action(self.request, 'restore', 'ServiceDept', instance.pk)
        return Response({'success': True, 'id': str(instance.id)})


# ---------------------------------------------------------------------------
# ClassRoom
# ---------------------------------------------------------------------------
class ClassRoomViewSet(
    EnvelopeWriteMixin, CampusCRUDMixin, ScopeQuerysetMixin, viewsets.ModelViewSet
):
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
    # 行级隔离配置（与 core/entity_scope.py 的 ENTITY_SCOPE['campus_class'] 对应）
    scope_field = 'hrbp__department'
    scope_creator_field = 'created_by'
    data_perm_entity = 'campus_class'

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
        # 行级隔离收口：不分 action，读写同源（见模块 docstring 🔴 说明）
        return self.scope_queryset(qs)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删的班级。

        🔴 S5-03：取对象必须重新套行级隔离（否则凭 id 复活他人班级）。
        """
        qs = self.scope_queryset(self.queryset.model.objects.filter(pk=pk))
        instance = qs.first()
        if instance is None:
            return Response({'success': False, 'message': '班级不存在'}, status=404)
        instance.restore()
        from apps.common.audit_helper import log_action
        log_action(self.request, 'restore', 'ClassRoom', instance.pk)
        return Response({'success': True, 'id': str(instance.id)})

    @action(detail=True, methods=['get'], url_path='members')
    def members(self, request, pk=None):
        """S5-06（需求 3-2）：班级成员明细（校招生档案）。

        按 class_room 过滤 Person；班级本身访问受 get_object 行级隔离保护，
        此处不再对 Person 叠加 campus_class scope（Person 未登记该实体，会 FieldError）。
        """
        instance = self.get_object()
        from apps.campus_control.models import Person
        from apps.campus_control.serializers import PersonSerializer
        qs = Person.objects.filter(deleted_at__isnull=True, class_room_id=instance.id)
        data = PersonSerializer(qs, many=True).data
        return Response({'success': True, 'data': data})
