"""校招学习与社区域首批迁移（2026-10-23 校招生全生命周期移植 · 契约 §3.1）。

## 背景

逆向自《校招生管理系统》演示环境（25 视图 / 5 角色），其「培养管理」板块
（逆向清单 §4.2）包含 courses / mycourses / exams / myexams / myactivity / myforum
六个视图。本迁移把这一域落成 9 张表。

## 改动点

新增 9 张表（db_table 全部 `campus_` 前缀）：

| 模型 | db_table |
|---|---|
| Course 课程 | campus_courses |
| LearnProgress 学习进度 | campus_learn_progress |
| LearnRecord 学习记录 | campus_learn_records |
| Exam 考试 | campus_exams |
| ExamScore 考试成绩 | campus_exam_scores |
| Activity 活动 | campus_activities |
| ActivityScore 活动评分 | campus_activity_scores |
| ForumBoard 论坛板块 | campus_forum_boards |
| ForumPost 论坛帖 | campus_forum_posts |

## 为什么这样切分

- **人员引用一律走 `campus_control.Person` 外键**（跨 app 字符串引用，避免
  import 成环）—— 不建第二套人员主数据；
- **LearnProgress 单独成表**：一人 × 一门课一行（唯一约束 person+course），
  它是「学习龙虎榜」与考核域「学习成长维度」（逆向清单 A4）的唯一数据源；
- **LearnRecord 单独成表**：进度是汇总，流水是明细 —— 两者生命周期不同
  （流水只增不改，进度会累加 / 封顶）；
- **ActivityScore.reward 存文本**（形如「+3 分」）：奖励描述是运营自由文本，
  解析成整数由 `apps.campus_learning.models.parse_reward_points` 负责
  （逆向清单 A6 的附加分口径），不把解析结果冗余落库。

## 唯一约束

- LearnProgress: (person, course) —— 同一门课对同一人只留一行进度；
- ExamScore: (exam, person) —— 同一场考试对同一人只留一行成绩。
"""
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # 依赖 campus_control 现有的最新迁移（人员外键指向 campus_control.Person）。
        # ⚠️ campus_control 侧的批次规则迁移（0022_*）由该域的负责人生成，
        #    本迁移不依赖它 —— 依赖 0021 已足以保证建表顺序（FK 目标表存在即可）。
        ('campus_control', '0021_person_class_monitor_personeducation'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128, verbose_name='活动名称')),
                ('type', models.CharField(blank=True, db_index=True, default='', max_length=32, verbose_name='活动类型')),
                ('date', models.DateField(db_index=True, verbose_name='活动日期')),
                ('status', models.CharField(choices=[('未开始', '未开始'), ('进行中', '进行中'), ('已结束', '已结束')], db_index=True, default='未开始', max_length=16, verbose_name='活动状态')),
                ('reward', models.CharField(blank=True, default='', max_length=64, verbose_name='奖励说明')),
                ('rule', models.TextField(blank=True, default='', verbose_name='活动规则')),
                ('enabled', models.BooleanField(db_index=True, default=True, verbose_name='启用')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '活动',
                'verbose_name_plural': '活动',
                'db_table': 'campus_activities',
                'ordering': ['-date', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ActivityScore',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('score', models.DecimalField(decimal_places=2, default=0, max_digits=6, verbose_name='活动得分')),
                ('reward', models.CharField(blank=True, default='', max_length=64, verbose_name='奖励说明')),
                ('rank', models.PositiveIntegerField(blank=True, null=True, verbose_name='名次')),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scores', to='campus_learning.activity', verbose_name='活动')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_scores', to='campus_control.person', verbose_name='校招生')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '活动评分',
                'verbose_name_plural': '活动评分',
                'db_table': 'campus_activity_scores',
                'ordering': ['-score'],
            },
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=32, unique=True, verbose_name='课程编号')),
                ('name', models.CharField(max_length=128, verbose_name='课程名称')),
                ('form', models.CharField(choices=[('直播', '直播'), ('录播', '录播'), ('面授', '面授'), ('线上', '线上')], db_index=True, default='直播', max_length=16, verbose_name='课程形式')),
                ('duration_min', models.PositiveIntegerField(default=0, verbose_name='时长(分钟)')),
                ('category', models.CharField(blank=True, db_index=True, default='', max_length=32, verbose_name='分类')),
                ('type', models.CharField(choices=[('必修', '必修'), ('选修', '选修')], db_index=True, default='必修', max_length=16, verbose_name='课程类型')),
                ('exam_required', models.BooleanField(default=False, verbose_name='需结课考试')),
                ('enabled', models.BooleanField(db_index=True, default=True, verbose_name='启用')),
                ('description', models.TextField(blank=True, default='', verbose_name='课程说明')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '课程',
                'verbose_name_plural': '课程',
                'db_table': 'campus_courses',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='Exam',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128, verbose_name='考试名称')),
                ('date', models.DateField(db_index=True, verbose_name='考试日期')),
                ('form', models.CharField(choices=[('线上', '线上'), ('线下', '线下')], db_index=True, default='线下', max_length=16, verbose_name='考试形式')),
                ('full_score', models.PositiveIntegerField(default=100, verbose_name='满分')),
                ('pass_score', models.PositiveIntegerField(default=60, verbose_name='及格分')),
                ('enabled', models.BooleanField(db_index=True, default=True, verbose_name='启用')),
                ('course', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='exams', to='campus_learning.course', verbose_name='关联课程')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '考试',
                'verbose_name_plural': '考试',
                'db_table': 'campus_exams',
                'ordering': ['-date', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ForumBoard',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64, unique=True, verbose_name='板块名称')),
                ('description', models.CharField(blank=True, default='', max_length=255, verbose_name='板块描述')),
                ('sort', models.PositiveIntegerField(db_index=True, default=0, verbose_name='排序')),
                ('enabled', models.BooleanField(db_index=True, default=True, verbose_name='启用')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '论坛板块',
                'verbose_name_plural': '论坛板块',
                'db_table': 'campus_forum_boards',
                'ordering': ['sort', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ForumPost',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=128, verbose_name='标题')),
                ('content', models.TextField(blank=True, default='', verbose_name='正文')),
                ('reply_count', models.PositiveIntegerField(default=0, verbose_name='回复数')),
                ('pinned', models.BooleanField(db_index=True, default=False, verbose_name='置顶')),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='发帖人')),
                ('board', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='campus_learning.forumboard', verbose_name='板块')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('person', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='forum_posts', to='campus_control.person', verbose_name='校招生')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '论坛帖',
                'verbose_name_plural': '论坛帖',
                'db_table': 'campus_forum_posts',
                'ordering': ['-pinned', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LearnRecord',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('date', models.DateField(db_index=True, verbose_name='学习日期')),
                ('start', models.TimeField(blank=True, null=True, verbose_name='开始时间')),
                ('minutes', models.PositiveIntegerField(default=0, verbose_name='学习分钟')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learn_records', to='campus_learning.course', verbose_name='课程')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learn_records', to='campus_control.person', verbose_name='校招生')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '学习记录',
                'verbose_name_plural': '学习记录',
                'db_table': 'campus_learn_records',
                'ordering': ['-date', '-start'],
            },
        ),
        migrations.CreateModel(
            name='ExamScore',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('score', models.DecimalField(decimal_places=2, max_digits=6, verbose_name='得分')),
                ('passed', models.BooleanField(db_index=True, default=False, verbose_name='是否通过')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scores', to='campus_learning.exam', verbose_name='考试')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_scores', to='campus_control.person', verbose_name='校招生')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '考试成绩',
                'verbose_name_plural': '考试成绩',
                'db_table': 'campus_exam_scores',
                'ordering': ['-score'],
                'constraints': [models.UniqueConstraint(fields=('exam', 'person'), name='uniq_exam_score_exam_person')],
            },
        ),
        migrations.CreateModel(
            name='LearnProgress',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('progress', models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='学习进度(%)')),
                ('minutes', models.PositiveIntegerField(default=0, verbose_name='累计学习分钟')),
                ('done_at', models.DateTimeField(blank=True, null=True, verbose_name='完成时间')),
                ('last_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='最后学习时间')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress', to='campus_learning.course', verbose_name='课程')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learn_progress', to='campus_control.person', verbose_name='校招生')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '学习进度',
                'verbose_name_plural': '学习进度',
                'db_table': 'campus_learn_progress',
                'ordering': ['-last_at'],
                'constraints': [models.UniqueConstraint(fields=('person', 'course'), name='uniq_learn_progress_person_course')],
            },
        ),
    ]
