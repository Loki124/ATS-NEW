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
from zipfile import BadZipFile

from django.db import IntegrityError, transaction
from django.db.models import Count
from django_fsm import TransitionNotAllowed
from openpyxl.utils.exceptions import InvalidFileException
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.campus_control.models import Person
from apps.common.excel import build_export_response
from apps.common.pagination import StandardResultsSetPagination
from apps.core.dept_depth import bg_ancestor, bu_ancestor
from apps.core.models import Department
from apps.core.permissions_v2 import ScopeQuerysetMixin, V2Permission
from apps.core.scope_resolver import scope_filter_q
from apps.core.views_permission_v2 import EnvelopeWriteMixin
from apps.demand.models import Demand

from . import io_rotation_resource
from .models import (
    ClassRoom,
    ConcurrentPostRecord,
    RotationApproval,
    RotationArrangement,
    RotationResource,
    RotationStage,
)
from .serializers import (
    ClassRoomSerializer,
    ConcurrentPostRecordSerializer,
    RotationApprovalSerializer,
    RotationArrangementSerializer,
    RotationResourceSerializer,
    RotationStageSerializer,
)
from .services import stats_overview
from .validators import user_has_campus_role


class BatchAssignError(Exception):
    """批量调整中的单条失败（用于触发整批回滚）。

    携带 detail = {'id': ..., 'reason': ...}，由 batch_assign 捕获后转成
    「整批拒绝 + 失败明细」响应。
    """

    def __init__(self, detail: dict):
        super().__init__(detail.get('reason', '批量调整失败'))
        self.detail = detail


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
        resource = params.get('resource')
        if resource:
            qs = qs.filter(resource_id=resource)
        direct_manager = params.get('direct_manager')
        if direct_manager:
            qs = qs.filter(direct_manager_id=direct_manager)
        person_id = params.get('person_id')
        if person_id:
            qs = qs.filter(person_id=person_id)
        # 2026-10-22：人员级关联筛选（校招生档案主键 nanoid）。
        #   与旧口径 person_id（账号 id）并存：前者是可靠口径，后者仅兼容历史数据。
        campus_person = params.get('campus_person')
        if campus_person:
            qs = qs.filter(campus_person_id=campus_person)
        search = params.get('search')
        if search:
            qs = qs.filter(note__icontains=search)
        # 行级隔离收口：不分 action，读写同源（见模块 docstring 🔴 说明）
        return self.scope_queryset(qs)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删的轮岗安排。

        取对象必须走**含软删行**的 manager（2026-10-21 卡 D3: 默认 manager 已过滤
        deleted_at，改用 ``all_objects``），否则对软删记录 restore 会 404
        （对齐 campus_control 原实现意图）。

        🔴 S5-03：取对象必须**重新套一遍行级隔离**。原实现直接
        `self.queryset.model.objects.filter(pk=pk)` 完全绕开 get_queryset()，
        意味着任何有 restore 权限的账号都能凭 id 恢复（复活）他人部门下的
        软删记录 —— 行级隔离对 restore 形同虚设。此处复用 scope_queryset。
        """
        qs = self.scope_queryset(self.queryset.model.all_objects.filter(pk=pk))
        instance = qs.first()
        if instance is None:
            return Response({'success': False, 'message': '轮岗安排不存在'}, status=404)
        instance.restore()
        from apps.common.audit_helper import log_action
        log_action(self.request, 'restore', 'RotationArrangement', instance.pk)
        return Response({'success': True, 'id': str(instance.id)})

    @action(detail=False, methods=['post'], url_path='batch-assign')
    def batch_assign(self, request):
        """批量调整轮岗安排信息（需求 5-3 / S5-18）。

        入参: {ids: [...], <字段>: <值>, ...}

        字段白名单（规格 §6.3）：
          current_dept / head_teacher / mentor / direct_manager /
          rotation_start / rotation_end / resource
        🔴 `stage` **不在白名单**：阶段是 FSM 流程态，必须走 /transition/ 端点。

        🔴 mentor / direct_manager 走**审批**（需求 5-5）：本端点不直改这两个字段，
        而是为每条记录创建 RotationApproval 申请单；审批通过后才由审批动作落字段。

        事务与失败语义（规格 §6.3）：
          - 全批校验通过后才落库（transaction.atomic 包裹）
          - 任一条校验失败 → **整批拒绝**，返回失败明细（不做静默部分成功）
          - 每条成功记录写一条 AuditLog
        """
        data = request.data or {}
        ids = data.get('ids') or []
        if not ids:
            return Response(
                {'success': False, 'message': 'ids 必填'},
                status=400,
            )
        if 'stage' in data:
            return Response(
                {'success': False, 'message': '阶段(stage)变更请走流转端点 /transition/'},
                status=400,
            )

        # ── ① 字段白名单 ──
        allowed_fields = {
            'current_dept', 'head_teacher', 'mentor', 'direct_manager',
            'rotation_start', 'rotation_end', 'resource',
        }
        payload_fields = {k: v for k, v in data.items() if k in allowed_fields}
        unknown_fields = [
            k for k in data.keys()
            if k not in allowed_fields and k != 'ids'
        ]
        if unknown_fields:
            return Response(
                {
                    'success': False,
                    'message': f'不支持的字段：{",".join(sorted(unknown_fields))}；'
                               f'可用字段：{",".join(sorted(allowed_fields))}',
                },
                status=400,
            )
        if not payload_fields:
            return Response(
                {
                    'success': False,
                    'message': '至少提供一个更新字段（'
                               f'{"/".join(sorted(allowed_fields))}）',
                },
                status=400,
            )

        # ── ② 逐条目标校验（先全批校验，任一失败整批拒绝）──
        from apps.campus_rotation.services.approval import (
            ApprovalError,
            create_approval_request,
        )

        # 2.1 目标记录必须在可见范围内（行级隔离）
        visible = self.scope_queryset(
            RotationArrangement.objects.filter(id__in=ids, deleted_at__isnull=True)
        )
        targets = {str(o.id): o for o in visible}
        missing = [str(i) for i in ids if str(i) not in targets]
        if missing:
            return Response(
                {
                    'success': False,
                    'message': '部分记录不存在或不在可操作范围内',
                    'data': {'failed': [{'id': mid, 'reason': '记录不存在或无权限'} for mid in missing]},
                },
                status=400,
            )

        # 2.2 字段级校验（对所有目标一致校验，因为传的是同一组值）
        field_errors = []
        if 'head_teacher' in payload_fields and payload_fields['head_teacher'] is not None:
            if not user_has_campus_role(payload_fields['head_teacher'], 'HEAD_TEACHER'):
                field_errors.append({'field': 'head_teacher', 'reason': '班主任须具备 HEAD_TEACHER 身份'})
        if 'mentor' in payload_fields and payload_fields['mentor'] is not None:
            if not user_has_campus_role(payload_fields['mentor'], 'CAMPUS_MENTOR'):
                field_errors.append({'field': 'mentor', 'reason': '带教导师须具备 CAMPUS_MENTOR 身份'})
        # 日期区间
        rs = payload_fields.get('rotation_start')
        re_ = payload_fields.get('rotation_end')
        if rs and re_ and str(re_) < str(rs):
            field_errors.append({'field': 'rotation_end', 'reason': '轮岗结束不能早于轮岗开始'})
        # FK 存在性（current_dept / resource）
        fk_instances = {}
        for fk_field, model in (('current_dept', Department), ('resource', RotationResource)):
            if fk_field in payload_fields and payload_fields[fk_field] is not None:
                inst = model.objects.filter(pk=payload_fields[fk_field]).first()
                if inst is None:
                    field_errors.append({'field': fk_field, 'reason': '目标记录不存在'})
                else:
                    fk_instances[fk_field] = inst
        if field_errors:
            return Response(
                {
                    'success': False,
                    'message': '校验失败，整批未执行',
                    'data': {'failed': field_errors},
                },
                status=400,
            )

        # ── ③ 事务：全批落库 ──
        from apps.common.audit_helper import log_action

        # mentor / direct_manager 需审批 → 单独走申请单，不直改
        approval_fields = {'mentor', 'direct_manager'}
        direct_fields = {
            k: v for k, v in payload_fields.items() if k not in approval_fields
        }

        updated_count = 0
        approval_count = 0
        try:
            with transaction.atomic():
                for obj in targets.values():
                    if direct_fields:
                        for field, value in direct_fields.items():
                            # 🔴 FK 字段必须赋模型实例，不能赋 pk 字符串
                            #    （Django 报 "must be a Department instance"）
                            setattr(obj, field, fk_instances.get(field, value))
                        obj.updated_by_id = request.user.id
                        obj.save(update_fields=list(direct_fields.keys()) + ['updated_by', 'updated_at'])
                        updated_count += 1
                        log_action(
                            request, 'batch_assign', 'RotationArrangement', str(obj.pk),
                            new_value=str(direct_fields),
                        )
                    # 需审批的字段：为每条记录建申请单（不改业务字段）
                    for field, ctype in (('mentor', 'MENTOR_CHANGE'),
                                         ('direct_manager', 'MANAGER_CHANGE')):
                        if field not in payload_fields:
                            continue
                        new_user_id = payload_fields[field]
                        if new_user_id is None:
                            continue
                        try:
                            create_approval_request(
                                arrangement=obj,
                                change_type=ctype,
                                new_user_id=new_user_id,
                                reason='批量调整发起',
                            )
                            approval_count += 1
                            log_action(
                                request, 'batch_approve_req', 'RotationApproval',
                                str(obj.pk), field=ctype, new_value=str(new_user_id),
                            )
                        except ApprovalError as exc:
                            # 单条建单失败 → 整批拒绝（事务回滚）
                            raise BatchAssignError({'id': str(obj.pk), 'reason': str(exc)})
        except BatchAssignError as exc:
            return Response(
                {
                    'success': False,
                    'message': '整批拒绝：部分记录变更申请创建失败，已全部回滚',
                    'data': {'failed': [exc.detail]},
                },
                status=400,
            )

        return Response({
            'success': True,
            'data': {
                'updated': updated_count,
                'approvalRequested': approval_count,
            },
        })

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        """轮岗阶段流转（FSM，需求 5-4 / S5-19）。

        入参: {action: 'submit'|'approve'|'reject'|'complete'|'terminate', reason?}

        所有 stage 流转只经此端点，确保 @transition 的 source/guard/副作用生效；
        通用 CRUD 的 stage 已设为只读（serializers.py）。非法流转（source 不匹配）
        或守卫不满足抛 TransitionNotAllowed → 统一返 409（对齐 application 服务契约）。
        """
        instance = self.get_queryset().filter(pk=pk).first()
        if instance is None:
            return Response({'success': False, 'message': '轮岗安排不存在'}, status=404)

        data = request.data or {}
        action = data.get('action')
        reason = data.get('reason')
        allowed = {'submit', 'approve', 'reject', 'complete', 'terminate'}
        if action not in allowed:
            return Response(
                {'success': False, 'message': f'不支持的流转动作: {action}'},
                status=400,
            )

        method = getattr(instance, action, None)
        if method is None or not hasattr(method, '_django_fsm'):
            return Response(
                {'success': False, 'message': f'当前状态不允许 {action}'},
                status=409,
            )

        try:
            with transaction.atomic():
                if action == 'terminate':
                    if not reason:
                        return Response(
                            {'success': False, 'message': '终止必须填写原因'},
                            status=400,
                        )
                    method(reason=reason)
                else:
                    method()
                instance.save()
        except TransitionNotAllowed as e:
            return Response(
                {'success': False, 'message': str(e) or f'当前状态不允许 {action}'},
                status=409,
            )

        from apps.common.audit_helper import log_action
        log_action(
            self.request, f'stage:{action}', 'RotationArrangement',
            instance.pk, new_value=instance.stage,
        )
        return Response(
            {'success': True, 'data': {'id': str(instance.id), 'stage': instance.stage}}
        )


# ---------------------------------------------------------------------------
# RotationStage（需求 5-8 / S5-21：N 段轮岗，每段独立考核）
# ---------------------------------------------------------------------------
class RotationStageViewSet(
    EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """轮岗阶段 CRUD。

    顶层资源，按 `?arrangement={id}` 过滤归属某轮岗安排的阶段；
    阶段期数 (stage_no) 在安排内唯一（unique_together，序列化器层校验）。

    🔴 行级隔离：阶段数据依附于轮岗安排，本ViewSet 不单独套 ScopeQuerysetMixin，
    由调用方在 `arrangement` 维度控制可见性；跨实体的完整隔离矩阵归 S5-24 统一落地。
    """

    queryset = RotationStage.objects.all()
    serializer_class = RotationStageSerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:rotation:list'
    permission_required_map = {
        'create': 'recruit:campus:rotation:edit',
        'update': 'recruit:campus:rotation:edit',
        'partial_update': 'recruit:campus:rotation:edit',
        'destroy': 'recruit:campus:rotation:delete',
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = RotationStage.objects.filter(deleted_at__isnull=True)
        arrangement = self.request.query_params.get('arrangement')
        if arrangement:
            qs = qs.filter(arrangement_id=arrangement)
        return qs

    @action(detail=True, methods=['post'], url_path='mark-assessed')
    def mark_assessed(self, request, pk=None):
        """阶段置为「已考核」（需求 5-9 / S5-22）。

        🔴 15 天规则：满 15 天（REQUIRED）且未填考核结论 → 拒绝，返 400。
        不足 15 天（WAIVED）→ 免考放行。
        """
        from apps.campus_rotation.services.assessment import (
            can_mark_assessed,
        )
        from apps.campus_rotation.services.assessment import (
            mark_assessed as do_mark_assessed,
        )

        instance = self.get_object()
        data = request.data or {}
        result = (data.get('result') or data.get('assessment_result') or '').strip()

        allowed, reason = can_mark_assessed(instance, pending_result=result)
        if not allowed:
            return Response(
                {'success': False, 'message': reason, 'code': 400},
                status=400,
            )

        do_mark_assessed(instance, result=result, assessed_by=request.user)

        from apps.common.audit_helper import log_action
        log_action(
            request, 'assess', 'RotationStage', instance.pk,
            new_value=instance.assessment_status,
        )
        return Response({
            'success': True,
            'data': {
                'id': str(instance.id),
                'assessmentStatus': instance.assessment_status,
                'assessmentResult': instance.assessment_result,
                'assessedAt': instance.assessed_at.isoformat() if instance.assessed_at else None,
            },
        })


# ---------------------------------------------------------------------------
# ConcurrentPostRecord（需求 5-2 / S5-25：兼岗记录）
# ---------------------------------------------------------------------------
class ConcurrentPostRecordViewSet(
    EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """兼岗记录 CRUD（本地落库 + 预留摩卡同步）。

    顶层资源，按 `?person=` / `?arrangement=` / `?sync_status=` 过滤。

    🔴 同步状态字段（sync_status / sync_request_id / sync_error / synced_at）
    序列化器层已设为只读，客户端不得直写；同步由 `sync` 动作调用
    `services.moka_sync.sync_concurrent_post` 独占写入（契约见 S5-26）。

    🔴 行级隔离：兼岗记录依附于轮岗安排/人员，本 ViewSet 不单独套
    ScopeQuerysetMixin，完整隔离矩阵归 S5-24 统一落地。
    """

    queryset = ConcurrentPostRecord.objects.all()
    serializer_class = ConcurrentPostRecordSerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:rotation:list'
    permission_required_map = {
        'create': 'recruit:campus:rotation:edit',
        'update': 'recruit:campus:rotation:edit',
        'partial_update': 'recruit:campus:rotation:edit',
        'destroy': 'recruit:campus:rotation:delete',
        'sync': 'recruit:campus:rotation:edit',
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ConcurrentPostRecord.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        person = params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        arrangement = params.get('arrangement')
        if arrangement:
            qs = qs.filter(arrangement_id=arrangement)
        sync_status = params.get('sync_status')
        if sync_status:
            qs = qs.filter(sync_status=sync_status)
        return qs

    @action(detail=True, methods=['post'], url_path='sync')
    def sync(self, request, pk=None):
        """触发摩卡兼岗同步（S5-26 钩子）。

        🔴 失败不阻塞主流程：同步异常一律落 sync_status='FAILED' + sync_error，
        返回 200，由调用方异步重试。
        """
        from apps.campus_rotation.services.moka_sync import sync_concurrent_post

        instance = self.get_object()
        # 返回值不用：响应体以落库后的 instance.sync_status 为准（更可靠，
        # 失败也落库），不取 sync_concurrent_post 的 bool 返回。
        sync_concurrent_post(instance)
        instance.refresh_from_db()
        from apps.common.audit_helper import log_action
        log_action(
            self.request, 'sync', 'ConcurrentPostRecord', instance.pk,
            new_value=instance.sync_status,
        )
        return Response({
            'success': True,
            'data': {
                'id': str(instance.id),
                'syncStatus': instance.sync_status,
                'syncRequestId': instance.sync_request_id,
                'syncError': instance.sync_error,
            },
        })


# ---------------------------------------------------------------------------
# RotationApproval（需求 5-5 / S5-17：轮岗变更审批）
# ---------------------------------------------------------------------------
class RotationApprovalViewSet(
    EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """轮岗变更审批单（更换带教导师 / 直接上级）。

    🔴 核心语义（规格 §6.5）：**创建申请单时不改业务字段** ——
    `RotationArrangement.mentor` / `direct_manager` 在审批通过（`approve`）后
    才由 `services/approval.py` 在同一事务内落值并写两条 AuditLog。

    免审路径（本 ViewSet 不介入）：兼岗记录创建、阶段/部门/日期等其它字段变更。
    """

    queryset = RotationApproval.objects.all()
    serializer_class = RotationApprovalSerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:approval:list'
    permission_required_map = {
        'create': 'recruit:campus:approval:create',
        'update': 'recruit:campus:approval:approve',
        'partial_update': 'recruit:campus:approval:approve',
        'destroy': 'recruit:campus:approval:approve',
        'approve': 'recruit:campus:approval:approve',
        'reject': 'recruit:campus:approval:reject',
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = RotationApproval.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        arrangement = params.get('arrangement')
        if arrangement:
            qs = qs.filter(arrangement_id=arrangement)
        status = params.get('status')
        if status:
            qs = qs.filter(status=status)
        change_type = params.get('change_type')
        if change_type:
            qs = qs.filter(change_type=change_type)
        return qs

    def create(self, request, *args, **kwargs):
        """创建变更申请单。

        🔴 `old_value` 由服务端从安排当前值快照生成，忽略客户端传入值。
        """
        from apps.campus_rotation.services.approval import (
            ApprovalError,
            create_approval_request,
        )

        data = request.data or {}
        arrangement = None
        arrangement_id = data.get('arrangement')
        if arrangement_id:
            # 🔴 必须显式查 RotationArrangement，不能用 self.get_queryset().model
            #    （那是 RotationApproval，会误查审批单导致恒 404）
            arrangement = RotationArrangement.objects.filter(
                pk=arrangement_id, deleted_at__isnull=True,
            ).first()
            if arrangement is None:
                return Response(
                    {'success': False, 'message': '轮岗安排不存在', 'code': 404},
                    status=404,
                )

        try:
            approval = create_approval_request(
                arrangement=arrangement,
                change_type=data.get('change_type'),
                new_user_id=data.get('new_value'),
                reason=data.get('reason') or '',
            )
        except ApprovalError as exc:
            return Response(
                {'success': False, 'message': str(exc), 'code': 400},
                status=400,
            )

        from apps.common.audit_helper import log_action
        log_action(
            request, 'create', 'RotationApproval', approval.pk,
            field=approval.change_type,
            old_value=approval.old_value, new_value=approval.new_value,
        )
        data_out = RotationApprovalSerializer(approval).data
        return Response({'success': True, 'data': data_out}, status=201)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """审批通过：落业务字段 + 同事务写两条 AuditLog。"""
        from apps.campus_rotation.services.approval import ApprovalError
        from apps.campus_rotation.services.approval import approve as do_approve

        instance = self.get_object()
        try:
            do_approve(instance, approver=request.user)
        except ApprovalError as exc:
            return Response(
                {'success': False, 'message': str(exc), 'code': 409},
                status=409,
            )
        instance.refresh_from_db()
        return Response({
            'success': True,
            'data': RotationApprovalSerializer(instance).data,
        })

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """审批驳回：仅记录，不落业务字段。"""
        from apps.campus_rotation.services.approval import ApprovalError
        from apps.campus_rotation.services.approval import reject as do_reject

        instance = self.get_object()
        data = request.data or {}
        try:
            do_reject(
                instance, approver=request.user,
                reason=data.get('reason') or data.get('reject_reason') or '',
            )
        except ApprovalError as exc:
            return Response(
                {'success': False, 'message': str(exc), 'code': 409},
                status=409,
            )
        instance.refresh_from_db()
        return Response({
            'success': True,
            'data': RotationApprovalSerializer(instance).data,
        })


# ---------------------------------------------------------------------------
# RotationResource（轮岗资源）
# ---------------------------------------------------------------------------
class RotationResourceViewSet(
    EnvelopeWriteMixin, CampusCRUDMixin, ScopeQuerysetMixin, viewsets.ModelViewSet
):
    """轮岗资源 CRUD（2026-10-22 兵哥指令：直播间 + 客服部门整合为一张表）。

    · 一张 `RotationResource` 表承载三种形态：`resource_type` 区分
      直播间 / 客服部门 / 其他；
    · 权限码沿用原「直播间 + 客服部门」共用的 `recruit:campus:resource:*`；
    · 行级隔离 `scope_field='bu'`、`data_perm_entity='campus_resource'` 与旧两表一致
      （见 core/entity_scope.py 的 ENTITY_SCOPE['campus_resource']）。
    """

    queryset = RotationResource.objects.all()
    serializer_class = RotationResourceSerializer
    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:resource:list'
    permission_required_map = {
        'create': 'recruit:campus:resource:create',
        'update': 'recruit:campus:resource:edit',
        'partial_update': 'recruit:campus:resource:edit',
        'destroy': 'recruit:campus:resource:delete',
        'restore': 'recruit:campus:resource:edit',
        # 2026-10-22：轮岗资源导入/导出（Excel）。键是 **action 方法名**（不是 url_path），
        # 见 apps/core/permissions_v2.py:128-131（V2Permission 显式 action 覆盖表）。
        'export_resources': 'recruit:campus:resource:list',
        'template_resources': 'recruit:campus:resource:list',
        'import_resources': 'recruit:campus:resource:create',
    }
    pagination_class = StandardResultsSetPagination
    # 行级隔离配置（与 core/entity_scope.py 的 ENTITY_SCOPE['campus_resource'] 对应）
    scope_field = 'bu'
    scope_creator_field = 'created_by'
    data_perm_entity = 'campus_resource'
    audit_entity = 'RotationResource'

    def get_queryset(self):
        qs = RotationResource.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        department = params.get('department')
        if department:
            # 2026-10-22：支持**多选**部门（部门树筛选组件回传逗号分隔的 id 列表）。
            #   单个 id 仍按原语义过滤（向后兼容，不影响既有调用方）。
            dept_ids = [d.strip() for d in str(department).split(',') if d.strip()]
            if dept_ids:
                qs = qs.filter(department_id__in=dept_ids)
        bu = params.get('bu')
        if bu:
            qs = qs.filter(bu_id=bu)
        resource_type = params.get('resource_type')
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
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
        """恢复已软删的轮岗资源。

        🔴 S5-03：取对象必须重新套行级隔离（否则凭 id 复活他人部门资源）。
        """
        qs = self.scope_queryset(self.queryset.model.all_objects.filter(pk=pk))
        instance = qs.first()
        if instance is None:
            return Response({'success': False, 'message': '轮岗资源不存在'}, status=404)
        instance.restore()
        from apps.common.audit_helper import log_action
        log_action(self.request, 'restore', 'RotationResource', instance.pk)
        return Response({'success': True, 'id': str(instance.id)})

    # ------------------------------------------------------------------
    # 导入 / 导出（2026-10-22 兵哥指令：轮岗资源导入导出，Excel 格式）
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='export')
    def export_resources(self, request):
        """导出轮岗资源（xlsx）。

        GET /api/v1/campus-rotation/resources/export/?file_format=xlsx

        · 数据范围 = 当前用户**可见范围**（行级隔离，与列表同源）；
        · 资源类型 / 平台写**中文名**、地点为自由文本原样输出、状态写 启用/停用、
          导师写显示名；
        · 校招人数为**一次性聚合**（不做逐行 count，避免 N+1）。
        """
        qs = self.scope_queryset(RotationResource.objects.filter(deleted_at__isnull=True))
        rows = io_rotation_resource.build_export_rows(qs)
        wb = io_rotation_resource.build_export_workbook(rows)
        from apps.common.audit_helper import log_action
        log_action(
            self.request, 'EXPORT', 'RotationResource',
            new_value=f'导出轮岗资源 {len(rows)} 条（xlsx）',
        )
        return build_export_response(wb, 'rotation_resources_export.xlsx')

    @action(detail=False, methods=['get'], url_path='template')
    def template_resources(self, request):
        """下载轮岗资源导入模板（xlsx：说明区 + 表头 + 1 行示例）。

        GET /api/v1/campus-rotation/resources/template/?file_format=xlsx
        """
        wb, _header_row = io_rotation_resource.build_template_workbook()
        from apps.common.audit_helper import log_action
        log_action(self.request, 'EXPORT', 'RotationResource', new_value='下载轮岗资源导入模板（xlsx）')
        return build_export_response(wb, 'rotation_resources_template.xlsx')

    @action(detail=False, methods=['post'], url_path='import')
    def import_resources(self, request):
        """批量导入轮岗资源（xlsx）。

        POST /api/v1/campus-rotation/resources/import/   （multipart，字段名 file）

        · 按「资源编号」upsert：编号留空 = 新建（服务端按资源类型自动补 LR+4 / SD+4 / OT+4）；
        · 单行失败只跳过该行并记录原因，不中断整批；
        · 一行都没成功且存在错误行 → 400（data 内仍带 errors 与 errorFile）。
        """
        f = request.FILES.get('file')
        if not f:
            return Response(
                {'success': False, 'detail': '缺少 file 文件字段'}, status=400,
            )
        try:
            rows, errors, original_rows, errors_by_line = (
                io_rotation_resource.parse_import_workbook(f)
            )
        except (InvalidFileException, BadZipFile, OSError, ValueError, KeyError) as exc:
            return Response(
                {'success': False, 'detail': f'文件解析失败：{exc}'}, status=400,
            )

        created, updated, upsert_errors, upsert_errors_by_line = (
            io_rotation_resource.import_resources(
                rows, self.request.user,
                scope_qs=lambda qs: self.scope_queryset(qs),
            )
        )
        errors = list(errors) + list(upsert_errors)
        errors_by_line = {**errors_by_line, **upsert_errors_by_line}
        error_file = io_rotation_resource.build_error_report_base64(
            original_rows, errors_by_line,
        )

        # 未导入的行数 = 校验失败行 + scope 外 / 已删除跳过行（每行恰好一条错误消息）
        skipped = len(errors_by_line)
        if not rows and not errors:
            errors = ['文件中未解析到任何有效轮岗资源行']
        data = {
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'failed': len(errors),
            'errors': errors,
            'error_file': error_file,
        }
        from apps.common.audit_helper import log_action
        log_action(
            self.request, 'IMPORT', 'RotationResource',
            new_value=(
                f'导入轮岗资源：新建 {created} / 更新 {updated} / 跳过 {skipped} / 失败 {len(errors)}'
            ),
        )
        ok = (created + updated) > 0
        return Response(
            {'success': ok, 'data': data},
            status=200 if ok else 400,
        )

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
        # 2026-10-22：班长筛选（班级管理页新增）
        class_monitor = params.get('class_monitor')
        if class_monitor:
            qs = qs.filter(class_monitor_id=class_monitor)
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
        qs = self.scope_queryset(self.queryset.model.all_objects.filter(pk=pk))
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

    # 阶段分布三态（2026-10-22）：班级列表「阶段分布」列的下钻口径
    STAGE_MEMBERS_STAGES = {
        'PENDING': '待分配',
        'ONGOING': '轮岗中',
        'DONE': '已完成',
    }

    @action(detail=True, methods=['get'], url_path='stage-members')
    def stage_members(self, request, pk=None):
        """班级 × 阶段的轮岗安排明细（阶段分布列的下钻）。

        GET /api/v1/campus-rotation/class-rooms/{id}/stage-members/?stage=ONGOING

        · stage 必填，取值 PENDING(待分配) / ONGOING(轮岗中) / DONE(已完成)；
        · 返回该班级该阶段的轮岗安排（含校招生姓名/工号，解析不到时留空）。
        """
        instance = self.get_object()
        stage = (request.query_params.get('stage') or '').strip().upper()
        if stage not in self.STAGE_MEMBERS_STAGES:
            return Response(
                {'success': False, 'message': 'stage 只能是 PENDING / ONGOING / DONE'},
                status=400,
            )
        qs = RotationArrangement.objects.filter(
            class_room_id=instance.id, stage=stage, deleted_at__isnull=True,
        ).select_related('current_dept', 'mentor')
        arrangements = list(qs)

        # 校招生姓名/工号：优先 campus_person（人员级 nanoid），回退 person_id → Person.user_id
        # （一次批量解析，N+1 纪律；两套口径的键统一用 str，避免 int/str 混用取不到）
        from apps.campus_control.models import Person
        person_map = {}
        campus_person_ids = [a.campus_person_id for a in arrangements if a.campus_person_id]
        if campus_person_ids:
            for p in Person.objects.filter(id__in=campus_person_ids, deleted_at__isnull=True):
                person_map.setdefault(str(p.id), p)
        legacy_user_ids = [
            a.person_id for a in arrangements if a.person_id and not a.campus_person_id
        ]
        if legacy_user_ids:
            for p in Person.objects.filter(user_id__in=legacy_user_ids, deleted_at__isnull=True):
                person_map.setdefault(str(p.user_id), p)

        items = []
        for a in arrangements:
            person = person_map.get(str(a.campus_person_id or a.person_id))
            items.append({
                'arrangementId': str(a.id),
                'personId': str(person.id) if person else '',
                'personName': person.name if person else '',
                'employeeId': person.employee_id if person else '',
                'currentDept': a.current_dept.name if a.current_dept_id else '',
                'mentor': a.mentor.full_name if a.mentor_id else '',
                'rotationStart': a.rotation_start.isoformat() if a.rotation_start else '',
                'rotationEnd': a.rotation_end.isoformat() if a.rotation_end else '',
            })
        return Response({
            'success': True,
            'data': {
                'stage': stage,
                'stageLabel': self.STAGE_MEMBERS_STAGES[stage],
                'classRoomId': str(instance.id),
                'classRoomName': instance.name,
                'total': len(items),
                'items': items,
            },
        })


# ---------------------------------------------------------------------------
# BU 汇总（需求 4-1，S5-14）：直播 / 客服 / 其他 / 总数据 四段式
# ---------------------------------------------------------------------------
class ResourceBuSummaryView(APIView):
    """轮岗资源按 BU 拆分的分段式汇总。

    端点：GET /api/v1/campus-rotation/resources/bu-summary/
    分段：live（直播间占用）/ service（客服部门占用）/ other（其他类型占用）/ total（总数据）。

    ⚠️ 2026-10-22 兵哥指令「直播间 + 客服部门整合为轮岗资源」后，本端点从
    「扫两张表」改为「扫一张表 + 按 resource_type 分段」：
      - 数据源统一为 `RotationResource`（原来分别是 LiveRoom / ServiceDept）；
      - 占用口径统一为**资源级**（`RotationArrangement.resource_id` + ONGOING），
        原来直播间按「归属部门」统计、客服部门按「资源」统计，两套口径混用；
      - 新增 `other` 段（OTHER 类型资源），避免非直播间/客服部门的资源在汇总里消失。

    性能纪律（MEMORY.md N+1）：占用数用一条 values().annotate(Count()) 分组查询，
    严禁逐 BU / 逐资源循环查询。

    口径：
      - count：该 BU 下**该类型**资源的 ONGOING 占用合计。
      - capacity：该 BU 下**该类型**资源的 capacity 合计（空值按 0）。
      - usedRate：count / capacity；capacity 为 0 → null（防除零）。

    行级隔离：复用 scope_filter_q(scope_field='bu', entity='campus_resource')，
    仅聚合当前用户可见 BU 的资源。
    """

    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:resource:list'
    data_perm_entity = 'campus_resource'
    scope_field = 'bu'

    # 分段定义：(资源类型, 段键, 段内计数字段名)
    SEGMENTS = (
        ('LIVE_ROOM', 'live', 'anchorCount'),
        ('SERVICE_DEPT', 'service', 'csCount'),
        ('OTHER', 'other', 'otherCount'),
    )

    def get(self, request):
        user = request.user

        # 1) 可见资源（已套行级隔离）
        resources = list(
            RotationResource.objects.filter(
                scope_filter_q(user, scope_field='bu', entity='campus_resource')
            ).values('id', 'bu_id', 'capacity', 'resource_type')
        )

        # 2) ONGOING 占用分组（一条聚合查询，禁 N+1）
        occ = dict(
            RotationArrangement.objects.filter(
                stage='ONGOING', deleted_at__isnull=True,
            )
            .exclude(resource_id__isnull=True)
            .values_list('resource_id')
            .annotate(cnt=Count('id'))
        )

        # 3) 按 BU × 资源类型 聚合
        #    结构：{bu_id: {type: {'count': n, 'capacity': n}}}
        bu_agg: dict = {}
        for r in resources:
            slot = bu_agg.setdefault(r['bu_id'], {})
            cell = slot.setdefault(r['resource_type'], {'count': 0, 'capacity': 0})
            cell['count'] += occ.get(r['id'], 0)
            cell['capacity'] += r['capacity'] or 0

        # 4) BU 名称
        named_bu_ids = [b for b in bu_agg if b]
        buses = (
            {d.id: d.name for d in Department.objects.filter(id__in=named_bu_ids)}
            if named_bu_ids else {}
        )

        def rate(count: int, capacity: int):
            return (count / capacity) if capacity else None

        segments: dict = {}
        for resource_type, seg_key, count_field in self.SEGMENTS:
            rows = []
            for bu_id, slot in bu_agg.items():
                cell = slot.get(resource_type)
                if not cell:
                    continue
                name = buses.get(bu_id, '') if bu_id else '未分配'
                rows.append({
                    'buId': bu_id,
                    'buName': name,
                    count_field: cell['count'],
                    'capacity': cell['capacity'],
                    'usedRate': rate(cell['count'], cell['capacity']),
                })
            rows.sort(key=lambda x: (x['buId'] is None, x['buName']))
            segments[seg_key] = rows

        # 5) 总数据 + 涉及 BU 清单
        bu_list = [
            {'buId': bu_id, 'buName': (buses.get(bu_id, '') if bu_id else '未分配')}
            for bu_id in bu_agg
        ]
        bu_list.sort(key=lambda x: (x['buId'] is None, x['buName']))

        totals = {}
        for resource_type, seg_key, count_field in self.SEGMENTS:
            totals[seg_key] = sum(r[count_field] for r in segments[seg_key])

        data = {
            'live': segments['live'],
            'service': segments['service'],
            'other': segments['other'],
            'total': {
                'liveAnchorTotal': totals['live'],
                'serviceTotal': totals['service'],
                'otherTotal': totals['other'],
                'grandTotal': totals['live'] + totals['service'] + totals['other'],
                'buList': bu_list,
            },
        }
        return Response({'success': True, 'data': data})


# ---------------------------------------------------------------------------
# 统计概览（需求 4-x）：BG × 当前BU 的多维测算表
# ---------------------------------------------------------------------------
def _dept_org_names(dept):
    """把一个部门解析成 (BG 名, BU 名)。

    口径（与 `apps.core.dept_depth` 一致，0 基层级）：
    - BU  = 部门自身或其深度 2 祖先（`bu_ancestor`）
    - BG  = 部门自身或其深度 1 祖先（事业群层）

    ⚠️ 返回的 BG/BU 名来自**部门树**命名空间，而统计概览的行粒度取自
    **校招生档案**（`Person.bu` / `Person.intent_bu`）命名空间 —— 两者是
    两套名字（部门树是「能良 / 醒市」，档案是「能电BG / 三到BG」），
    按名字 join 不上。故需求侧按「BU 名 → BG 名 → 未分配」三级兜底归集，
    归不上的落到「未分配」行并在响应里回报数量，**不静默丢弃**。
    """
    if dept is None:
        return '', ''
    bu = bu_ancestor(dept)
    bg = bg_ancestor(dept)
    return (bg.name if bg else ''), (bu.name if bu else dept.name)


class ResourceStatsOverviewView(APIView):
    """轮岗资源 · 统计概览（BG × 当前BU 多维测算表）。

    端点：GET /api/v1/campus-rotation/resources/stats-overview/

    返回：{'rows': [...], 'totals': {...}, 'unassignedDemand': int}
    逐列口径见 `apps.campus_rotation.services.stats_overview` 模块头。

    行级隔离：三个数据源各按自己的实体口径过滤（人员 campus_person /
    轮岗安排 campus_arrangement / 需求 demand），任一未配置规则 → fail-open。
    """

    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:resource:list'
    data_perm_entity = 'campus_resource'
    scope_field = 'bu'

    def get(self, request):
        user = request.user

        # ── 1) 校招生档案（行粒度与人员类指标）──
        person_q = scope_filter_q(user, scope_field='head_teacher__department', entity='campus_person')
        persons_qs = Person.objects.all()
        if person_q is not None:
            persons_qs = persons_qs.filter(person_q)
        persons = [
            {
                'bg': p['bu'] or '',
                'bu': p['intent_bu'] or '',
                'sex': p['sex'] or '',
                'status': p['status'] or '',
                'onboarded': p['actual_entry_date'] is not None,
            }
            for p in persons_qs.values(
                'bu', 'intent_bu', 'sex', 'status', 'actual_entry_date'
            )
        ]

        # ── 2) 轮岗安排（已定岗 / 定岗流失 / 资源类型分布）──
        #    person_id 是 Person.user_id 口径（Person 主键是 nanoid），
        #    故按 user_id 批量取一次状态，避免逐条查（N+1）。
        uid_status = {
            p['user_id']: p['status']
            for p in Person.objects.filter(user_id__isnull=False).values('user_id', 'status')
        }

        arr_q = scope_filter_q(user, scope_field='current_dept', entity='campus_arrangement')
        arrangements_qs = RotationArrangement.objects.filter(deleted_at__isnull=True)
        if arr_q is not None:
            arrangements_qs = arrangements_qs.filter(arr_q)
        arrangement_rows = []
        for a in arrangements_qs.select_related('resource', 'campus_person').values(
            'intent_bu', 'final_dept', 'person_id',
            'resource__resource_type',
            'campus_person__status', 'campus_person__bu', 'campus_person__intent_bu',
        ):
            linked_status = a['campus_person__status'] or uid_status.get(a['person_id']) or ''
            # 组织维度跟人走（与行粒度同源）；人取不到时退回安排自身的意向 BU
            arrangement_rows.append({
                'bg': a['campus_person__bu'] or '',
                'bu': a['campus_person__intent_bu'] or a['intent_bu'] or '',
                'resource_type': a['resource__resource_type'] or '',
                'person_status': linked_status,
                'fixed': bool(a['final_dept']),
            })

        # ── 3) 校招需求（业务需求）──
        demand_q = scope_filter_q(user, scope_field='department', entity='demand')
        demands_qs = Demand.objects.filter(recruit_type='campus')
        if demand_q is not None:
            demands_qs = demands_qs.filter(demand_q)
        demand_rows = []
        dept_cache: dict = {}
        for d in demands_qs.values('department_id', 'headcount'):
            if d['department_id'] not in dept_cache:
                dept_cache[d['department_id']] = (
                    Department.objects.filter(id=d['department_id']).first()
                    if d['department_id'] else None
                )
            bg_name, bu_name = _dept_org_names(dept_cache[d['department_id']])
            demand_rows.append({
                'bg': bg_name,
                'bu': bu_name,
                'headcount': d['headcount'] or 0,
            })

        data = stats_overview.build_stats_overview(
            persons=persons,
            arrangements=arrangement_rows,
            demands=demand_rows,
        )
        return Response({'success': True, 'data': data})
