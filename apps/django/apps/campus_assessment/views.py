"""campus_assessment 视图集。

范式（照抄 apps/campus_rotation/views.py 与 apps/campus_control/views.py）：
- `SoftDeleteRestoreMixin`：restore 动作能取到已软删行，但不绕过行级隔离；
- `EnvelopeWriteMixin`：写操作统一包 {success, data} 信封；
- `AuditMixin` / `SoftDeleteViewSetMixin`：写入带审计人、DELETE 走软删；
- `V2Permission`：资源级权限，按 action 派生读写码；
- `StandardResultsSetPagination`：统一分页。

🔴 **行级隔离接入口径（勿改）**：
    `get_queryset()` 对**所有 action**（不只 list）统一套可见范围 ——
    DRF 的 `get_object()` 复用 `get_queryset()`，若按 `if self.action != 'list'` 提前
    返回全表，retrieve/update/delete 会完全绕过隔离（带教导师猜到 id 就能改别人的记录）。
    可见范围统一走 `apps.campus_control.visibility.visible_persons`（契约 §1.3），
    **本 app 是该助手的只读调用方**，不修改它。

权限码族（契约 §1.2 / §5.3）：
- `recruit:campus:assessment:*`    月度考核 / 考核模板 / 五行五力 / 试用期 / 排名
- `recruit:campus:attendance:*`    每日打卡 / 月度考勤汇总
- `recruit:campus:monthly_report:*` 月报与评分
- `recruit:campus:feedback:*`      反馈记录

资源码本身由父会话统一登记到 `permission_resources` / `role_permission` /
`permission_templates`（契约 §1.2 末尾），本模块只引用正确码。
"""
from datetime import date as date_cls

from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import APIView

from apps.common.mixins import (
    AuditMixin,
    SoftDeleteRestoreMixin,
    SoftDeleteViewSetMixin,
)
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.core.permissions_v2 import V2Permission
from apps.core.views_permission_v2 import EnvelopeWriteMixin

from . import ranking as R
from . import services
from .models import (
    AssessmentTemplate,
    AttendanceMonthly,
    AttendanceRecord,
    FeedbackRecord,
    FiveForceScore,
    MonthlyAssessment,
    MonthlyReport,
    MonthlyReportScore,
    Probation,
)
from .serializers import (
    AssessmentTemplateSerializer,
    AttendanceMonthlySerializer,
    AttendanceRecordSerializer,
    FeedbackRecordSerializer,
    FiveForceScoreSerializer,
    MonthlyAssessmentSerializer,
    MonthlyReportScoreSerializer,
    MonthlyReportSerializer,
    ProbationSerializer,
)


class CampusAssessmentBaseViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, AuditMixin,
    SoftDeleteViewSetMixin, viewsets.ModelViewSet,
):
    """考核域 ViewSet 基类：统一权限声明位 / 分页 / 审计 / 软删。"""

    permission_classes = [V2Permission]
    pagination_class = StandardResultsSetPagination
    #: 审计实体标识（写进 AuditLog 的 entity 字段）
    audit_entity = 'campus_assessment'

    def _visible_person_ids(self):
        """当前用户可见的校招生 id（可见范围的**唯一**收窄入口）。"""
        return services.visible_person_ids(self.request.user)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删记录（契约 §1.1「提供 restore 动作」）。

        `SoftDeleteRestoreMixin` 让本动作下的 `get_object()` 能取到已软删行，
        同时保留可见范围过滤 —— 不会变成「全库可恢复」。
        """
        instance = self.get_object()
        instance.restore()
        return success_response(self.get_serializer(instance).data)


# ---------------------------------------------------------------------------
# 月度考核
# ---------------------------------------------------------------------------
class MonthlyAssessmentViewSet(CampusAssessmentBaseViewSet):
    """月度考核（契约 §2.2 `monthly-assessments/`）。

    筛选：`?ym=&person=&status=&class=`。
    动作：`check/`（核对通过 → 锁定当月并计入排名）、`adjust/`（加减分）。
    """

    queryset = MonthlyAssessment.objects.all()
    serializer_class = MonthlyAssessmentSerializer
    permission_required = 'recruit:campus:assessment:list'
    permission_required_map = {
        'check': 'recruit:campus:assessment:edit',
        'adjust': 'recruit:campus:assessment:edit',
        'restore': 'recruit:campus:assessment:edit',
    }

    def get_queryset(self):
        qs = MonthlyAssessment.objects.filter(deleted_at__isnull=True)
        qs = qs.filter(person_id__in=self._visible_person_ids())
        params = self.request.query_params
        ym = params.get('ym')
        if ym:
            qs = qs.filter(ym=ym)
        person = params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        status = params.get('status')
        if status:
            qs = qs.filter(status=status)
        class_filter = params.get('class')
        if class_filter:
            qs = qs.filter(person__in=services.filter_persons_by_class(
                services.visible_person_qs(self.request.user), class_filter))
        return qs.select_related('person', 'person__class_room', 'checked_by')

    @action(detail=True, methods=['post'], url_path='check')
    def check(self, request, pk=None):
        """核对通过：置 `status=checked` + 写核对人/时间，并**锁定当月**。

        锁定含义（逆向清单 §4.3「核对通过（锁定当月并计入排名）」）：
        核对后不可再改 KPI / 考试 / 加减分 —— 序列化器与 adjust 动作都会拦。
        """
        obj = self.get_object()
        if obj.status == MonthlyAssessment.Status.CHECKED:
            raise DRFValidationError({'detail': '该月已核对通过，无需重复核对'})
        obj.status = MonthlyAssessment.Status.CHECKED
        obj.checked_by = request.user
        obj.checked_at = timezone.now()
        obj.save(update_fields=['status', 'checked_by', 'checked_at', 'updated_at'])
        return success_response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='adjust')
    def adjust(self, request, pk=None):
        """加减分：body `{ "adjust": 3, "reason": "创新提案" }`。

        ⚠️ 加减分是**累计**语义（迟到 −1、创新提案 +3，逐条累加到同一条月度考核上）。
        """
        obj = self.get_object()
        if obj.status == MonthlyAssessment.Status.CHECKED:
            raise DRFValidationError({'detail': '该月已核对通过，不可再调整加减分'})
        value = request.data.get('adjust')
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise DRFValidationError({'adjust': '加减分必须是整数'})
        reason = str(request.data.get('reason') or '').strip()
        obj.adjust = (obj.adjust or 0) + value
        if reason:
            parts = [p for p in [obj.note, reason] if p]
            obj.note = '；'.join(parts)[:255]
        obj.save(update_fields=['adjust', 'note', 'updated_at'])
        return success_response(self.get_serializer(obj).data)


# ---------------------------------------------------------------------------
# 考核模板
# ---------------------------------------------------------------------------
class AssessmentTemplateViewSet(CampusAssessmentBaseViewSet):
    """考核模板（契约 §2.2 `assessment-templates/`，含 items 嵌套写入）。

    筛选：`?scope_type=&stage=&enabled=`。

    ⚠️ 模板是**配置数据**，不挂在任何校招生身上 → 无「可见人员」口径可套，
    访问控制完全由资源级权限码承担（与仓库其它配置类 ViewSet 一致）。
    """

    queryset = AssessmentTemplate.objects.all()
    serializer_class = AssessmentTemplateSerializer
    permission_required = 'recruit:campus:assessment:list'
    permission_required_map = {
        'restore': 'recruit:campus:assessment:edit',
    }

    def get_queryset(self):
        qs = AssessmentTemplate.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        scope_type = params.get('scope_type')
        if scope_type:
            qs = qs.filter(scope_type=scope_type)
        stage = params.get('stage')
        if stage:
            qs = qs.filter(stage=stage)
        enabled = params.get('enabled')
        if enabled is not None and enabled != '':
            qs = qs.filter(enabled=str(enabled).lower() in ('1', 'true', 'yes'))
        return qs.prefetch_related('items')


# ---------------------------------------------------------------------------
# 五行五力
# ---------------------------------------------------------------------------
class FiveForceScoreViewSet(CampusAssessmentBaseViewSet):
    """五行五力（契约 §2.2 `five-forces/`），筛选 `?person=`。"""

    queryset = FiveForceScore.objects.all()
    serializer_class = FiveForceScoreSerializer
    permission_required = 'recruit:campus:assessment:list'
    permission_required_map = {
        'restore': 'recruit:campus:assessment:edit',
    }

    def get_queryset(self):
        qs = FiveForceScore.objects.filter(deleted_at__isnull=True)
        qs = qs.filter(person_id__in=self._visible_person_ids())
        person = self.request.query_params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        return qs.select_related('person', 'person__class_room', 'scorer')


# ---------------------------------------------------------------------------
# 考勤
# ---------------------------------------------------------------------------
class AttendanceRecordViewSet(CampusAssessmentBaseViewSet):
    """每日打卡（契约 §2.2 `attendance-records/`），筛选 `?date_from=&date_to=&person=`。"""

    queryset = AttendanceRecord.objects.all()
    serializer_class = AttendanceRecordSerializer
    permission_required = 'recruit:campus:attendance:list'
    permission_required_map = {
        # ⚠️ 父会话 core/0051 给 `attendance` 子模块登记的是 list/create/edit/export，
        #    **没有 :delete** —— 若走默认派生（destroy → :delete），删除动作会被
        #    V2Permission 的 fail-closed 守卫拒掉（码未注册 → 拒绝写）。
        #    契约 §2.2 要求这些端点提供 CRUD，故显式把删除动作落到已登记的 :edit 上。
        #    待父会话补登 `recruit:campus:attendance:delete` 后可改回派生。
        'destroy': 'recruit:campus:attendance:edit',
        'restore': 'recruit:campus:attendance:edit',
    }

    def get_queryset(self):
        qs = AttendanceRecord.objects.filter(deleted_at__isnull=True)
        qs = qs.filter(person_id__in=self._visible_person_ids())
        params = self.request.query_params
        date_from = params.get('date_from')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        date_to = params.get('date_to')
        if date_to:
            qs = qs.filter(date__lte=date_to)
        person = params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        return qs.select_related('person', 'person__class_room')


class AttendanceMonthlyViewSet(CampusAssessmentBaseViewSet):
    """月度考勤汇总（契约 §2.2 `attendance-monthly/`），筛选 `?ym=`。"""

    queryset = AttendanceMonthly.objects.all()
    serializer_class = AttendanceMonthlySerializer
    permission_required = 'recruit:campus:attendance:list'
    permission_required_map = {
        'destroy': 'recruit:campus:attendance:edit',
        'restore': 'recruit:campus:attendance:edit',
    }

    def get_queryset(self):
        qs = AttendanceMonthly.objects.filter(deleted_at__isnull=True)
        qs = qs.filter(person_id__in=self._visible_person_ids())
        ym = self.request.query_params.get('ym')
        if ym:
            qs = qs.filter(ym=ym)
        return qs.select_related('person', 'person__class_room')


# ---------------------------------------------------------------------------
# 反馈记录
# ---------------------------------------------------------------------------
class FeedbackRecordViewSet(CampusAssessmentBaseViewSet):
    """反馈记录（契约 §2.2 `feedback-records/`），筛选 `?category=&status=&kw=&person=`。

    动作：`resolve/`（办结 → 已解决 + 处理人/处理时间）。
    """

    queryset = FeedbackRecord.objects.all()
    serializer_class = FeedbackRecordSerializer
    permission_required = 'recruit:campus:feedback:list'
    permission_required_map = {
        'resolve': 'recruit:campus:feedback:edit',
        'restore': 'recruit:campus:feedback:edit',
    }

    def get_queryset(self):
        qs = FeedbackRecord.objects.filter(deleted_at__isnull=True)
        qs = qs.filter(person_id__in=self._visible_person_ids())
        params = self.request.query_params
        category = params.get('category')
        if category:
            qs = qs.filter(category=category)
        status = params.get('status')
        if status:
            qs = qs.filter(status=status)
        person = params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        kw = (params.get('kw') or '').strip()
        if kw:
            # 搜索姓名·内容·分类（逆向清单 §4.3「搜索姓名·内容·分类」）
            qs = qs.filter(
                Q(content__icontains=kw)
                | Q(person__name__icontains=kw)
                | Q(type__icontains=kw)
            )
        return qs.select_related('person', 'person__class_room', 'reporter', 'handler')

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        """办结：`处理中` → `已解决`，记录处理人与处理时间。"""
        obj = self.get_object()
        if obj.status == FeedbackRecord.Status.CLOSED:
            raise DRFValidationError({'detail': '该记录已闭环，无需重复办结'})
        obj.status = FeedbackRecord.Status.RESOLVED
        obj.handler = request.user
        obj.handled_at = timezone.now()
        obj.save(update_fields=['status', 'handler', 'handled_at', 'updated_at'])
        return success_response(self.get_serializer(obj).data)


class MonthlyReportViewSet(CampusAssessmentBaseViewSet):
    """月报（契约 §2.2 `monthly-reports/`），筛选 `?ym=&person=&status=`。

    动作：`submit/`（提交）、`score/`（评分并回算综合分 A7）。
    """

    queryset = MonthlyReport.objects.all()
    serializer_class = MonthlyReportSerializer
    permission_required = 'recruit:campus:monthly_report:list'
    permission_required_map = {
        # 评分走 `:evaluate`（契约 §1.2 允许的 action 白名单含 evaluate，
        # 且父会话 core/0051 给 monthly_report 登记的正是 evaluate 码）。
        'score': 'recruit:campus:monthly_report:evaluate',
        'submit': 'recruit:campus:monthly_report:edit',
        # ⚠️ core/0051 未给 monthly_report 登记 :delete（登记的是 list/create/edit/evaluate），
        #    走默认派生会让删除动作被 fail-closed 拒掉 → 显式落到已登记的 :edit。
        'destroy': 'recruit:campus:monthly_report:edit',
        'restore': 'recruit:campus:monthly_report:edit',
    }

    def get_queryset(self):
        qs = MonthlyReport.objects.filter(deleted_at__isnull=True)
        qs = qs.filter(person_id__in=self._visible_person_ids())
        params = self.request.query_params
        ym = params.get('ym')
        if ym:
            qs = qs.filter(ym=ym)
        person = params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        status = params.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs.select_related('person', 'person__class_room').prefetch_related('scores')

    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        """提交月报：`draft` → `submitted`，写提交时间。"""
        obj = self.get_object()
        if obj.status != MonthlyReport.Status.DRAFT:
            raise DRFValidationError({'detail': '仅草稿状态的月报可提交'})
        obj.status = MonthlyReport.Status.SUBMITTED
        obj.submitted_at = timezone.now()
        obj.save(update_fields=['status', 'submitted_at', 'updated_at'])
        return success_response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='score')
    def score(self, request, pk=None):
        """评分：body `{ role, case, insight, problem, clarity, executable, comment }`。

        口径（逆向清单 A7 / core.js:258）：
        - 角色总分 = 5 子项之和；
        - 综合分 = `round(business.total×0.7 + growth.total×0.3, 1)`；
        - **两个角色都评分后**才置 `status=scored` —— 只评一个角色时综合分无解，
          此时保持 `submitted`，等另一角色补齐（见返回体 `pending` 字段）。
        """
        report = self.get_object()
        if report.status == MonthlyReport.Status.DRAFT:
            raise DRFValidationError({'detail': '月报尚未提交，不能评分'})

        role = str(request.data.get('role') or '')
        if role not in (MonthlyReportScore.Role.BUSINESS, MonthlyReportScore.Role.GROWTH):
            raise DRFValidationError({'role': '评分角色必须是 business 或 growth'})

        sub_items = {}
        for field in ('case', 'insight', 'problem', 'clarity', 'executable'):
            raw = request.data.get(field)
            try:
                value = float(raw) if raw is not None else 0.0
            except (TypeError, ValueError):
                raise DRFValidationError({field: '评分必须是数字'})
            if value < 0:
                raise DRFValidationError({field: '评分不能为负'})
            sub_items[field] = value

        total = R.report_role_total(**sub_items)
        score_row, _created = MonthlyReportScore.objects.update_or_create(
            report=report,
            role=role,
            defaults={
                **sub_items,
                'total': total,
                'scorer': request.user,
                'comment': str(request.data.get('comment') or ''),
                'scored_at': timezone.now(),
            },
        )

        existing = {s.role: s.total for s in MonthlyReportScore.objects.filter(report=report)}
        report.business_score = existing.get(MonthlyReportScore.Role.BUSINESS, 0)
        report.growth_score = existing.get(MonthlyReportScore.Role.GROWTH, 0)

        pending = []
        if MonthlyReportScore.Role.BUSINESS in existing and MonthlyReportScore.Role.GROWTH in existing:
            report.final_score = R.report_final_score(
                existing[MonthlyReportScore.Role.BUSINESS],
                existing[MonthlyReportScore.Role.GROWTH],
            )
            report.status = MonthlyReport.Status.SCORED
        else:
            for missing in (MonthlyReportScore.Role.BUSINESS, MonthlyReportScore.Role.GROWTH):
                if missing not in existing:
                    pending.append(missing)
            report.save(update_fields=[
                'business_score', 'growth_score', 'updated_at',
            ])
            return success_response({
                'report': self.get_serializer(report).data,
                'score': MonthlyReportScoreSerializer(score_row).data,
                'pending': pending,
                'message': '已保存该角色评分，等待另一角色评分后回算综合分',
            })

        report.save(update_fields=[
            'business_score', 'growth_score', 'final_score', 'status', 'updated_at',
        ])
        return success_response({
            'report': self.get_serializer(report).data,
            'score': MonthlyReportScoreSerializer(score_row).data,
            'pending': [],
        })


# ---------------------------------------------------------------------------
# 试用期
# ---------------------------------------------------------------------------
class ProbationViewSet(CampusAssessmentBaseViewSet):
    """试用期考核（契约 §2.2 `probations/`），筛选 `?person=`。

    动作：`decide/`（body `{ decision, note }`，decision ∈ 转正/延期转正/不合格）。
    """

    queryset = Probation.objects.all()
    serializer_class = ProbationSerializer
    permission_required = 'recruit:campus:assessment:list'
    permission_required_map = {
        'decide': 'recruit:campus:assessment:edit',
        'restore': 'recruit:campus:assessment:edit',
    }

    def get_queryset(self):
        qs = Probation.objects.filter(deleted_at__isnull=True)
        qs = qs.filter(person_id__in=self._visible_person_ids())
        person = self.request.query_params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        return qs.select_related('person', 'person__class_room', 'decided_by')

    @action(detail=True, methods=['post'], url_path='decide')
    def decide(self, request, pk=None):
        """试用期决策：写处理类型 / 决策人 / 决策时间 / 说明。"""
        obj = self.get_object()
        decision = str(request.data.get('decision') or '')
        if decision not in (
            Probation.Decision.CONFIRM, Probation.Decision.DELAY, Probation.Decision.REJECT,
        ):
            raise DRFValidationError({'decision': '处理类型必须是 转正 / 延期转正 / 不合格'})
        obj.decision = decision
        obj.decided_by = request.user
        obj.decided_at = timezone.now()
        obj.decision_note = str(request.data.get('note') or '')
        obj.save(update_fields=[
            'decision', 'decided_by', 'decided_at', 'decision_note', 'updated_at',
        ])
        return success_response(self.get_serializer(obj).data)


# ---------------------------------------------------------------------------
# 统计 / 排名（独立端点，非 ViewSet）
# ---------------------------------------------------------------------------
class BaseStatsView(APIView):
    """统计类端点基类：统一权限声明与信封。"""

    permission_classes = [V2Permission]
    permission_required = 'recruit:campus:assessment:list'


class DailyAttendanceRankingView(BaseStatsView):
    """当日打卡排名（契约 §2.2 `attendance-records/daily-ranking/`）。

    ⚠️ 该路径与 ViewSet 的 `attendance-records/<pk>/` 详情路由**同前缀**，
    而 DRF 的 pk 正则 `[^/.]+` 能匹配 "daily-ranking" → 必须排在 router.urls 之前
    （与 apps/campus_rotation/urls.py 的 bu-summary 同一个坑）。
    """

    permission_required = 'recruit:campus:attendance:list'

    def get(self, request):
        day = request.query_params.get('date')
        parsed = None
        if day:
            try:
                parsed = date_cls.fromisoformat(day)
            except ValueError:
                raise DRFValidationError({'date': '日期格式必须是 YYYY-MM-DD'})
            # Python 3.11+ 的 fromisoformat 也认「20260701」紧凑格式，
            # 但接口约定是 YYYY-MM-DD —— 回写校验，避免两种写法混用。
            if parsed.isoformat() != day:
                raise DRFValidationError({'date': '日期格式必须是 YYYY-MM-DD'})
        return success_response(services.daily_attendance_ranking(request.user, parsed))


class CompositeRankingView(BaseStatsView):
    """综合排名（契约 §2.2 `ranking/composite/`）。

    query：`?dim=comp|kpi|learn|force|add&ym=&class=`
    """

    def get(self, request):
        params = request.query_params
        data = services.composite_ranking(
            request.user,
            dim=params.get('dim') or 'comp',
            ym=params.get('ym') or None,
            class_filter=params.get('class') or None,
        )
        return success_response(data)


class TeacherRankingView(BaseStatsView):
    """班主任排名（契约 §2.2 `ranking/teacher/`）。"""

    def get(self, request):
        return success_response(services.teacher_ranking(request.user))


class StatsOverviewView(BaseStatsView):
    """4 卡统计 + 考勤汇总（契约 §2.2 `stats/overview/`）。"""

    def get(self, request):
        return success_response(services.stats_overview(request.user, ym=request.query_params.get('ym')))
