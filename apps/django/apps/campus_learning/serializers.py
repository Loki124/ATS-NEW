"""campus_learning 序列化器。

写时业务校验集中在这里：
- **可见范围**（契约 §1.3）：带人员的模型写入时校验目标校招生在当前用户可见范围内，
  否则导师可给「自己看不见的人」建记录（列表虽然收窄了，写入口却敞开 = 越权）。
- **考试通过判定**（契约 §3.2）：`ExamScore.passed` 由 `score >= exam.pass_score`
  服务端回算，`passed` 设为只读 → 前端传什么都不认。
- **活动奖励分值**（逆向清单 A6）：`reward` 是文本（「+3 分」），
  用 `parse_reward_points` 解析出整数，作为只读字段 `reward_points` 输出，
  供排名 / 附加分计算消费。
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.campus_control.visibility import visible_persons

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
    parse_reward_points,
)


class PersonVisibilityMixin:
    """写时可见范围校验（契约 §1.3 的写侧补齐）。"""

    def _validate_person_visible(self, person):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            return person
        if not visible_persons(user).filter(pk=person.pk).exists():
            raise serializers.ValidationError({'person': '该校招生不在你的可见范围内'})
        return person


class PersonNameMixin(serializers.Serializer):
    """校招生姓名（FK 本身只出 PK，前端列表要显示姓名）。

    ⚠️ 本 mixin **必须继承 `serializers.Serializer`**：DRF 的 `SerializerMetaclass`
    只从「带 `_declared_fields` 的基类」继承已声明字段（见 DRF 源码
    `_get_declared_fields`：`for base in bases if hasattr(base, '_declared_fields')`）。
    若 mixin 是普通 object 子类，`person_name` 这个 SerializerMethodField
    会被静默丢弃 → 序列化时 DRF 去找模型上的 person_name 字段 → 报
    "Field name `person_name` is not valid for model ..."（500）。
    """

    person_name = serializers.SerializerMethodField()

    def get_person_name(self, obj):
        return obj.person.name if obj.person_id else ''


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------
class CourseSerializer(serializers.ModelSerializer):
    """课程（管理端 CRUD）。"""

    class Meta:
        model = Course
        fields = [
            'id', 'code', 'name', 'form', 'duration_min', 'category', 'type',
            'exam_required', 'enabled', 'description', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ---------------------------------------------------------------------------
# LearnProgress
# ---------------------------------------------------------------------------
class LearnProgressSerializer(PersonVisibilityMixin, PersonNameMixin, serializers.ModelSerializer):
    """学习进度（一人一课一行；`done_at` 由服务端在首次满 100 时写入）。"""

    course_name = serializers.SerializerMethodField()

    class Meta:
        model = LearnProgress
        fields = [
            'id', 'person', 'person_name', 'course', 'course_name',
            'progress', 'minutes', 'done_at', 'last_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'done_at', 'last_at', 'created_at', 'updated_at']

    def get_course_name(self, obj):
        return obj.course.name if obj.course_id else ''

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        # 进度封顶 100（契约 §3.2 业务规则）——写入口就夹住，不靠调用方自觉。
        progress = attrs.get('progress')
        if progress is not None and progress > 100:
            raise serializers.ValidationError({'progress': '学习进度不能超过 100'})
        return attrs

    def create(self, validated_data):
        # 直写进度到 100 → 视为完成，写入 done_at（与 record 端点同一口径）。
        if validated_data.get('progress', 0) >= 100:
            validated_data.setdefault('done_at', timezone.now())
        validated_data.setdefault('last_at', timezone.now())
        return super().create(validated_data)

    def update(self, instance, validated_data):
        progress = validated_data.get('progress', instance.progress)
        if progress >= 100 and instance.done_at is None:
            validated_data['done_at'] = timezone.now()
        return super().update(instance, validated_data)


# ---------------------------------------------------------------------------
# LearnRecord
# ---------------------------------------------------------------------------
class LearnRecordSerializer(PersonVisibilityMixin, PersonNameMixin, serializers.ModelSerializer):
    """学习记录流水。"""

    course_name = serializers.SerializerMethodField()

    class Meta:
        model = LearnRecord
        fields = [
            'id', 'person', 'person_name', 'course', 'course_name',
            'date', 'start', 'minutes', 'remark', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_course_name(self, obj):
        return obj.course.name if obj.course_id else ''

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        return attrs


# ---------------------------------------------------------------------------
# Exam / ExamScore
# ---------------------------------------------------------------------------
class ExamSerializer(serializers.ModelSerializer):
    """考试。"""

    course_name = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            'id', 'name', 'date', 'form', 'full_score', 'pass_score',
            'course', 'course_name', 'enabled', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_course_name(self, obj):
        return obj.course.name if obj.course_id else ''

    def validate(self, attrs):
        full_score = attrs.get('full_score', getattr(self.instance, 'full_score', None))
        pass_score = attrs.get('pass_score', getattr(self.instance, 'pass_score', None))
        if full_score is not None and pass_score is not None and pass_score > full_score:
            raise serializers.ValidationError({'pass_score': '及格分不能高于满分'})
        return attrs


class ExamScoreSerializer(PersonVisibilityMixin, PersonNameMixin, serializers.ModelSerializer):
    """考试成绩。

    🔴 `passed` **只读**：由 `score >= exam.pass_score` 服务端判定（契约 §3.2
    「写入时算，不要信任前端传值」）。前端传 `passed` 会被 DRF 忽略。
    """

    exam_name = serializers.SerializerMethodField()

    class Meta:
        model = ExamScore
        fields = [
            'id', 'exam', 'exam_name', 'person', 'person_name',
            'score', 'passed', 'remark', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'passed', 'created_at', 'updated_at']

    def get_exam_name(self, obj):
        return obj.exam.name if obj.exam_id else ''

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        return attrs

    def _apply_passed(self, validated_data):
        """写入**前**回算通过判定：`score >= exam.pass_score`。

        必须在 save 之前算 —— 若先存后算，`passed` 只改了内存对象，库里仍是
        默认 False（跨请求读出来就成了「判错」）。这里直接塞进 validated_data，
        一次 INSERT/UPDATE 落库。
        """
        exam = validated_data.get('exam') or getattr(self.instance, 'exam', None)
        score = validated_data.get('score', getattr(self.instance, 'score', None))
        if exam is not None and score is not None:
            validated_data['passed'] = Decimal(score) >= Decimal(exam.pass_score)
        return validated_data

    def create(self, validated_data):
        return super().create(self._apply_passed(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._apply_passed(validated_data))


# ---------------------------------------------------------------------------
# Activity / ActivityScore
# ---------------------------------------------------------------------------
class ActivitySerializer(serializers.ModelSerializer):
    """活动（`reward_points` = 奖励文本解析出的整数分值，逆向清单 A6）。"""

    reward_points = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            'id', 'name', 'type', 'date', 'status', 'reward', 'reward_points',
            'rule', 'enabled', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'reward_points', 'created_at', 'updated_at']

    def get_reward_points(self, obj):
        return parse_reward_points(obj.reward)


class ActivityScoreSerializer(PersonVisibilityMixin, PersonNameMixin, serializers.ModelSerializer):
    """活动评分（`reward_points` 同上：文本 → 整数分值）。"""

    activity_name = serializers.SerializerMethodField()
    reward_points = serializers.SerializerMethodField()

    class Meta:
        model = ActivityScore
        fields = [
            'id', 'activity', 'activity_name', 'person', 'person_name',
            'score', 'reward', 'reward_points', 'rank', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'reward_points', 'created_at', 'updated_at']

    def get_activity_name(self, obj):
        return obj.activity.name if obj.activity_id else ''

    def get_reward_points(self, obj):
        return parse_reward_points(obj.reward)

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        return attrs


# ---------------------------------------------------------------------------
# ForumBoard / ForumPost
# ---------------------------------------------------------------------------
class ForumBoardSerializer(serializers.ModelSerializer):
    """论坛板块。"""

    class Meta:
        model = ForumBoard
        fields = [
            'id', 'name', 'description', 'sort', 'enabled',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ForumPostSerializer(serializers.ModelSerializer):
    """论坛帖。

    ⚠️ 论坛是**社区空间**：按逆向清单 §4.2「`myforum` 板块 + 帖子；全部角色可见」，
    帖子列表**不按校招生可见范围收窄**（否则外班学生看不到同校帖子，与原系统语义相反）。

    🔴 `author` / `person` 均由服务端决定（不信任前端传值）：
    `author` = 当前登录用户，`person` = 该登录用户自己的校招生档案（没有则留空）。
    """

    board_name = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ForumPost
        fields = [
            'id', 'board', 'board_name', 'title', 'content', 'author', 'author_name',
            'person', 'reply_count', 'pinned', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'reply_count', 'author', 'person', 'created_at', 'updated_at']

    def get_board_name(self, obj):
        return obj.board.name if obj.board_id else ''

    def get_author_name(self, obj):
        if not obj.author_id:
            return ''
        return obj.author.get_full_name() or obj.author.username or ''
