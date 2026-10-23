"""校招定岗与结算域 · 首版建表（契约 §4.1 的 11 张表）。

## 背景

契约 §4.1 定岗与结算域的完整数据模型：岗位需求 / 志愿 / 撮合流程 / 定岗跟踪（+目标·数据·考核）
/ 定价方案 / 出价 / 输出台账 / 结算账单。

## 改动点

- `campus_position_demands` 岗位需求（含发布范围三档与开放窗口）
- `campus_position_applications` 双选志愿（撮合状态机载体）
- `campus_selection_flows` 撮合流程（按批次独立推进）
- `campus_placement_records` 定岗跟踪（+ `campus_placement_goals` / `campus_placement_metrics`
  / `campus_placement_assessments` 三张子表）
- `campus_price_schemes` / `campus_price_bids` 定价方案与出价
- `campus_revenue_records` / `campus_bills` 输出台账与结算账单

跨 app 外键：人员一律指向 `campus_control.Person`（字符串外键，不 import 对方 models）。
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('campus_control', '0022_batchrule_batchnaming'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Bill',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('bill_no', models.CharField(max_length=32, unique=True, verbose_name='账单号')),
                ('business_dept', models.CharField(blank=True, default='', max_length=64, verbose_name='业务部门')),
                ('period', models.CharField(blank=True, db_index=True, default='', max_length=16, verbose_name='账期')),
                ('person_count', models.PositiveIntegerField(default=0, verbose_name='结算人数')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='金额')),
                ('status', models.CharField(choices=[('待确认', '待确认'), ('已确认', '已确认')], db_index=True, default='待确认', max_length=16, verbose_name='状态')),
                ('confirmed_at', models.DateTimeField(blank=True, null=True, verbose_name='确认时间')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '结算账单',
                'verbose_name_plural': '结算账单',
                'db_table': 'campus_bills',
                'ordering': ['-period', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PlacementRecord',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('dept', models.CharField(blank=True, default='', max_length=64, verbose_name='定岗部门')),
                ('position_name', models.CharField(blank=True, default='', max_length=64, verbose_name='岗位')),
                ('place_date', models.DateField(blank=True, null=True, verbose_name='定岗日期')),
                ('track_years', models.PositiveIntegerField(default=1, verbose_name='跟踪年数')),
                ('latest_perf', models.CharField(blank=True, default='', max_length=32, verbose_name='最近绩效')),
                ('status', models.CharField(choices=[('待跟踪', '待跟踪'), ('跟踪中', '跟踪中'), ('已结束', '已结束')], db_index=True, default='待跟踪', max_length=16, verbose_name='状态')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='placement_records', to='campus_control.person', verbose_name='校招生')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '定岗跟踪',
                'verbose_name_plural': '定岗跟踪',
                'db_table': 'campus_placement_records',
                'ordering': ['-place_date', 'person_id'],
            },
        ),
        migrations.CreateModel(
            name='PlacementMetric',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('ym', models.CharField(blank=True, db_index=True, default='', max_length=7, verbose_name='月份')),
                ('metric', models.CharField(blank=True, default='', max_length=64, verbose_name='指标')),
                ('actual_value', models.CharField(blank=True, default='', max_length=64, verbose_name='完成值')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='metrics', to='campus_placement.placementrecord', verbose_name='定岗记录')),
            ],
            options={
                'verbose_name': '定岗数据',
                'verbose_name_plural': '定岗数据',
                'db_table': 'campus_placement_metrics',
                'ordering': ['record_id', 'ym'],
            },
        ),
        migrations.CreateModel(
            name='PlacementGoal',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128, verbose_name='目标名称')),
                ('metric', models.CharField(blank=True, default='', max_length=64, verbose_name='衡量指标')),
                ('target_value', models.CharField(blank=True, default='', max_length=64, verbose_name='目标值')),
                ('weight', models.PositiveIntegerField(default=0, verbose_name='权重')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='截止日期')),
                ('status', models.CharField(blank=True, default='', max_length=16, verbose_name='状态')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='goals', to='campus_placement.placementrecord', verbose_name='定岗记录')),
            ],
            options={
                'verbose_name': '定岗目标',
                'verbose_name_plural': '定岗目标',
                'db_table': 'campus_placement_goals',
                'ordering': ['record_id', 'name'],
            },
        ),
        migrations.CreateModel(
            name='PlacementAssessment',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('period', models.CharField(blank=True, default='', max_length=32, verbose_name='考核周期')),
                ('score', models.DecimalField(decimal_places=2, default=0, max_digits=6, verbose_name='得分')),
                ('perf_level', models.CharField(blank=True, default='', max_length=16, verbose_name='绩效等级')),
                ('assessed_at', models.DateField(blank=True, null=True, verbose_name='评定日期')),
                ('comment', models.TextField(blank=True, default='', verbose_name='评语')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assessments', to='campus_placement.placementrecord', verbose_name='定岗记录')),
            ],
            options={
                'verbose_name': '定岗考核',
                'verbose_name_plural': '定岗考核',
                'db_table': 'campus_placement_assessments',
                'ordering': ['record_id', 'assessed_at'],
            },
        ),
        migrations.CreateModel(
            name='PositionDemand',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128, verbose_name='岗位名称')),
                ('dept', models.CharField(blank=True, default='', max_length=64, verbose_name='用人部门')),
                ('business_dept', models.CharField(blank=True, default='', max_length=64, verbose_name='业务部门')),
                ('headcount', models.PositiveIntegerField(default=1, verbose_name='需求人数')),
                ('need_status', models.CharField(choices=[('待审核', '待审核'), ('已通过', '已通过'), ('已驳回', '已驳回'), ('已发布', '已发布')], db_index=True, default='待审核', max_length=16, verbose_name='需求状态')),
                ('need_desc', models.TextField(blank=True, default='', verbose_name='需求描述')),
                ('biz_intro', models.TextField(blank=True, default='', verbose_name='业务介绍')),
                ('dept_intro', models.TextField(blank=True, default='', verbose_name='部门介绍')),
                ('assess_req', models.TextField(blank=True, default='', verbose_name='考核要求')),
                ('need_time', models.CharField(blank=True, default='', max_length=64, verbose_name='需求时间')),
                ('work_location', models.CharField(blank=True, default='', max_length=64, verbose_name='工作地点')),
                ('scope_type', models.CharField(choices=[('all', '全部'), ('batch', '按批次'), ('intentDept', '按意向部门')], default='all', max_length=16, verbose_name='发布范围')),
                ('scope_batch', models.CharField(blank=True, default='', max_length=32, verbose_name='发布范围批次')),
                ('scope_intent_depts', models.JSONField(default=list, verbose_name='发布范围部门列表')),
                ('open_enabled', models.BooleanField(default=False, verbose_name='开放报名')),
                ('open_start', models.DateField(blank=True, null=True, verbose_name='开放开始日')),
                ('open_end', models.DateField(blank=True, null=True, verbose_name='开放结束日')),
                ('open_batch_no', models.CharField(blank=True, default='', max_length=32, verbose_name='面向批次号')),
                ('bp', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='负责BP')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('submitter', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='提交人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '岗位需求',
                'verbose_name_plural': '岗位需求',
                'db_table': 'campus_position_demands',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PositionApplication',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(default=1, verbose_name='志愿顺序')),
                ('channel', models.CharField(choices=[('志愿', '志愿'), ('指定', '指定')], default='志愿', max_length=16, verbose_name='来源渠道')),
                ('status', models.CharField(choices=[('已填报', '已填报'), ('推送中', '推送中'), ('已录取', '已录取'), ('已放弃', '已放弃'), ('已释放', '已释放'), ('人才市场', '人才市场')], db_index=True, default='已填报', max_length=16, verbose_name='状态')),
                ('pushed_at', models.DateTimeField(blank=True, null=True, verbose_name='推送时间')),
                ('decision', models.CharField(blank=True, default='', max_length=16, verbose_name='BP决定')),
                ('decided_at', models.DateTimeField(blank=True, null=True, verbose_name='决定时间')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='position_applications', to='campus_control.person', verbose_name='校招生')),
                ('pushed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='推送人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
                ('position', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='campus_placement.positiondemand', verbose_name='岗位需求')),
            ],
            options={
                'verbose_name': '双选志愿',
                'verbose_name_plural': '双选志愿',
                'db_table': 'campus_position_applications',
                'ordering': ['person_id', 'order'],
            },
        ),
        migrations.CreateModel(
            name='PriceScheme',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64, verbose_name='方案名称')),
                ('type', models.CharField(choices=[('FIXED', '固定价'), ('BID', '出价'), ('CONTEST', '竞价')], default='FIXED', max_length=16, verbose_name='方案类型')),
                ('batch', models.CharField(blank=True, default='', max_length=32, verbose_name='校招批次')),
                ('sel_flow_batch', models.CharField(blank=True, default='', max_length=32, verbose_name='双选流程批次')),
                ('tiers', models.JSONField(default=list, verbose_name='排名分档')),
                ('is_default', models.BooleanField(default=False, verbose_name='默认方案')),
                ('enabled', models.BooleanField(default=True, verbose_name='启用')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '定价方案',
                'verbose_name_plural': '定价方案',
                'db_table': 'campus_price_schemes',
                'ordering': ['-is_default', 'name'],
            },
        ),
        migrations.CreateModel(
            name='PriceBid',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='出价')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_bids', to='campus_control.person', verbose_name='出价人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
                ('scheme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bids', to='campus_placement.pricescheme', verbose_name='定价方案')),
            ],
            options={
                'verbose_name': '出价记录',
                'verbose_name_plural': '出价记录',
                'db_table': 'campus_price_bids',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RevenueRecord',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('ym', models.CharField(blank=True, db_index=True, default='', max_length=7, verbose_name='月份')),
                ('output_dept', models.CharField(blank=True, default='', max_length=64, verbose_name='输出部门')),
                ('stage', models.CharField(blank=True, default='', max_length=32, verbose_name='阶段')),
                ('attend_days', models.PositiveIntegerField(default=0, verbose_name='出勤天数')),
                ('rule', models.CharField(blank=True, default='', max_length=64, verbose_name='计价规则')),
                ('unit_price', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='单价')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='金额')),
                ('status', models.CharField(choices=[('待确认', '待确认'), ('已确认', '已确认')], db_index=True, default='待确认', max_length=16, verbose_name='状态')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='revenue_records', to='campus_control.person', verbose_name='校招生')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '输出台账',
                'verbose_name_plural': '输出台账',
                'db_table': 'campus_revenue_records',
                'ordering': ['-ym', 'output_dept'],
            },
        ),
        migrations.CreateModel(
            name='SelectionFlow',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='删除时间')),
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('batch', models.CharField(max_length=32, unique=True, verbose_name='校招批次')),
                ('started', models.BooleanField(default=False, verbose_name='已启动')),
                ('start_time', models.DateTimeField(blank=True, null=True, verbose_name='启动时间')),
                ('wish_limit', models.PositiveIntegerField(blank=True, null=True, verbose_name='志愿数量上限')),
                ('published', models.BooleanField(default=False, verbose_name='已发布结果')),
                ('published_at', models.DateTimeField(blank=True, null=True, verbose_name='发布时间')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '双选撮合流程',
                'verbose_name_plural': '双选撮合流程',
                'db_table': 'campus_selection_flows',
                'ordering': ['batch'],
            },
        ),
    ]
