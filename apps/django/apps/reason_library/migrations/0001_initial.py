"""Handwritten initial migration for reason_library (T02).

设计: 5 张表 + 全部 UNIQUE/INDEX/CHECK 在创建时一次落库。
不依赖 makemigrations 自动生成 — 因为跨表引用较多, 自动生成会引入
未期望的 ALTER 顺序。

注意: SQLite 默认不支持 CHECK 约束名变更, 这里使用 ``db_index=True``
+ ``unique=True`` 在 SQLite 上正常工作 (Django 在 SQLite 上将 unique=True
映射为 UNIQUE INDEX, CHECK 约束会写入 CREATE TABLE 但 SQLite 解析时跳过)。
"""
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------
        # 1) reason_tag
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name='ReasonTag',
            fields=[
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=32, unique=True, verbose_name='标签名')),
                ('code', models.CharField(editable=False, help_text='系统自动生成, 供开发在代码中引用 (如 R4fKq2xB9zW3)', max_length=24, unique=True, verbose_name='原因代码')),
                ('en_name', models.CharField(blank=True, default='', max_length=64, verbose_name='英文名')),
                ('tip', models.CharField(blank=True, default='', max_length=128, verbose_name='提示文案')),
                ('type', models.CharField(
                    choices=[('system', 'system'), ('custom', 'custom')],
                    default='custom', max_length=16, verbose_name='类型',
                )),
                ('enabled', models.BooleanField(default=True, verbose_name='启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True, on_delete=models.SET_NULL,
                    related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人',
                )),
            ],
            options={
                'verbose_name': '原因标签',
                'verbose_name_plural': '原因标签',
                'db_table': 'reason_tag',
                'ordering': ['type', 'name'],
            },
        ),
        migrations.AddIndex(
            model_name='reasontag',
            index=models.Index(fields=['type', 'enabled'], name='idx_rtag_type_enabled'),
        ),

        # ------------------------------------------------------------------
        # 2) scene_rule
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name='SceneRule',
            fields=[
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64, verbose_name='规则名')),
                ('is_system', models.BooleanField(db_index=True, default=False, verbose_name='系统预置')),
                ('enabled', models.BooleanField(db_index=True, default=True, verbose_name='启用')),
                ('description', models.CharField(blank=True, default='', max_length=200, verbose_name='描述')),
                ('max_selectable_tags', models.PositiveSmallIntegerField(default=5, help_text='用户在实际使用弹窗中最多可选的原因标签条数 (0 表示不限制)', verbose_name='可选标签上限')),
                ('modal_title', models.CharField(blank=True, default='', max_length=64, help_text='终端用户选择原因弹窗的标题文案 (空=使用默认文案「选择原因」)', verbose_name='弹窗标题')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '场景规则',
                'verbose_name_plural': '场景规则',
                'db_table': 'scene_rule',
                'ordering': ['-is_system', '-updated_at'],
            },
        ),

        # ------------------------------------------------------------------
        # 3) rule_category
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name='RuleCategory',
            fields=[
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=32, verbose_name='分类名')),
                ('order', models.IntegerField(default=0, verbose_name='排序')),
                ('allow_custom', models.BooleanField(default=False, verbose_name='允许业务自定义')),
                ('level', models.IntegerField(default=1, verbose_name='层级 1..4')),
                ('color', models.CharField(blank=True, default='', help_text='#RRGGBB; 空串=未自定义 (一级用默认色, 非一级继承所属一级分类颜色)', max_length=16, verbose_name='区块颜色')),
                ('parent', models.ForeignKey(
                    blank=True, null=True, on_delete=models.SET_NULL,
                    related_name='children', to='reason_library.rulecategory', verbose_name='父分类',
                )),
                ('rule', models.ForeignKey(
                    on_delete=models.CASCADE,
                    related_name='categories', to='reason_library.scenerule', verbose_name='所属规则',
                )),
            ],
            options={
                'verbose_name': '规则分类',
                'verbose_name_plural': '规则分类',
                'db_table': 'rule_category',
                'ordering': ['rule', 'parent__id', 'order'],
            },
        ),
        migrations.AddIndex(
            model_name='rulecategory',
            index=models.Index(fields=['rule', 'parent'], name='idx_rcat_rule_parent'),
        ),
        migrations.AddConstraint(
            model_name='rulecategory',
            constraint=models.CheckConstraint(
                condition=models.Q(level__gte=1) & models.Q(level__lte=4),
                name='ck_rcat_level_1_4',
            ),
        ),

        # ------------------------------------------------------------------
        # 4) category_assignment
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name='CategoryAssignment',
            fields=[
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('order', models.IntegerField(default=0, verbose_name='排序')),
                ('category', models.ForeignKey(
                    on_delete=models.CASCADE,
                    related_name='assignments', to='reason_library.rulecategory', verbose_name='分类',
                )),
                ('tag', models.ForeignKey(
                    on_delete=models.PROTECT,
                    related_name='category_assignments', to='reason_library.reasontag', verbose_name='标签',
                )),
            ],
            options={
                'verbose_name': '分类标签绑定',
                'verbose_name_plural': '分类标签绑定',
                'db_table': 'category_assignment',
                'ordering': ['category', 'order'],
            },
        ),
        migrations.AddConstraint(
            model_name='categoryassignment',
            constraint=models.UniqueConstraint(fields=('category', 'tag'), name='uniq_cat_tag'),
        ),

        # ------------------------------------------------------------------
        # 5) rule_scene_assignment
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name='RuleSceneAssignment',
            fields=[
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('scene', models.CharField(
                    choices=[
                        ('筛选不通过', '筛选不通过'),
                        ('取消面试', '取消面试'),
                        ('放入人才库', '放入人才库'),
                        ('淘汰', '淘汰'),
                        ('标记失败', '标记失败'),
                        ('邀约标注', '邀约标注'),
                    ],
                    max_length=32, verbose_name='场景',
                )),
                ('rule', models.ForeignKey(
                    on_delete=models.CASCADE,
                    related_name='scene_assignments', to='reason_library.scenerule', verbose_name='规则',
                )),
            ],
            options={
                'verbose_name': '规则场景引用',
                'verbose_name_plural': '规则场景引用',
                'db_table': 'rule_scene_assignment',
            },
        ),
        migrations.AddConstraint(
            model_name='rulesceneassignment',
            constraint=models.UniqueConstraint(fields=('scene',), name='uniq_scene'),
        ),
    ]
