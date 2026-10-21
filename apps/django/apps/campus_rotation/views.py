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
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Count
from django_fsm import TransitionNotAllowed

from apps.common.pagination import StandardResultsSetPagination
from apps.core.models import Department
from apps.core.permissions_v2 import ScopeQuerysetMixin, V2Permission
from apps.core.scope_resolver import scope_filter_q
from apps.core.views_permission_v2 import EnvelopeWriteMixin
from django.db import IntegrityError

from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import (
    ClassRoom,
    ConcurrentPostRecord,
    LiveRoom,
    RotationApproval,
    RotationArrangement,
    RotationStage,
    ServiceDept,
)
from .serializers import (
    ClassRoomSerializer,
    ConcurrentPostRecordSerializer,
    LiveRoomSerializer,
    RotationApprovalSerializer,
    RotationArrangementSerializer,
    RotationStageSerializer,
    ServiceDeptSerializer,
)
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
        """批量调整轮岗安排信息（需求 5-3 / S5-18）。

        入参: {ids: [...], <字段>: <值>, ...}

        字段白名单（规格 §6.3）：
          current_dept / head_teacher / mentor / direct_manager /
          rotation_start / rotation_end / service_dept
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
            'rotation_start', 'rotation_end', 'service_dept',
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
        # FK 存在性（current_dept / service_dept）
        fk_instances = {}
        for fk_field, model in (('current_dept', Department), ('service_dept', ServiceDept)):
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
        ok = sync_concurrent_post(instance)
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
        from apps.campus_rotation.services.approval import ApprovalError, approve as do_approve

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
        from apps.campus_rotation.services.approval import ApprovalError, reject as do_reject

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


# ---------------------------------------------------------------------------
# BU 汇总（需求 4-1，S5-14）：直播 / 客服 / 总数据 三段式
# ---------------------------------------------------------------------------
class ResourceBuSummaryView(APIView):
    """轮岗资源按 BU 拆分的三段式汇总。

    端点：GET /api/v1/campus-rotation/resources/bu-summary/
    分段：live（直播主播占用）/ service（客服占用）/ total（总数据）。

    性能纪律（MEMORY.md N+1）：占用数用两条 values().annotate(Count()) 分组查询，
    严禁逐 BU / 逐资源循环查询。

    口径：
      - anchorCount：该 BU 下 LiveRoom 的 ONGOING 占用（复用 LiveRoomSerializer.campusCount
        的 `RotationArrangement.stage='ONGOING' AND current_dept_id=直播间.department_id`）。
      - csCount：该 BU 下 ServiceDept 的 ONGOING 占用（RotationArrangement.service_dept_id）。
      - capacity：资源 capacity 合计（空值按 0）。
      - usedRate：count / capacity；capacity 为 0 → null（防除零）。

    行级隔离：复用 scope_filter_q(scope_field='bu', entity='campus_resource')，
    仅聚合当前用户可见 BU 的资源。
    """

    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:resource:list'
    data_perm_entity = 'campus_resource'
    scope_field = 'bu'

    def get(self, request):
        user = request.user

        # 1) 可见资源（已套行级隔离）
        live_rooms = list(
            LiveRoom.objects.filter(
                scope_filter_q(user, scope_field='bu', entity='campus_resource')
            ).values('id', 'department_id', 'bu_id', 'capacity')
        )
        service_depts = list(
            ServiceDept.objects.filter(
                scope_filter_q(user, scope_field='bu', entity='campus_resource')
            ).values('id', 'bu_id', 'capacity')
        )

        live_dept_ids = [lr['department_id'] for lr in live_rooms if lr['department_id']]
        sd_ids = [sd['id'] for sd in service_depts]

        # 2) ONGOING 占用分组（两条聚合查询，禁 N+1）
        live_occ = {}
        if live_dept_ids:
            live_occ = dict(
                RotationArrangement.objects.filter(
                    stage='ONGOING', current_dept_id__in=live_dept_ids
                ).values_list('current_dept_id').annotate(cnt=Count('id'))
            )
        sd_occ = {}
        if sd_ids:
            sd_occ = dict(
                RotationArrangement.objects.filter(
                    stage='ONGOING', service_dept_id__in=sd_ids
                ).values_list('service_dept_id').annotate(cnt=Count('id'))
            )

        # 3) 按 BU 聚合
        bu_agg: dict = {}
        for lr in live_rooms:
            a = bu_agg.setdefault(
                lr['bu_id'],
                {'anchorCount': 0, 'liveCapacity': 0, 'csCount': 0, 'serviceCapacity': 0},
            )
            a['liveCapacity'] += lr['capacity'] or 0
            a['anchorCount'] += live_occ.get(lr['department_id'], 0)
        for sd in service_depts:
            a = bu_agg.setdefault(
                sd['bu_id'],
                {'anchorCount': 0, 'liveCapacity': 0, 'csCount': 0, 'serviceCapacity': 0},
            )
            a['serviceCapacity'] += sd['capacity'] or 0
            a['csCount'] += sd_occ.get(sd['id'], 0)

        # 4) BU 名称
        named_bu_ids = [b for b in bu_agg if b]
        bus = (
            {d.id: d.name for d in Department.objects.filter(id__in=named_bu_ids)}
            if named_bu_ids else {}
        )

        def rate(count: int, capacity: int):
            return (count / capacity) if capacity else None

        def build(bu_id):
            name = bus.get(bu_id, '') if bu_id else '未分配'
            return bu_id, name

        live, service, bu_list = [], [], []
        for bu_id, a in bu_agg.items():
            name = bus.get(bu_id, '') if bu_id else '未分配'
            bu_list.append({'buId': bu_id, 'buName': name})
            live.append({
                'buId': bu_id, 'buName': name,
                'anchorCount': a['anchorCount'],
                'capacity': a['liveCapacity'],
                'usedRate': rate(a['anchorCount'], a['liveCapacity']),
            })
            service.append({
                'buId': bu_id, 'buName': name,
                'csCount': a['csCount'],
                'capacity': a['serviceCapacity'],
                'usedRate': rate(a['csCount'], a['serviceCapacity']),
            })

        live.sort(key=lambda x: (x['buId'] is None, x['buName']))
        service.sort(key=lambda x: (x['buId'] is None, x['buName']))
        bu_list.sort(key=lambda x: (x['buId'] is None, x['buName']))

        live_anchor_total = sum(a['anchorCount'] for a in bu_agg.values())
        service_total = sum(a['csCount'] for a in bu_agg.values())

        data = {
            'live': live,
            'service': service,
            'total': {
                'liveAnchorTotal': live_anchor_total,
                'serviceTotal': service_total,
                'grandTotal': live_anchor_total + service_total,
                'buList': bu_list,
            },
        }
        return Response({'success': True, 'data': data})
