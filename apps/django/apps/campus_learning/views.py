"""campus_learning 视图集（校招学习与社区域）。

统一范式（照抄 `apps/campus_rotation/views.py` 的既有写法）：
- `EnvelopeWriteMixin`：写操作包 {success, data} 信封；
- `V2Permission`：资源级权限（按 action 派生读/写码）；
- `LearningCRUDMixin`：软删 + restore（复用 FullAuditModel.deleted_at）+ 审计埋点；
- `PersonScopedMixin`：行级数据隔离（契约 §1.3，走 `campus_control.visibility` 唯一真源）；
- `StandardResultsSetPagination`：仓库统一分页信封。

🔴 **行级隔离接入口径（勿改）**：
    `get_queryset()` 对**所有 action** 统一套可见范围，不是只对 list。
    原因：DRF 的 `get_object()` 复用 `get_queryset()`，若只对 list 收窄，
    retrieve/update/delete 会**完全绕过隔离** —— 导师只要猜到 id 就能改别人的
    学习进度 / 成绩（越权）。读写必须同源。

🔴 **权限码命名**：仓库 `V2Permission` 实际读取的属性名是 `permission_required_map`
    （契约 §1.2 写作 `permission_map`）。为同时满足契约命名与仓库运行时，
    两个属性都写：`permission_required_map` 生效，`permission_map` 是同值别名。
"""
import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Case, Count, IntegerField, Sum, When
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.campus_control.constants import STATUS as PERSON_STATUS
from apps.campus_control.visibility import visible_persons
from apps.common.audit_helper import log_action
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.core.permissions_v2 import V2Permission
from apps.core.views_permission_v2 import EnvelopeWriteMixin

from .models import (
    Activity,
    ActivityScore,
    Course,
    Exam,
    ExamScore,
    ForumBoard,
    ForumPost,
    LearnProgress,
    LearnRecord,
)
from .serializers import (
    ActivityScoreSerializer,
    ActivitySerializer,
    CourseSerializer,
    ExamScoreSerializer,
    ExamSerializer,
    ForumBoardSerializer,
    ForumPostSerializer,
    LearnProgressSerializer,
    LearnRecordSerializer,
)


#: 已离职人员的状态值。上游 `campus_control.constants.STATUS` 是人员状态枚举的
#: 唯一真源，这里取「离职」项 —— 不在本 app 另立一套状态枚举（契约 §1.1 禁止裸字符串）。
#: 上游若改名，`index()` 会直接抛 ValueError（导入期失败）而不是静默放行离职人员。
STATUS_PERSON_LEFT = PERSON_STATUS[PERSON_STATUS.index('离职')]


def _permission_map(submodule: str) -> dict:
    """按子模块生成写操作权限码映射（契约 §1.2）。

    动作码取仓库 `ACTION_WHITELIST` 语义：create / edit / delete。
    `restore` 归到 edit（恢复软删 = 改数据）。
    """
    return {
        'create': f'recruit:campus:{submodule}:create',
        'update': f'recruit:campus:{submodule}:edit',
        'partial_update': f'recruit:campus:{submodule}:edit',
        'destroy': f'recruit:campus:{submodule}:delete',
        'restore': f'recruit:campus:{submodule}:edit',
    }


class LearningCRUDMixin:
    """写操作统一：回填创建人 / 软删 / 审计埋点。

    照搬 `campus_rotation.views.CampusCRUDMixin`，DELETE 走**软删**
    （`FullAuditModel.deleted_at`），另补 `restore` 动作（契约 §1.1）。
    """

    def _audit_entity(self) -> str:
        """审计实体标识：优先用子类声明的 audit_entity，否则回退模型名。"""
        return getattr(self, 'audit_entity', self.queryset.model.__name__)

    def perform_create(self, serializer):
        try:
            instance = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})
        log_action(self.request, 'create', self._audit_entity(), instance.pk)

    def perform_update(self, serializer):
        try:
            instance = serializer.save(updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})
        log_action(self.request, 'update', self._audit_entity(), instance.pk)

    def perform_destroy(self, instance):
        pk = instance.pk
        instance.soft_delete()
        log_action(self.request, 'delete', self._audit_entity(), pk)

    def restore_queryset(self):
        """restore 取对象用的 queryset（含软删行）。

        默认取全量软删行；带人员的模型由 `PersonScopedMixin` 收窄到可见范围。
        """
        return self.queryset.model.all_objects.all()

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """恢复已软删的记录。

        取对象必须走**含软删行**的 manager（2026-10-21 卡 D3：默认 manager 已过滤
        `deleted_at`，改用 `all_objects`），否则对软删记录 restore 会 404。
        """
        instance = self.restore_queryset().filter(pk=pk).first()
        if instance is None:
            return Response({'success': False, 'message': '记录不存在或不在可见范围内'}, status=404)
        instance.restore()
        log_action(request, 'restore', self._audit_entity(), instance.pk)
        return success_response({'id': str(instance.id)})


class VisibilityScopeMixin:
    """行级数据隔离（契约 §1.3）：按当前用户可见人员范围收窄。

    可见范围统一走 `apps.campus_control.visibility.visible_persons`（唯一真源，
    与考核 / 定岗两个域共用），**不在本 app 复刻一套角色判断** —— 复刻必然漂移。

    🔴 **按模型是否有人员维度开关**（`visibility_person_field`）：
        - 课程 / 考试 / 活动 / 板块是**全局目录**（模型上根本没有 person 外键），
          若无差别地套 `person__in=...` 会直接抛 FieldError（模型无该字段）;
        - 论坛帖子是**社区空间**（逆向清单 §4.2「全部角色可见」），**不收窄**;
        - 学习进度 / 学习记录 / 考试成绩 / 活动评分才收窄。
      故默认值是 None（不收窄），由带人员维度的 ViewSet 显式声明。

    ⚠️ MRO 要求：本类必须排在 `LearningCRUDMixin` **之前**，
       否则 `restore_queryset` 的 `super()` 链会断（见 LearningViewSetBase 的基类顺序注释）。
    """

    #: 人员外键路径；None = 该模型无人员维度 → 不做可见范围收窄
    visibility_person_field = None

    def apply_filters(self, qs):
        """子类覆写：按 query 参数过滤。默认不过滤。"""
        return qs

    def apply_visibility(self, qs):
        """收窄到当前用户可见的校招生（无人员维度 → 原样返回）。"""
        field = self.visibility_person_field
        if not field:
            return qs
        return qs.filter(**{f'{field}__in': visible_persons(self.request.user)})

    def get_queryset(self):
        qs = super().get_queryset().filter(deleted_at__isnull=True)
        qs = self.apply_filters(qs)
        return self.apply_visibility(qs)

    def restore_queryset(self):
        """恢复软删行同样按可见范围收窄（无人员维度 → 原样返回）。"""
        qs = super().restore_queryset()
        field = self.visibility_person_field
        if not field:
            return qs
        return qs.filter(**{f'{field}__in': visible_persons(self.request.user)})


class LearningViewSetBase(
    EnvelopeWriteMixin, VisibilityScopeMixin, LearningCRUDMixin, viewsets.ModelViewSet
):
    """学习域 ViewSet 基类。

    ⚠️ 基类顺序不可调换：`VisibilityScopeMixin` 必须在 `LearningCRUDMixin` 之前，
       否则 `VisibilityScopeMixin.restore_queryset` 里的 `super()` 会跳过
       `LearningCRUDMixin.restore_queryset`（MRO 单调性）→ 恢复软删行时
       忘了过滤可见范围 → 可恢复他人范围的软删记录。
    """

    permission_classes = [V2Permission]
    pagination_class = StandardResultsSetPagination


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------
class CourseViewSet(LearningViewSetBase):
    """课程 CRUD（契约 §3.2 `courses/`，?type=&form=&enabled=）。

    课程是**全局目录**（不带人员维度）→ 不做可见范围收窄。
    """

    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_required = 'recruit:campus:course:list'
    permission_required_map = _permission_map('course')
    #: 契约 §1.2 的属性名别名（仓库运行时读的是 permission_required_map）
    permission_map = permission_required_map

    def apply_filters(self, qs):
        params = self.request.query_params
        for field in ('type', 'form'):
            value = params.get(field)
            if value:
                qs = qs.filter(**{field: value})
        enabled = params.get('enabled')
        if enabled in ('0', '1'):
            qs = qs.filter(enabled=enabled == '1')
        return qs


# ---------------------------------------------------------------------------
# LearnProgress / LearnRecord
# ---------------------------------------------------------------------------
class LearnProgressViewSet(LearningViewSetBase):
    """学习进度 CRUD + 记学习记录（契约 §3.2 `learn-progress/`）。"""

    queryset = LearnProgress.objects.all()
    serializer_class = LearnProgressSerializer
    permission_required = 'recruit:campus:course:list'
    permission_required_map = {**_permission_map('course'), 'record': 'recruit:campus:course:edit'}
    permission_map = permission_required_map
    audit_entity = 'LearnProgress'
    #: 带人员维度 → 列表 / 详情 / 恢复 均按可见范围收窄（契约 §1.3）
    visibility_person_field = 'person'

    def apply_filters(self, qs):
        params = self.request.query_params
        person = params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        course = params.get('course')
        if course:
            qs = qs.filter(course_id=course)
        return qs

    @action(detail=True, methods=['post'], url_path='record')
    def record(self, request, pk=None):
        """POST `learn-progress/{id}/record/` —— 记学习记录。

        口径（契约 §3.2「写 LearnRecord 并累加 progress/minutes」）：
          - `minutes` 必填：本次学习分钟数；
          - `progress` 可选：**本次进度增量**（百分点）。未传时按
            `minutes / course.duration_min * 100` 自动折算（课程时长为 0 时按 0 计）；
          - 累加后 `progress` **封顶 100**；**首次**满 100 时写入 `done_at`
            （已完成后不再刷新完成时间）；
          - `minutes` 累加，`last_at` 刷新到本次学习时刻；
          - 同时写一条 `LearnRecord` 流水（哪天几点学了多少）。

        取对象走 `self.get_object()` → 复用 `get_queryset()` → **已按可见范围收窄**，
        所以导师无法给看不见的人记学习记录。
        """
        progress = self.get_object()
        body = request.data or {}

        try:
            minutes = int(body.get('minutes') or 0)
        except (TypeError, ValueError):
            raise DRFValidationError({'minutes': '学习分钟数必须是整数'})
        if minutes <= 0:
            raise DRFValidationError({'minutes': '学习分钟数必须大于 0'})

        delta = self._resolve_progress_delta(body, progress.course, minutes)
        now = timezone.now()

        with transaction.atomic():
            new_progress = min(100, progress.progress + delta)
            new_minutes = progress.minutes + minutes
            # done_at 只在**首次**满 100 时写入（已完成的课程再学不刷新完成时间）
            done_at = progress.done_at
            if new_progress >= 100 and done_at is None:
                done_at = now
            progress.progress = new_progress
            progress.minutes = new_minutes
            progress.last_at = now
            if done_at is not None:
                progress.done_at = done_at
            progress.save(update_fields=['progress', 'minutes', 'last_at', 'done_at', 'updated_at'])

            record = LearnRecord.objects.create(
                person=progress.person,
                course=progress.course,
                date=self._parse_date(body.get('date')) or now.date(),
                start=self._parse_time(body.get('start')),
                minutes=minutes,
                remark=(body.get('remark') or '')[:255],
                created_by=request.user,
                updated_by=request.user,
            )

        log_action(request, 'create', 'LearnRecord', record.pk)
        log_action(request, 'update', 'LearnProgress', progress.pk)
        return success_response({
            'progress': LearnProgressSerializer(progress).data,
            'record': LearnRecordSerializer(record).data,
        })

    @staticmethod
    def _parse_date(raw):
        """解析 body 里的日期字符串（YYYY-MM-DD）；非法值 → 400 而不是 500。"""
        if not raw:
            return None
        try:
            return datetime.date.fromisoformat(str(raw))
        except ValueError:
            raise DRFValidationError({'date': '日期格式必须是 YYYY-MM-DD'})

    @staticmethod
    def _parse_time(raw):
        """解析 body 里的时间字符串（HH:MM 或 HH:MM:SS）；非法值 → 400 而不是 500。"""
        if not raw:
            return None
        try:
            return datetime.time.fromisoformat(str(raw))
        except ValueError:
            raise DRFValidationError({'start': '时间格式必须是 HH:MM'})

    @staticmethod
    def _resolve_progress_delta(body, course, minutes) -> int:
        """本次进度增量：body 显式传 `progress` 则用它，否则按课程时长自动折算。"""
        raw = body.get('progress')
        if raw is not None and raw != '':
            try:
                delta = int(raw)
            except (TypeError, ValueError):
                raise DRFValidationError({'progress': '进度增量必须是整数'})
            if delta < 0:
                raise DRFValidationError({'progress': '进度增量不能为负'})
            return delta
        duration = getattr(course, 'duration_min', 0) or 0
        if duration <= 0:
            return 0
        return int(round(minutes / duration * 100))


class LearnRecordViewSet(LearningViewSetBase):
    """学习记录 CRUD（契约 §3.2 `learn-records/`）。"""

    queryset = LearnRecord.objects.all()
    serializer_class = LearnRecordSerializer
    permission_required = 'recruit:campus:course:list'
    permission_required_map = _permission_map('course')
    permission_map = permission_required_map
    audit_entity = 'LearnRecord'
    visibility_person_field = 'person'

    def apply_filters(self, qs):
        params = self.request.query_params
        person = params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        course = params.get('course')
        if course:
            qs = qs.filter(course_id=course)
        return qs


# ---------------------------------------------------------------------------
# Exam / ExamScore
# ---------------------------------------------------------------------------
class ExamViewSet(LearningViewSetBase):
    """考试 CRUD + 考试排名（契约 §3.2 `exams/`、`exams/{id}/ranking/`）。

    考试是**全局目录**（不带人员维度）→ 列表不做可见范围收窄；
    但「排名」是**人的成绩** → 排名内容按可见范围收窄。
    """

    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_required = 'recruit:campus:exam:list'
    permission_required_map = _permission_map('exam')
    permission_map = permission_required_map
    audit_entity = 'Exam'

    def apply_filters(self, qs):
        params = self.request.query_params
        enabled = params.get('enabled')
        if enabled in ('0', '1'):
            qs = qs.filter(enabled=enabled == '1')
        course = params.get('course')
        if course:
            qs = qs.filter(course_id=course)
        return qs

    @action(detail=True, methods=['get'], url_path='ranking')
    def ranking(self, request, pk=None):
        """GET `exams/{id}/ranking/` —— 考试排名。

        口径（契约 §3.2「按分数降序 + 通过判定 + 得分条百分比」）：
          - 按 `score` 降序；**同分同名次**（竞赛式排名：1,1,3）；
          - `passed` = `score >= exam.pass_score`；
          - `percent` = `score / full_score * 100`（得分条百分比，1 位小数）；
          - 只统计当前用户**可见人员**的成绩。
        """
        exam = self.get_object()
        scores = (
            ExamScore.objects
            .filter(exam=exam, deleted_at__isnull=True)
            .filter(person__in=visible_persons(request.user))
            .select_related('person', 'person__class_room')
            .order_by('-score', 'person__name')
        )

        rows = []
        rank = 0
        prev_score = None
        for idx, item in enumerate(scores, start=1):
            score = Decimal(item.score)
            if prev_score is None or score != prev_score:
                rank = idx
            prev_score = score
            rows.append({
                'rank': rank,
                'person_id': item.person_id,
                'name': item.person.name,
                'class': item.person.class_room.name if item.person.class_room_id else '',
                'score': float(score),
                'passed': item.passed,
                'percent': round(float(score) / exam.full_score * 100, 1) if exam.full_score else 0.0,
            })
        return success_response(rows)


class ExamScoreViewSet(LearningViewSetBase):
    """考试成绩 CRUD（`passed` 由服务端回算，见 ExamScoreSerializer）。"""

    queryset = ExamScore.objects.all()
    serializer_class = ExamScoreSerializer
    permission_required = 'recruit:campus:exam:list'
    permission_required_map = _permission_map('exam')
    permission_map = permission_required_map
    audit_entity = 'ExamScore'
    visibility_person_field = 'person'

    def apply_filters(self, qs):
        params = self.request.query_params
        exam = params.get('exam')
        if exam:
            qs = qs.filter(exam_id=exam)
        person = params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        return qs


# ---------------------------------------------------------------------------
# Activity / ActivityScore
# ---------------------------------------------------------------------------
class ActivityViewSet(LearningViewSetBase):
    """活动 CRUD（活动是全局目录 → 不做可见范围收窄）。"""

    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    permission_required = 'recruit:campus:activity:list'
    permission_required_map = _permission_map('activity')
    permission_map = permission_required_map
    audit_entity = 'Activity'

    def apply_filters(self, qs):
        params = self.request.query_params
        status = params.get('status')
        if status:
            qs = qs.filter(status=status)
        type_ = params.get('type')
        if type_:
            qs = qs.filter(type=type_)
        enabled = params.get('enabled')
        if enabled in ('0', '1'):
            qs = qs.filter(enabled=enabled == '1')
        return qs


class ActivityScoreViewSet(LearningViewSetBase):
    """活动评分 CRUD（`reward_points` = 奖励文本解析出的整数分值，逆向清单 A6）。"""

    queryset = ActivityScore.objects.all()
    serializer_class = ActivityScoreSerializer
    permission_required = 'recruit:campus:activity:list'
    permission_required_map = _permission_map('activity')
    permission_map = permission_required_map
    audit_entity = 'ActivityScore'
    visibility_person_field = 'person'

    def apply_filters(self, qs):
        params = self.request.query_params
        activity = params.get('activity')
        if activity:
            qs = qs.filter(activity_id=activity)
        person = params.get('person')
        if person:
            qs = qs.filter(person_id=person)
        return qs


# ---------------------------------------------------------------------------
# ForumBoard / ForumPost
# ---------------------------------------------------------------------------
class ForumBoardViewSet(LearningViewSetBase):
    """论坛板块 CRUD（全局目录）。"""

    queryset = ForumBoard.objects.all()
    serializer_class = ForumBoardSerializer
    permission_required = 'recruit:campus:forum:list'
    permission_required_map = _permission_map('forum')
    permission_map = permission_required_map
    audit_entity = 'ForumBoard'

    def apply_filters(self, qs):
        params = self.request.query_params
        enabled = params.get('enabled')
        if enabled in ('0', '1'):
            qs = qs.filter(enabled=enabled == '1')
        return qs


class ForumPostViewSet(LearningViewSetBase):
    """论坛帖 CRUD（契约 §3.2 `forum-posts/`，?board=&kw=）。

    ⚠️ **不按校招生可见范围收窄**：逆向清单 §4.2「`myforum` 板块 + 帖子；
    **全部角色可见**」—— 论坛是社区空间，外班学生也要能看到同校帖子。
    若按人员范围收窄，会退化成「只有本班能看到本班帖」，与原系统语义相反。
    （实现：`visibility_person_field` 保持 None —— 基类据此跳过收窄。）

    🔴 写入口仍要防越权：**不能替别人发帖** —— `author` 固定为当前登录用户，
    `person`（发帖人的校招生档案）由服务端按登录用户反查，前端传什么都不认。
    """

    queryset = ForumPost.objects.all()
    serializer_class = ForumPostSerializer
    permission_required = 'recruit:campus:forum:list'
    permission_required_map = _permission_map('forum')
    permission_map = permission_required_map
    audit_entity = 'ForumPost'
    #: 论坛帖子不按人员范围收窄（逆向清单 §4.2「全部角色可见」）
    visibility_person_field = None

    def apply_filters(self, qs):
        params = self.request.query_params
        board = params.get('board')
        if board:
            qs = qs.filter(board_id=board)
        keyword = params.get('kw')
        if keyword:
            qs = qs.filter(title__icontains=keyword)
        return qs

    def perform_create(self, serializer):
        """发帖人 / 发帖人档案一律服务端决定（不信任前端传值）。"""
        from apps.campus_control.models import Person

        serializer.validated_data['author'] = self.request.user
        own_person = Person.objects.filter(
            user_id=self.request.user.pk, deleted_at__isnull=True,
        ).first()
        if own_person is not None:
            serializer.validated_data['person'] = own_person
        super().perform_create(serializer)


# ---------------------------------------------------------------------------
# 学习龙虎榜
# ---------------------------------------------------------------------------
class LearnBoardStatsView(APIView):
    """GET `stats/learn-board/` —— **学习龙虎榜**（契约 §3.2）。

    逆向证据 §4.2：学生端课程页「含**学习龙虎榜**（多维排名：学习分钟 / 完成数 /
    平均进度）」。

    输出每人一行：`{ id, name, class, minutes, done, avgProg, total }`
      - `minutes` 累计学习分钟（Σ LearnProgress.minutes）；
      - `done`    完成课程数（progress = 100 的课程数）；
      - `total`   参与学习的课程总数（`avgProg` 的分母，与 `done` 构成「完成数/总数」）；
      - `avgProg` 平均进度（Σ progress / total，1 位小数）。

    口径：
      - 按 `minutes` 降序（同分再按 done 降序、姓名升序，保证顺序稳定）；
      - **排除已离职人员**（`Person.status == '离职'`）—— 离职者不在培养中，不上榜；
      - 只统计**当前用户可见人员**（契约 §1.3）；
      - 无学习记录的人不上榜（`total = 0` 的行没有排名意义）。
    """

    permission_classes = [V2Permission]
    #: 纯 APIView 无 DRF action → 权限码按 HTTP method 匹配（见 V2Permission 说明）
    permission_required_map = {'get': 'recruit:campus:course:list'}

    def get(self, request):
        persons = (
            visible_persons(request.user)
            .exclude(status=STATUS_PERSON_LEFT)
            .select_related('class_room')
        )
        person_ids = list(persons.values_list('id', flat=True))

        aggregated = {
            row['person_id']: row
            for row in (
                LearnProgress.objects
                .filter(person_id__in=person_ids, deleted_at__isnull=True)
                .values('person_id')
                .annotate(
                    minutes=Sum('minutes'),
                    total=Count('id'),
                    done=Count(Case(When(progress__gte=100, then=1), output_field=IntegerField())),
                    progress_sum=Sum('progress'),
                )
            )
        }
        if not aggregated:
            return success_response([])

        name_map = {p.id: p.name for p in persons}
        class_map = {p.id: (p.class_room.name if p.class_room_id else '') for p in persons}

        rows = []
        for person_id, agg in aggregated.items():
            if person_id not in name_map:
                continue
            total = agg['total'] or 0
            rows.append({
                'id': person_id,
                'name': name_map.get(person_id, ''),
                'class': class_map.get(person_id, ''),
                'minutes': agg['minutes'] or 0,
                'done': agg['done'] or 0,
                'avgProg': round((agg['progress_sum'] or 0) / total, 1) if total else 0.0,
                'total': total,
            })

        rows.sort(key=lambda r: (-r['minutes'], -r['done'], r['name']))
        return success_response(rows)
