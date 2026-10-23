"""校招定岗与结算域视图（campus_placement）。

契约：`ARCH_校招生全生命周期移植_技术契约_2026-10-23.md` §4.3
逆向依据：`校招生管理_逆向功能清单与差距矩阵_2026-10-23.md` §4.3（六步撮合状态机）/ §4.4（定岗安排 / 交易结算）

🔴 **双选撮合六步状态机**（逆向清单 §4.3，本文件是它的编排层）：

    ① 校招生填报 N 个志愿      —— POST /applications/
       （N = 该批次 `SelectionFlow.wish_limit`，缺省继承全局默认 2）
    ② 撮合启动后：第一志愿推送至「岗位所属业务 BP」
       —— POST /selection-flows/（started=True, start_time=now）→ 自动推送
    ③ BP 录取 → 后续志愿自动释放（status=已释放）
       BP 放弃 → 下一志愿自动推送
       —— POST /applications/{id}/accept/ 与 /reject/
    ④ 两志愿均未被选 → 进入人才市场（status=人才市场），全员 BP 可选
       —— /reject/ 顺延不到下一志愿时自动置为人才市场
    ⑤ 仍未被选 → 班主任/管理员指定分配（channel=指定）
       —— POST /applications/{id}/assign/
    ⑥ 管理员发布双选结果
       —— POST /selection-flows/{id}/publish/

**岗位开放判定顺序**（逆向清单 §4.3，顺序固定不得调整）：
    审核状态 → 开放开关 → 发布范围(all/batch/intentDept) → 面向届数/班级 → 窗口期
    实现见 `_position_open_state()`。

**可见范围**：所有按人取数的列表端点统一走 `apps.campus_control.visibility.visible_persons`
（只读调用，不修改该模块）—— 班主任只见自己带的班、导师只见自己的徒弟、HRBP 只见归属范围、
校招生只见本人、超管全量。
"""
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.views import APIView

from apps.campus_control.visibility import visible_persons
from apps.common.mixins import SoftDeleteRestoreMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.common.views import EnvelopeWriteMixin
from apps.core.permission_check import has_perm
from apps.core.permissions_v2 import V2Permission

from .models import (
    DEFAULT_WISH_LIMIT,
    Bill,
    PlacementAssessment,
    PlacementGoal,
    PlacementMetric,
    PlacementRecord,
    PositionApplication,
    PositionDemand,
    PriceBid,
    PriceScheme,
    RevenueRecord,
    SelectionFlow,
)
from .serializers import (
    BillSerializer,
    PlacementAssessmentSerializer,
    PlacementGoalSerializer,
    PlacementMetricSerializer,
    PlacementRecordSerializer,
    PositionApplicationSerializer,
    PositionDemandSerializer,
    PriceBidSerializer,
    PriceSchemeSerializer,
    RevenueRecordSerializer,
    SelectionFlowSerializer,
)

#: 定岗域权限码（契约 §1.2；资源码登记由父会话统一落 core 迁移）
PERM_LIST = 'recruit:campus:placement:list'
PERM_CREATE = 'recruit:campus:placement:create'
PERM_EDIT = 'recruit:campus:placement:edit'
PERM_DELETE = 'recruit:campus:placement:delete'
PERM_PUBLISH = 'recruit:campus:placement:publish'
PERM_APPROVE = 'recruit:campus:placement:approve'
PERM_REJECT = 'recruit:campus:placement:reject'
PERM_ASSIGN = 'recruit:campus:placement:assign'
#: 定岗跟踪（独立子模块 `placement_track`，与父会话 core 迁移登记的码对齐）
PERM_TRACK_LIST = 'recruit:campus:placement_track:list'
PERM_TRACK_CREATE = 'recruit:campus:placement_track:create'
PERM_TRACK_EDIT = 'recruit:campus:placement_track:edit'
PERM_TRACK_DELETE = 'recruit:campus:placement_track:delete'
#: 交易与结算域权限码（父会话 core 迁移登记了 list / create / edit / export / import，
#: **未登记 delete** → 结算域的删除动作复用 edit 码，避免派生出一个未注册的码导致 403）
PERM_SETTLEMENT_LIST = 'recruit:campus:settlement:list'
PERM_SETTLEMENT_CREATE = 'recruit:campus:settlement:create'
PERM_SETTLEMENT_EDIT = 'recruit:campus:settlement:edit'
PERM_SETTLEMENT_DELETE = PERM_SETTLEMENT_EDIT


# ---------------------------------------------------------------------------
# 撮合状态机辅助
# ---------------------------------------------------------------------------
def _position_open_state(demand, person):
    """岗位开放判定（逆向清单 §4.3，判定顺序固定）。

    顺序：审核状态 → 开放开关 → 发布范围(all/batch/intentDept) → 面向届数/班级 → 窗口期。

    Args:
        demand: `PositionDemand`。
        person: `campus_control.Person`（可空）。

    Returns:
        (是否开放, 原因)。开放时原因为空串。
    """
    # ① 审核状态（待审核 / 已驳回 → 一律不开放）
    if demand.need_status not in (
        PositionDemand.NeedStatus.APPROVED,
        PositionDemand.NeedStatus.PUBLISHED,
    ):
        if demand.need_status == PositionDemand.NeedStatus.REJECTED:
            return False, '该岗位需求已被驳回'
        return False, '该岗位需求尚未通过审核'

    # ② 开放开关
    if not demand.open_enabled:
        return False, '该岗位未开放报名'

    # ③ 发布范围（all / batch / intentDept）
    if demand.scope_type == PositionDemand.ScopeType.BATCH:
        if demand.scope_batch and person is not None and person.batch != demand.scope_batch:
            return False, f'该岗位仅对「{demand.scope_batch}」批次开放'
    elif demand.scope_type == PositionDemand.ScopeType.INTENT_DEPT:
        depts = demand.scope_intent_depts or []
        # 「按意向部门」= 校招生**投递时的意向部门**（`Person.intent_bu`），
        # 不是当前轮岗部门（`Person.bu`）；意向部门为空时才回落当前部门。
        person_depts = set()
        if person is not None:
            person_depts = ({person.intent_bu} - {''}) or ({person.bu} - {''})
        if depts and person is not None and not (person_depts & set(depts)):
            return False, '该岗位不在你的意向部门范围内'

    # ④ 面向届数 / 班级（契约模型只有批次号字段，班级维度无字段承载 → 留白）
    if demand.open_batch_no and person is not None and person.batch != demand.open_batch_no:
        return False, f'该岗位仅面向「{demand.open_batch_no}」批次'

    # ⑤ 窗口期
    today = timezone.localdate()
    if demand.open_start and today < demand.open_start:
        return False, f'该岗位将于 {demand.open_start} 开放报名'
    if demand.open_end and today > demand.open_end:
        return False, f'该岗位已于 {demand.open_end} 截止报名'
    return True, ''


def _batch_flow(batch):
    """取批次的撮合流程（无则 None）。"""
    if not batch:
        return None
    return SelectionFlow.objects.filter(batch=batch).first()


def _wish_limit(batch):
    """该批次的志愿上限：批次覆盖优先，缺省继承全局默认 2（逆向清单 §4.3 ①）。"""
    flow = _batch_flow(batch)
    return flow.effective_wish_limit() if flow is not None else DEFAULT_WISH_LIMIT


def _push_application(app, user):
    """把一条志愿推送给岗位所属业务 BP（状态机 ②/③）。"""
    app.status = PositionApplication.Status.PUSHING
    app.pushed_at = timezone.now()
    app.pushed_by = user
    app.save(update_fields=['status', 'pushed_at', 'pushed_by', 'updated_at'])
    return app


def _release_other_applications(person, keep_id):
    """录取后释放该生的其余志愿（状态机 ③：后续志愿自动释放）。"""
    return PositionApplication.objects.filter(person=person).exclude(id=keep_id).filter(
        status__in=[
            PositionApplication.Status.FILED,
            PositionApplication.Status.PUSHING,
            PositionApplication.Status.MARKET,
        ]
    ).update(status=PositionApplication.Status.RELEASED, updated_at=timezone.now())


def _push_first_wishes(flow, user):
    """撮合启动后，把每个校招生的**第一志愿**推送给岗位所属业务 BP（状态机 ②）。

    只推送该批次内每人 `order` 最小、且仍处于「已填报」的志愿；已推送的不重复推送。
    """
    apps = (
        PositionApplication.objects.filter(person__batch=flow.batch)
        .filter(status=PositionApplication.Status.FILED)
        .select_related('position')
        .order_by('person_id', 'order')
    )
    pushed = []
    seen = set()
    for app in apps:
        if app.person_id in seen:
            continue
        seen.add(app.person_id)
        _push_application(app, user)
        pushed.append(app)
    return pushed


def _visible_person_ids(request):
    """当前用户可见的校招生 id（只读调用 campus_control.visibility）。"""
    return list(visible_persons(request.user).values_list('id', flat=True))


class CampusCRUDMixin:
    """写操作统一兜底：带入当前用户；软删（instance.soft_delete）；审计埋点。"""

    def _audit_entity(self) -> str:
        return getattr(self, 'audit_entity', self.queryset.model.__name__)

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        from apps.common.audit_helper import log_action
        log_action(self.request, 'create', self._audit_entity(), instance.pk)

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        from apps.common.audit_helper import log_action
        log_action(self.request, 'update', self._audit_entity(), instance.pk)

    def perform_destroy(self, instance):
        pk = instance.pk
        instance.soft_delete()
        from apps.common.audit_helper import log_action
        log_action(self.request, 'delete', self._audit_entity(), pk)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复软删行（契约 §1.1：软删模型须提供 restore 动作）。"""
        instance = self.get_object()
        instance.restore()
        return success_response({'id': instance.id})


# ---------------------------------------------------------------------------
# 岗位需求
# ---------------------------------------------------------------------------
class PositionDemandViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """岗位需求（契约 §4.3 `position-demands/`）。

    端点：CRUD + `review/`（审核）+ `open/`（开放报名）+ `withdraw/`（HRBP 撤回）+ `publish/`（发布）。
    """

    queryset = PositionDemand.objects.all()
    serializer_class = PositionDemandSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_LIST
    permission_required_map = {
        'create': PERM_CREATE,
        'update': PERM_EDIT,
        'partial_update': PERM_EDIT,
        'destroy': PERM_DELETE,
        'review': PERM_APPROVE,
        'publish': PERM_PUBLISH,
        'open': PERM_EDIT,
        'withdraw': PERM_EDIT,
        'restore': PERM_EDIT,
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = PositionDemand.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        need_status = (params.get('need_status') or '').strip()
        if need_status:
            qs = qs.filter(need_status=need_status)
        scope_type = (params.get('scope_type') or '').strip()
        if scope_type:
            qs = qs.filter(scope_type=scope_type)
        dept = (params.get('dept') or '').strip()
        if dept:
            qs = qs.filter(dept=dept)
        return qs

    @action(detail=True, methods=['post'], url_path='review')
    def review(self, request, pk=None):
        """需求审核：body `{ action: 'approve'|'reject', note }`。

        - approve → `need_status='已通过'`（需求码 `recruit:campus:placement:approve`）
        - reject  → `need_status='已驳回'`（额外校验 `recruit:campus:placement:reject` 码）

        ⚠️ 契约 §4.1 的 `PositionDemand` 无审核备注字段，`note` 原样回传给前端（不落库）。
        """
        demand = self.get_object()
        action_name = (request.data.get('action') or '').strip()
        note = request.data.get('note') or ''
        if action_name not in ('approve', 'reject'):
            raise ValidationError({'detail': '审核动作只能是 approve 或 reject'})
        if action_name == 'reject' and not has_perm(request.user, PERM_REJECT):
            raise PermissionDenied('没有驳回需求的权限')
        demand.need_status = (
            PositionDemand.NeedStatus.APPROVED if action_name == 'approve'
            else PositionDemand.NeedStatus.REJECTED
        )
        demand.save(update_fields=['need_status', 'updated_at'])
        return success_response({'need_status': demand.need_status, 'note': note})

    @action(detail=True, methods=['post'], url_path='open')
    def open(self, request, pk=None):
        """开放 / 关闭报名（`open_enabled`），可同时调整窗口期与面向批次。"""
        demand = self.get_object()
        data = request.data or {}
        if 'open_enabled' in data:
            demand.open_enabled = bool(data.get('open_enabled'))
        else:
            demand.open_enabled = not demand.open_enabled
        for field in ('open_start', 'open_end'):
            if field in data:
                setattr(demand, field, data.get(field) or None)
        if 'open_batch_no' in data:
            demand.open_batch_no = data.get('open_batch_no') or ''
        demand.save(update_fields=['open_enabled', 'open_start', 'open_end', 'open_batch_no', 'updated_at'])
        return success_response({
            'open_enabled': demand.open_enabled,
            'open_start': demand.open_start,
            'open_end': demand.open_end,
            'open_batch_no': demand.open_batch_no,
        })

    @action(detail=True, methods=['post'], url_path='withdraw')
    def withdraw(self, request, pk=None):
        """HRBP 撤回需求申请：状态回到「待审核」（可编辑后重新提交）。"""
        demand = self.get_object()
        demand.need_status = PositionDemand.NeedStatus.PENDING
        demand.open_enabled = False
        demand.save(update_fields=['need_status', 'open_enabled', 'updated_at'])
        return success_response({'need_status': demand.need_status})

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """发布岗位需求（`已通过` → `已发布`），发布后方可填报志愿。"""
        demand = self.get_object()
        if demand.need_status == PositionDemand.NeedStatus.PENDING:
            raise ValidationError({'detail': '需求尚未通过审核，不能发布'})
        if demand.need_status == PositionDemand.NeedStatus.REJECTED:
            raise ValidationError({'detail': '需求已被驳回，不能发布'})
        demand.need_status = PositionDemand.NeedStatus.PUBLISHED
        demand.save(update_fields=['need_status', 'updated_at'])
        return success_response({'need_status': demand.need_status})


# ---------------------------------------------------------------------------
# 志愿（双选撮合核心）
# ---------------------------------------------------------------------------
class PositionApplicationViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """志愿（契约 §4.3 `applications/`）。"""

    queryset = PositionApplication.objects.all()
    serializer_class = PositionApplicationSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_LIST
    permission_required_map = {
        'create': PERM_CREATE,
        'update': PERM_EDIT,
        'partial_update': PERM_EDIT,
        'destroy': PERM_DELETE,
        'push': PERM_EDIT,
        'accept': PERM_APPROVE,
        'reject': PERM_REJECT,
        'assign': PERM_ASSIGN,
        'restore': PERM_EDIT,
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = PositionApplication.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        person = (params.get('person') or '').strip()
        if person:
            qs = qs.filter(person_id=person)
        batch = (params.get('batch') or '').strip()
        if batch:
            qs = qs.filter(person__batch=batch)
        status = (params.get('status') or '').strip()
        if status:
            qs = qs.filter(status=status)
        # 可见范围收窄：只保留当前用户可见的校招生
        return qs.filter(person_id__in=_visible_person_ids(self.request))

    # -- 填报（状态机 ①）----------------------------------------------------
    def create(self, request, *args, **kwargs):
        """志愿填报（状态机 ①）：body `{ position_id, order }`（`person_id` 可选，管理员代填）。

        拦截口径：
        - 该批次撮合已启动 → **不可再修改志愿**（明确中文错误信息）；
        - 志愿条数超过该批次上限（wish_limit，缺省 2）；
        - 同一顺序重复填报 / 同一岗位重复填报；
        - 岗位未开放（按「审核状态 → 开放开关 → 发布范围 → 面向届数/班级 → 窗口期」判定）。
        """
        data = request.data or {}
        person = self._resolve_person(request, data.get('person_id'))
        if person is None:
            raise ValidationError({'detail': '未找到对应的校招生档案'})

        position_id = data.get('position_id')
        position = PositionDemand.objects.filter(id=position_id, deleted_at__isnull=True).first()
        if position is None:
            raise ValidationError({'detail': '岗位需求不存在'})

        try:
            order = int(data.get('order') or 1)
        except (TypeError, ValueError):
            raise ValidationError({'detail': '志愿顺序必须是数字'})

        batch = person.batch
        flow = _batch_flow(batch)
        # 撮合已启动 → 志愿冻结（逆向清单 §4.3「启动后校招生不可再改志愿」）
        if flow is not None and flow.started:
            raise ValidationError({'detail': '本批次双选撮合已启动，不能再修改志愿'})
        limit = flow.effective_wish_limit() if flow is not None else DEFAULT_WISH_LIMIT

        existing = PositionApplication.objects.filter(person=person, deleted_at__isnull=True)
        if existing.count() >= limit:
            raise ValidationError({'detail': f'本批次最多填报 {limit} 个志愿'})
        if order < 1 or order > limit:
            raise ValidationError({'detail': f'志愿顺序必须在 1 ~ {limit} 之间'})
        if existing.filter(order=order).exists():
            raise ValidationError({'detail': f'第 {order} 志愿已填报，请调整志愿顺序'})
        if existing.filter(position=position).exists():
            raise ValidationError({'detail': '该岗位已填报过志愿'})

        opened, reason = _position_open_state(position, person)
        if not opened:
            raise ValidationError({'detail': reason})

        app = PositionApplication.objects.create(
            person=person,
            position=position,
            order=order,
            channel=PositionApplication.Channel.WISH,
            status=PositionApplication.Status.FILED,
            created_by=request.user,
            updated_by=request.user,
        )
        return success_response(PositionApplicationSerializer(app).data, status_code=201)

    def _resolve_person(self, request, person_id):
        """解析志愿所属校招生。

        - 传了 `person_id` → 必须在当前用户可见范围内（学生只能填自己的）；
        - 没传 → 取当前登录用户绑定的校招生档案（`Person.user_id == user.pk`）。
        """
        visible = visible_persons(request.user)
        if person_id:
            return visible.filter(id=person_id).first()
        return visible.filter(user_id=request.user.pk).first()

    def _assert_wish_mutable(self, app):
        """撮合启动后志愿冻结（逆向清单 §4.3「启动后校招生不可再改志愿」）。"""
        flow = _batch_flow(app.person.batch)
        if flow is not None and flow.started:
            raise ValidationError({'detail': '本批次双选撮合已启动，不能再修改志愿'})

    def update(self, request, *args, **kwargs):
        """改志愿同样受「启动后冻结」约束（DRF 的 partial_update 内部也走 update）。"""
        self._assert_wish_mutable(self.get_object())
        return super().update(request, *args, **kwargs)

    # -- 推送 / 录取 / 放弃 / 指定分配 ---------------------------------------
    @action(detail=True, methods=['post'], url_path='push')
    def push(self, request, pk=None):
        """手动推送志愿给岗位所属业务 BP（状态机 ②）。"""
        app = self.get_object()
        if app.status != PositionApplication.Status.FILED:
            raise ValidationError({'detail': f'当前状态「{app.status}」不能推送'})
        _push_application(app, request.user)
        return success_response({'status': app.status, 'pushed_at': app.pushed_at})

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        """BP 录取（状态机 ③）：本条置「已录取」，该生的其余志愿自动「已释放」。

        人才市场态的志愿也可被任意 BP 录取（状态机 ④「全员 BP 可选」），
        此时可用 body `{ position_id }` 指定实际录用的岗位。
        """
        app = self.get_object()
        self._assert_bp_or_admin(request, app)
        if app.status not in (
            PositionApplication.Status.PUSHING,
            PositionApplication.Status.MARKET,
        ):
            raise ValidationError({'detail': f'当前状态「{app.status}」不能录取'})

        position_id = (request.data or {}).get('position_id')
        if position_id:
            target = PositionDemand.objects.filter(id=position_id, deleted_at__isnull=True).first()
            if target is None:
                raise ValidationError({'detail': '目标岗位需求不存在'})
            app.position = target

        with transaction.atomic():
            app.status = PositionApplication.Status.ACCEPTED
            app.decision = '接受'
            app.decided_at = timezone.now()
            app.save(update_fields=['position', 'status', 'decision', 'decided_at', 'updated_at'])
            _release_other_applications(app.person, app.id)
        return success_response({'status': app.status, 'decision': app.decision})

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """BP 放弃（状态机 ③）：本条置「已放弃」，**下一志愿自动推送**。

        若已无下一志愿（两志愿均未被选）→ 本条转入「人才市场」（状态机 ④），
        全员 BP 可选。
        """
        app = self.get_object()
        self._assert_bp_or_admin(request, app)
        if app.status != PositionApplication.Status.PUSHING:
            raise ValidationError({'detail': f'当前状态「{app.status}」不能放弃'})

        with transaction.atomic():
            app.status = PositionApplication.Status.REJECTED
            app.decision = '拒绝'
            app.decided_at = timezone.now()
            app.save(update_fields=['status', 'decision', 'decided_at', 'updated_at'])

            # 顺延：下一志愿（order 更大、仍「已填报」）自动推送给其岗位 BP
            nxt = (
                PositionApplication.objects.filter(person=app.person)
                .filter(status=PositionApplication.Status.FILED)
                .filter(order__gt=app.order)
                .order_by('order')
                .first()
            )
            if nxt is not None:
                _push_application(nxt, request.user)
            else:
                # 两志愿均未被选 → 人才市场（全员 BP 可选）
                app.status = PositionApplication.Status.MARKET
                app.save(update_fields=['status', 'updated_at'])
        return success_response({
            'status': app.status,
            'decision': app.decision,
            'next_pushed': bool(nxt),
        })

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """指定分配（状态机 ⑤，班主任 / 管理员）：body `{ position_id }`。

        落地：新建或更新一条 `channel='指定'`、`status='已录取'` 的志愿，
        并释放该生的其余志愿。
        """
        app = self.get_object()
        position_id = (request.data or {}).get('position_id')
        if not position_id:
            raise ValidationError({'detail': '请指定分配到的岗位需求'})
        target = PositionDemand.objects.filter(id=position_id, deleted_at__isnull=True).first()
        if target is None:
            raise ValidationError({'detail': '岗位需求不存在'})
        if target.need_status == PositionDemand.NeedStatus.REJECTED:
            raise ValidationError({'detail': '不能分配到已驳回的岗位需求'})

        with transaction.atomic():
            assigned = PositionApplication.objects.filter(
                person=app.person, position=target, deleted_at__isnull=True,
            ).first()
            if assigned is None:
                assigned = PositionApplication.objects.create(
                    person=app.person,
                    position=target,
                    order=app.order,
                    channel=PositionApplication.Channel.ASSIGNED,
                    status=PositionApplication.Status.ACCEPTED,
                    decision='接受',
                    decided_at=timezone.now(),
                    created_by=request.user,
                    updated_by=request.user,
                )
            else:
                assigned.channel = PositionApplication.Channel.ASSIGNED
                assigned.status = PositionApplication.Status.ACCEPTED
                assigned.decision = '接受'
                assigned.decided_at = timezone.now()
                assigned.save(update_fields=[
                    'channel', 'status', 'decision', 'decided_at', 'updated_at',
                ])
            _release_other_applications(app.person, assigned.id)
        return success_response({
            'id': assigned.id,
            'channel': assigned.channel,
            'status': assigned.status,
        })

    def _assert_bp_or_admin(self, request, app):
        """录取 / 放弃只能由该岗位的业务 BP（或管理员）操作。"""
        from apps.core.permission_check import is_super_admin

        if is_super_admin(request.user):
            return
        bp_id = app.position.bp_id if app.position_id else None
        if bp_id and bp_id != request.user.pk:
            raise PermissionDenied('只有该岗位的业务 BP 才能做此操作')


# ---------------------------------------------------------------------------
# 撮合流程
# ---------------------------------------------------------------------------
class SelectionFlowViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """撮合流程（按批次独立推进）。"""

    queryset = SelectionFlow.objects.all()
    serializer_class = SelectionFlowSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_LIST
    permission_required_map = {
        'create': PERM_EDIT,
        'update': PERM_EDIT,
        'partial_update': PERM_EDIT,
        'destroy': PERM_DELETE,
        'publish': PERM_PUBLISH,
        'restore': PERM_EDIT,
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = SelectionFlow.objects.filter(deleted_at__isnull=True)
        batch = (self.request.query_params.get('batch') or '').strip()
        if batch:
            qs = qs.filter(batch=batch)
        return qs

    def perform_create(self, serializer):
        """启动撮合（状态机 ②）。

        - body **显式**传 `started: false` → 建一条**待启动**流程
          （先定 `wish_limit`，让学生先填报，再启动 —— 顺序是 ① 填报 → ② 启动）；
        - 其余情况（不传 started，或传 true）→ `started=True` + `start_time=now`，
          并自动把每个校招生的第一志愿推送给岗位所属业务 BP。
        """
        want_started = serializer.validated_data.get('started', True)
        with transaction.atomic():
            instance = serializer.save(
                started=want_started,
                start_time=timezone.now() if want_started else None,
                created_by=self.request.user,
                updated_by=self.request.user,
            )
            if want_started:
                _push_first_wishes(instance, self.request.user)

    def perform_update(self, serializer):
        """把未启动的流程置为已启动时，同样触发第一志愿自动推送。"""
        instance = self.get_object()
        was_started = instance.started
        with transaction.atomic():
            updated = serializer.save(updated_by=self.request.user)
            if not was_started and updated.started:
                if not updated.start_time:
                    updated.start_time = timezone.now()
                    updated.save(update_fields=['start_time', 'updated_at'])
                _push_first_wishes(updated, self.request.user)

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """管理员发布双选结果（状态机 ⑥）。"""
        flow = self.get_object()
        if not flow.started:
            raise ValidationError({'detail': '撮合尚未启动，不能发布双选结果'})
        flow.published = True
        flow.published_at = timezone.now()
        flow.save(update_fields=['published', 'published_at', 'updated_at'])
        accepted = PositionApplication.objects.filter(
            person__batch=flow.batch, status=PositionApplication.Status.ACCEPTED,
        ).count()
        return success_response({
            'published': flow.published,
            'published_at': flow.published_at,
            'accepted_count': accepted,
        })


# ---------------------------------------------------------------------------
# 定岗跟踪
# ---------------------------------------------------------------------------
class PlacementRecordViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """定岗跟踪主表（子模块 `placement_track`，权限码与父会话登记的码对齐）。"""

    queryset = PlacementRecord.objects.all()
    serializer_class = PlacementRecordSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_TRACK_LIST
    permission_required_map = {
        'create': PERM_TRACK_CREATE, 'update': PERM_TRACK_EDIT,
        'partial_update': PERM_TRACK_EDIT, 'destroy': PERM_TRACK_DELETE,
        'restore': PERM_TRACK_EDIT,
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = PlacementRecord.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        dept = (params.get('dept') or '').strip()
        if dept:
            qs = qs.filter(dept=dept)
        status = (params.get('status') or '').strip()
        if status:
            qs = qs.filter(status=status)
        return qs.filter(person_id__in=_visible_person_ids(self.request))


class _PlacementChildViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """定岗子表（目标 / 数据 / 考核）公共基类：按所属定岗记录的校招生收窄可见范围。"""

    def get_queryset(self):
        return self.queryset.filter(deleted_at__isnull=True).filter(
            record__person_id__in=_visible_person_ids(self.request),
        )


class PlacementGoalViewSet(_PlacementChildViewSet):
    queryset = PlacementGoal.objects.all()
    serializer_class = PlacementGoalSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_TRACK_LIST
    permission_required_map = {
        'create': PERM_TRACK_CREATE, 'update': PERM_TRACK_EDIT,
        'partial_update': PERM_TRACK_EDIT, 'destroy': PERM_TRACK_DELETE,
        'restore': PERM_TRACK_EDIT,
    }
    pagination_class = StandardResultsSetPagination


class PlacementMetricViewSet(_PlacementChildViewSet):
    queryset = PlacementMetric.objects.all()
    serializer_class = PlacementMetricSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_TRACK_LIST
    permission_required_map = {
        'create': PERM_TRACK_CREATE, 'update': PERM_TRACK_EDIT,
        'partial_update': PERM_TRACK_EDIT, 'destroy': PERM_TRACK_DELETE,
        'restore': PERM_TRACK_EDIT,
    }
    pagination_class = StandardResultsSetPagination


class PlacementAssessmentViewSet(_PlacementChildViewSet):
    queryset = PlacementAssessment.objects.all()
    serializer_class = PlacementAssessmentSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_TRACK_LIST
    permission_required_map = {
        'create': PERM_TRACK_CREATE, 'update': PERM_TRACK_EDIT,
        'partial_update': PERM_TRACK_EDIT, 'destroy': PERM_TRACK_DELETE,
        'restore': PERM_TRACK_EDIT,
    }
    pagination_class = StandardResultsSetPagination


# ---------------------------------------------------------------------------
# 交易与结算
# ---------------------------------------------------------------------------
class PriceSchemeViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """定价方案（排名分档 → 单价 / 底价）。"""

    queryset = PriceScheme.objects.all()
    serializer_class = PriceSchemeSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_SETTLEMENT_LIST
    permission_required_map = {
        'create': PERM_SETTLEMENT_CREATE, 'update': PERM_SETTLEMENT_EDIT,
        'partial_update': PERM_SETTLEMENT_EDIT, 'destroy': PERM_SETTLEMENT_DELETE,
        'restore': PERM_SETTLEMENT_EDIT,
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = PriceScheme.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        type_ = (params.get('type') or '').strip()
        if type_:
            qs = qs.filter(type=type_)
        batch = (params.get('batch') or '').strip()
        if batch:
            qs = qs.filter(batch=batch)
        enabled = params.get('enabled')
        if enabled not in (None, ''):
            qs = qs.filter(enabled=str(enabled).lower() in ('1', 'true', 'yes'))
        return qs


class PriceBidViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """出价记录。"""

    queryset = PriceBid.objects.all()
    serializer_class = PriceBidSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_SETTLEMENT_LIST
    permission_required_map = {
        'create': PERM_SETTLEMENT_CREATE, 'update': PERM_SETTLEMENT_EDIT,
        'partial_update': PERM_SETTLEMENT_EDIT, 'destroy': PERM_SETTLEMENT_DELETE,
        'restore': PERM_SETTLEMENT_EDIT,
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return PriceBid.objects.filter(deleted_at__isnull=True).filter(
            person_id__in=_visible_person_ids(self.request),
        )


class RevenueRecordViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """输出台账。"""

    queryset = RevenueRecord.objects.all()
    serializer_class = RevenueRecordSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_SETTLEMENT_LIST
    permission_required_map = {
        'create': PERM_SETTLEMENT_CREATE, 'update': PERM_SETTLEMENT_EDIT,
        'partial_update': PERM_SETTLEMENT_EDIT, 'destroy': PERM_SETTLEMENT_DELETE,
        'restore': PERM_SETTLEMENT_EDIT,
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = RevenueRecord.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        ym = (params.get('ym') or '').strip()
        if ym:
            qs = qs.filter(ym=ym)
        output_dept = (params.get('output_dept') or '').strip()
        if output_dept:
            qs = qs.filter(output_dept=output_dept)
        return qs.filter(person_id__in=_visible_person_ids(self.request))


class BillViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """结算账单。"""

    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_SETTLEMENT_LIST
    permission_required_map = {
        'create': PERM_SETTLEMENT_CREATE, 'update': PERM_SETTLEMENT_EDIT,
        'partial_update': PERM_SETTLEMENT_EDIT, 'destroy': PERM_SETTLEMENT_DELETE,
        'restore': PERM_SETTLEMENT_EDIT,
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = Bill.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        period = (params.get('period') or '').strip()
        if period:
            qs = qs.filter(period=period)
        status = (params.get('status') or '').strip()
        if status:
            qs = qs.filter(status=status)
        return qs


class SettlementStatView(APIView):
    """GET `/api/v1/campus-placement/settlement/stat/` —— 收入统计。

    按 月份 / 输出部门 / 阶段 聚合「出勤 · 单价 · 金额」，返回明细行 + 合计。
    """

    permission_classes = [V2Permission]
    permission_required_map = {'get': PERM_SETTLEMENT_LIST}

    def get(self, request, *args, **kwargs):
        params = request.query_params
        qs = RevenueRecord.objects.filter(deleted_at__isnull=True)
        ym = (params.get('ym') or '').strip()
        if ym:
            qs = qs.filter(ym=ym)
        output_dept = (params.get('output_dept') or '').strip()
        if output_dept:
            qs = qs.filter(output_dept=output_dept)
        stage = (params.get('stage') or '').strip()
        if stage:
            qs = qs.filter(stage=stage)
        qs = qs.filter(person_id__in=_visible_person_ids(request))

        rows = (
            qs.values('ym', 'output_dept', 'stage')
            .annotate(
                attend_days=Sum('attend_days'),
                amount=Sum('amount'),
                unit_price=Sum('unit_price'),
                person_count=Count('id'),
            )
            .order_by('ym', 'output_dept', 'stage')
        )
        data = [
            {
                'ym': r['ym'],
                'output_dept': r['output_dept'],
                'stage': r['stage'],
                'attend_days': r['attend_days'] or 0,
                'person_count': r['person_count'],
                'unit_price': float(r['unit_price'] or 0),
                'amount': float(r['amount'] or 0),
            }
            for r in rows
        ]
        total_amount = sum(r['amount'] for r in data)
        total_attend = sum(r['attend_days'] for r in data)
        return success_response({'rows': data, 'total_amount': total_amount, 'total_attend_days': total_attend})


class SettlementPriceView(APIView):
    """GET `/api/v1/campus-placement/settlement/price/` —— 定价管理视图。

    返回全部启用中的定价方案（含排名分档 tiers）+ 默认方案。
    """

    permission_classes = [V2Permission]
    permission_required_map = {'get': PERM_SETTLEMENT_LIST}

    def get(self, request, *args, **kwargs):
        schemes = PriceScheme.objects.filter(deleted_at__isnull=True, enabled=True)
        default = schemes.filter(is_default=True).first() or schemes.first()
        data = PriceSchemeSerializer(schemes, many=True).data
        return success_response({
            'schemes': data,
            'default': PriceSchemeSerializer(default).data if default is not None else None,
        })
