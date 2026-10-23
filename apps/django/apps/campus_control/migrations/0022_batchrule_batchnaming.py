"""批次规则引擎（契约 §4.2）—— 新增 BatchRule / BatchNaming 两张表。

## 背景

逆向自 workbuddy.link《校招生管理系统》演示环境的「批次规则」页（逆向清单 §4.4），
本仓原先**完全缺失**该能力：批次号只能靠 `campus_rotation.rules.batch_no` 的硬编码口径
（月中 15 号为界）生成，无法按「命名模板 + 区间 + 序号」重算，也无法按区间回填历史人员批次。

## 改动点

1. 新增 `BatchRule`（批次规则：批次号 + 中文名 + 入职日期区间 + 启停 + 排序）
   → `campus_batch_rules`；
2. 新增 `BatchNaming`（批次命名配置单例：模板 / 序号位数 / 起始值 / 循环粒度 / 判定依据）
   → `campus_batch_naming`；
3. **顺带承载** `constants.DEPTS` 扩档（7 档 BG）带来的 `choices` 漂移：
   `ControlRule.bu` / `Person.bu` / `Person.intent_bu` 三个字段的 choices 同步。
   ⚠️ 这三条 AlterField 并非本任务引入 —— DEPTS 扩档是校招生真实数据导入任务
   （聂荣口径，2026-10-23）的并行改动，模型与迁移必须同步落库，
   故一并由本迁移承载，避免出现「模型与迁移不一致」的漂移。

依赖：`campus_control.0021_person_class_monitor_personeducation`（**未覆盖**）。
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campus_control', '0021_person_class_monitor_personeducation'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='controlrule',
            name='bu',
            field=models.CharField(blank=True, choices=[('能电BG', '能电BG'), ('三到BG', '三到BG'), ('综合BG', '综合BG'), ('醒电BG', '醒电BG'), ('能人BG', '能人BG'), ('能智BG', '能智BG'), ('能本BG', '能本BG')], default='', max_length=16, verbose_name='部门'),
        ),
        migrations.AlterField(
            model_name='person',
            name='bu',
            field=models.CharField(choices=[('能电BG', '能电BG'), ('三到BG', '三到BG'), ('综合BG', '综合BG'), ('醒电BG', '醒电BG'), ('能人BG', '能人BG'), ('能智BG', '能智BG'), ('能本BG', '能本BG')], max_length=16, verbose_name='部门'),
        ),
        migrations.AlterField(
            model_name='person',
            name='intent_bu',
            field=models.CharField(blank=True, choices=[('能电BG', '能电BG'), ('三到BG', '三到BG'), ('综合BG', '综合BG'), ('醒电BG', '醒电BG'), ('能人BG', '能人BG'), ('能智BG', '能智BG'), ('能本BG', '能本BG')], default='', max_length=16, verbose_name='意向部门'),
        ),
        migrations.CreateModel(
            name='BatchNaming',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('template', models.CharField(default='{YY}{MM}{SEQ}', max_length=64, verbose_name='命名模板')),
                ('seq_width', models.PositiveIntegerField(default=2, verbose_name='序号位数')),
                ('seq_start', models.PositiveIntegerField(default=1, verbose_name='序号起始值')),
                ('cycle', models.CharField(choices=[('month', '每月归零'), ('year', '每年归零'), ('none', '全局递增')], default='month', max_length=16, verbose_name='序号循环粒度')),
                ('date_field', models.CharField(choices=[('entryDate', '入职日期'), ('hireDate', '录用日期')], default='entryDate', max_length=16, verbose_name='区间判定依据')),
                ('auto_apply', models.BooleanField(default=True, verbose_name='新增人员自动归属批次')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '批次命名配置',
                'verbose_name_plural': '批次命名配置',
                'db_table': 'campus_batch_naming',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='BatchRule',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('code', models.CharField(db_index=True, max_length=32, verbose_name='批次号')),
                ('name', models.CharField(max_length=64, verbose_name='批次名称')),
                ('start_date', models.DateField(verbose_name='区间开始日')),
                ('end_date', models.DateField(verbose_name='区间结束日')),
                ('enabled', models.BooleanField(default=True, verbose_name='启用')),
                ('sort', models.PositiveIntegerField(default=0, verbose_name='排序')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '批次规则',
                'verbose_name_plural': '批次规则',
                'db_table': 'campus_batch_rules',
                'ordering': ['sort', 'start_date', 'code'],
            },
        ),
    ]
