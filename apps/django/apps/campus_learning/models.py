"""校招学习与社区领域模型（campus_learning app）。

覆盖逆向清单 §4.2「培养管理」的五个视图：
- `courses`   课程管理（管理端：课程 / 形式 / 时长 / 分类 / 类型 / 结课考试 / 完成情况）
- `mycourses` 课程学习（学生端：进度 / 累计学习 / 学习龙虎榜）
- `exams`     考试管理（管理端：排名 / 得分条 / 成绩录入）/ `myexams` 考试认证
- `myactivity` 活动竞技（我的成绩 / 排名 / 奖励）
- `myforum`   交流论坛（板块 + 帖子）

统一基类 `FullAuditModel`（审计 + deleted_at 软删 + restore）+ `UUIDModel`（nanoid 主键）。
DELETE 走软删，不硬删。

🔴 **人员引用一律用字符串外键 `'campus_control.Person'`**：
跨 app 引用不 import models，避免 `campus_learning ↔ campus_control` 成环
（契约 §0「跨域只读引用 campus_control.Person，不互相 import models」）。

🔴 **不新建第二套人员主数据**：本 app 没有任何姓名字段，人员一律走 FK。
"""
import re
import unicodedata

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import FullAuditModel, UUIDModel

# ---------------------------------------------------------------------------
# 活动奖励分值解析（逆向清单 A6「附加分 = 活动奖励分值 + 历月加减分之和」）
# ---------------------------------------------------------------------------
#: 先找「带符号整数」（+3 分 / -2 分）——奖励分值的规范写法必带符号；
#: 找不到再退化为「第一个整数」（3 分 / 3分）；都没有 → 0。
_REWARD_SIGNED_RE = re.compile(r'([+-]\d+)')
_REWARD_PLAIN_RE = re.compile(r'(\d+)')


def parse_reward_points(text) -> int:
    """从活动奖励文本中解析整数分值（**纯函数**，无 DB / 无副作用）。

    逆向证据：逆向清单 §5 A6 —— 「附加分 = 活动奖励分值 + 历月加减分之和」
    （证据 `views2.js:88`）。而 `ActivityScore.reward` 存的是**文本**（形如
    「+3 分」），不是数字 → 参与附加分计算前必须先把文本解析成整数。

    解析口径（确定性优先，避免「排名第 1 名」里的 1 被误当成奖励）：
      1. NFKC 归一化（全角「＋3 分」「３分」「－2」→「+3 分」「3分」「-2」）；
      2. 取**第一个带符号整数**（`+3` / `-2`）——奖励分值的规范写法；
      3. 无带符号整数时取**第一个整数**（`3 分`）；
      4. 都没有（「无奖励」「一等奖」「」空串）→ 0。

    ⚠️ 本函数是跨 app 复用的**唯一真相源**：`campus_assessment` 的综合排名
    「附加分」维度（A6）需要同一套解析口径，故放在本模块（与 `reward` 字段同源），
    供 `from apps.campus_learning.models import parse_reward_points` 引用。
    """
    if text is None:
        return 0
    normalized = unicodedata.normalize('NFKC', str(text))
    matched = _REWARD_SIGNED_RE.search(normalized) or _REWARD_PLAIN_RE.search(normalized)
    if not matched:
        return 0
    return int(matched.group(1))


class Course(FullAuditModel, UUIDModel):
    """课程（逆向清单 §4.2 `courses` 课程管理）。

    管理端列：课程 / 形式 / 时长 / 分类 / 类型 / 结课考试 / 完成情况 / 操作。
    「完成情况」不在本表 —— 它是 `LearnProgress` 的聚合（完成人数 / 完成率），
    按 N+1 纪律在序列化器层算，不落库（与 `campus_rotation.RotationResource.campus_count` 同款做法）。
    """

    class Form(models.TextChoices):
        """课程形式（逆向清单原文：直播 / 录播 / 面授 / 线上）。"""

        LIVE = '直播', '直播'
        RECORDED = '录播', '录播'
        OFFLINE = '面授', '面授'
        ONLINE = '线上', '线上'

    class Type(models.TextChoices):
        """课程类型：必修 / 选修。"""

        REQUIRED = '必修', '必修'
        OPTIONAL = '选修', '选修'

    code = models.CharField(max_length=32, unique=True, verbose_name='课程编号')
    name = models.CharField(max_length=128, verbose_name='课程名称')
    form = models.CharField(
        max_length=16, choices=Form.choices, default=Form.LIVE,
        db_index=True, verbose_name='课程形式',
    )
    duration_min = models.PositiveIntegerField(default=0, verbose_name='时长(分钟)')
    category = models.CharField(max_length=32, blank=True, default='', db_index=True, verbose_name='分类')
    type = models.CharField(
        max_length=16, choices=Type.choices, default=Type.REQUIRED,
        db_index=True, verbose_name='课程类型',
    )
    exam_required = models.BooleanField(default=False, verbose_name='需结课考试')
    enabled = models.BooleanField(default=True, db_index=True, verbose_name='启用')
    description = models.TextField(blank=True, default='', verbose_name='课程说明')

    class Meta:
        db_table = 'campus_courses'
        verbose_name = '课程'
        verbose_name_plural = '课程'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'


class LearnProgress(FullAuditModel, UUIDModel):
    """学习进度（逆向清单 §4.2 `mycourses` 学生端「进度 / 累计学习」）。

    一人 × 一门课一行（唯一约束 person+course），是「学习龙虎榜」与
    考核域「学习成长维度」（逆向清单 A4）的唯一数据源。

    累加口径（由 `learn-progress/{id}/record/` 端点维护）：
      - `progress` 累加，**封顶 100**；
      - `minutes` 累加（累计学习分钟）；
      - `done_at` 在**首次**满 100 时写入（完成后不再刷新）。
    """

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='learn_progress', verbose_name='校招生',
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name='progress', verbose_name='课程',
    )
    progress = models.PositiveIntegerField(
        default=0, verbose_name='学习进度(%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    minutes = models.PositiveIntegerField(default=0, verbose_name='累计学习分钟')
    done_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    last_at = models.DateTimeField(default=timezone.now, verbose_name='最后学习时间')

    class Meta:
        db_table = 'campus_learn_progress'
        verbose_name = '学习进度'
        verbose_name_plural = '学习进度'
        ordering = ['-last_at']
        constraints = [
            models.UniqueConstraint(fields=['person', 'course'], name='uniq_learn_progress_person_course'),
        ]

    def __str__(self):
        return f'{self.person_id} / {self.course_id} = {self.progress}%'


class LearnRecord(FullAuditModel, UUIDModel):
    """学习记录（每次学习一条流水）。

    与 `LearnProgress` 的关系：`LearnProgress` 是**汇总**（进度 + 累计分钟），
    `LearnRecord` 是**流水**（哪天几点学了多少）。记学习记录时两者同时写
    （`learn-progress/{id}/record/`）。
    """

    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='learn_records', verbose_name='校招生',
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name='learn_records', verbose_name='课程',
    )
    date = models.DateField(db_index=True, verbose_name='学习日期')
    start = models.TimeField(null=True, blank=True, verbose_name='开始时间')
    minutes = models.PositiveIntegerField(default=0, verbose_name='学习分钟')
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'campus_learn_records'
        verbose_name = '学习记录'
        verbose_name_plural = '学习记录'
        ordering = ['-date', '-start']

    def __str__(self):
        return f'{self.person_id} / {self.course_id} / {self.date}'


class Exam(FullAuditModel, UUIDModel):
    """考试（逆向清单 §4.2 `exams` 考试管理 / `myexams` 考试认证）。

    管理端列：排名 / 校招生 / 班级 / 得分 / 结果 / 得分条 + 成绩录入。
    「得分条百分比」= `score / full_score * 100`（排名端点 `exams/{id}/ranking/` 输出）。
    """

    class Form(models.TextChoices):
        """考试形式：线上 / 线下。"""

        ONLINE = '线上', '线上'
        OFFLINE = '线下', '线下'

    name = models.CharField(max_length=128, verbose_name='考试名称')
    date = models.DateField(db_index=True, verbose_name='考试日期')
    form = models.CharField(
        max_length=16, choices=Form.choices, default=Form.OFFLINE,
        db_index=True, verbose_name='考试形式',
    )
    full_score = models.PositiveIntegerField(default=100, verbose_name='满分')
    pass_score = models.PositiveIntegerField(default=60, verbose_name='及格分')
    course = models.ForeignKey(
        Course, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='exams', verbose_name='关联课程',
    )
    enabled = models.BooleanField(default=True, db_index=True, verbose_name='启用')

    class Meta:
        db_table = 'campus_exams'
        verbose_name = '考试'
        verbose_name_plural = '考试'
        ordering = ['-date', 'name']

    def __str__(self):
        return self.name


class ExamScore(FullAuditModel, UUIDModel):
    """考试成绩（一人 × 一场考试一行，唯一约束 exam+person）。

    🔴 `passed` 由服务端按 `score >= exam.pass_score` **自动判定**（契约 §3.2），
    不信任前端传值 —— 序列化器层把 `passed` 设为只读并在写入时回算。
    """

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE,
        related_name='scores', verbose_name='考试',
    )
    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='exam_scores', verbose_name='校招生',
    )
    score = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='得分')
    passed = models.BooleanField(default=False, db_index=True, verbose_name='是否通过')
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'campus_exam_scores'
        verbose_name = '考试成绩'
        verbose_name_plural = '考试成绩'
        ordering = ['-score']
        constraints = [
            models.UniqueConstraint(fields=['exam', 'person'], name='uniq_exam_score_exam_person'),
        ]

    def __str__(self):
        return f'{self.exam_id} / {self.person_id} = {self.score}'


class Activity(FullAuditModel, UUIDModel):
    """活动（逆向清单 §4.2 `myactivity` 活动竞技）。

    活动列：活动名称 / 类型 / 日期 / 状态 / 我的成绩 / 排名 / 奖励 / 操作。
    `reward` 是**活动奖励的文本描述**（形如「+3 分」），参与综合排名「附加分」
    维度时按 `parse_reward_points` 解析成整数（逆向清单 A6）。
    """

    class Status(models.TextChoices):
        """活动状态：未开始 / 进行中 / 已结束。"""

        NOT_STARTED = '未开始', '未开始'
        ONGOING = '进行中', '进行中'
        FINISHED = '已结束', '已结束'

    name = models.CharField(max_length=128, verbose_name='活动名称')
    type = models.CharField(max_length=32, blank=True, default='', db_index=True, verbose_name='活动类型')
    date = models.DateField(db_index=True, verbose_name='活动日期')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.NOT_STARTED,
        db_index=True, verbose_name='活动状态',
    )
    reward = models.CharField(max_length=64, blank=True, default='', verbose_name='奖励说明')
    rule = models.TextField(blank=True, default='', verbose_name='活动规则')
    enabled = models.BooleanField(default=True, db_index=True, verbose_name='启用')

    class Meta:
        db_table = 'campus_activities'
        verbose_name = '活动'
        verbose_name_plural = '活动'
        ordering = ['-date', 'name']

    def __str__(self):
        return self.name


class ActivityScore(FullAuditModel, UUIDModel):
    """活动评分（逆向清单 §4.2 `myactivity`「我的成绩 / 排名 / 奖励」）。

    `reward` 同样是文本（形如「+3 分」）→ 附加分维度靠 `parse_reward_points` 解析。
    """

    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE,
        related_name='scores', verbose_name='活动',
    )
    person = models.ForeignKey(
        'campus_control.Person', on_delete=models.CASCADE,
        related_name='activity_scores', verbose_name='校招生',
    )
    score = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='活动得分')
    reward = models.CharField(max_length=64, blank=True, default='', verbose_name='奖励说明')
    rank = models.PositiveIntegerField(null=True, blank=True, verbose_name='名次')

    class Meta:
        db_table = 'campus_activity_scores'
        verbose_name = '活动评分'
        verbose_name_plural = '活动评分'
        ordering = ['-score']

    def __str__(self):
        return f'{self.activity_id} / {self.person_id} = {self.score}'


class ForumBoard(FullAuditModel, UUIDModel):
    """论坛板块（逆向清单 §4.2 `myforum`「板块 + 帖子」）。"""

    name = models.CharField(max_length=64, unique=True, verbose_name='板块名称')
    description = models.CharField(max_length=255, blank=True, default='', verbose_name='板块描述')
    sort = models.PositiveIntegerField(default=0, db_index=True, verbose_name='排序')
    enabled = models.BooleanField(default=True, db_index=True, verbose_name='启用')

    class Meta:
        db_table = 'campus_forum_boards'
        verbose_name = '论坛板块'
        verbose_name_plural = '论坛板块'
        ordering = ['sort', 'name']

    def __str__(self):
        return self.name


class ForumPost(FullAuditModel, UUIDModel):
    """论坛帖（逆向清单 §4.2 `myforum`「板块 + 帖子；全部角色可见」）。

    `author` 是发帖账号（core.User），`person` 是发帖人的**校招生档案**（可空，
    员工/导师发帖时没有校招生档案）。
    """

    board = models.ForeignKey(
        ForumBoard, on_delete=models.CASCADE,
        related_name='posts', verbose_name='板块',
    )
    title = models.CharField(max_length=128, verbose_name='标题')
    content = models.TextField(blank=True, default='', verbose_name='正文')
    author = models.ForeignKey(
        'core.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='发帖人',
    )
    person = models.ForeignKey(
        'campus_control.Person', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='forum_posts', verbose_name='校招生',
    )
    reply_count = models.PositiveIntegerField(default=0, verbose_name='回复数')
    pinned = models.BooleanField(default=False, db_index=True, verbose_name='置顶')

    class Meta:
        db_table = 'campus_forum_posts'
        verbose_name = '论坛帖'
        verbose_name_plural = '论坛帖'
        ordering = ['-pinned', '-created_at']

    def __str__(self):
        return self.title
