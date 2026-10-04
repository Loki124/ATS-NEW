"""数据迁移：指标模板版本化数据层（LIFE-1 / T01）。

方案 C：主表 `metrics_metric_template` 新增只读计数 `version` 列（default=1）+
新建不可变快照表 `metrics_metric_template_version`（建表 + 唯一约束 (template, version)）。

本迁移为**纯 additive**：
  - AddField(version)        —— 带 default，存量行自动置 1，无需重写业务数据
  - CreateModel(MetricTemplateVersion)
  - RunPython                —— 为每条存量 MetricTemplate 补一条 version=1 基线快照
                                （change_kind='create'，snapshot 取模板当前字段值拼成 15 项 JSON，
                                 created_by 留空）。自此任何后续修改都能 diff 出「改了什么」。

逆操作：删本迁移写的所有基线快照（filter(change_kind='create', version=1).delete()）。
注意：主表 `version` 列与快照表本身由 Reverse 自动 DropField / RemoveModel，业务数据零改动。

约定（对齐 0018 头部注释）：seed 数据直写 `.get_or_create`，**不走 `clean()`**，
避免「恰好一个 FK / operators 合法性」校验拦截存量（二选一约束允许其中一个为 None）。
迁移内历史模型不携带 models.py 的 property（`metric`/`metric_kind` 等），
故快照冗余字段（metric_name/metric_kind/metric_path/data_type/unit）在此手工从 FK 关联取出。
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _new_id():
    """与 UUIDModel.save() 一致：nanoid size=21，失败回退 uuid.hex。"""
    try:
        from nanoid import generate as nanoid_generate
        return nanoid_generate(size=21)
    except Exception:
        import uuid
        return uuid.uuid4().hex


def _build_snapshot(tpl, atomic_model, derived_model):
    """从存量模板行拼 15 项 snapshot（对齐文档 4.2 ② JSON 示例）。

    tpl 为迁移历史模型实例，仅含字段、不含自定义 property，故手工解析关联指标。
    二选一约束允许 atomic / derived 其中一个为 None，两种情况都安全处理。
    """
    if tpl.atomic_metric_id:
        metric = atomic_model.objects.filter(pk=tpl.atomic_metric_id).first()
        metric_kind = 'atomic'
    else:
        metric = derived_model.objects.filter(pk=tpl.derived_metric_id).first()
        metric_kind = 'derived'

    metric_name = metric.name if metric else None
    if metric is None:
        metric_path = None
        data_type = None
        unit = None
    elif metric_kind == 'atomic':
        metric_path = metric.source_path
        data_type = metric.data_type
        unit = metric.unit
    else:
        metric_path = metric.base_path
        data_type = metric.data_type
        unit = metric.unit

    return {
        'name': tpl.name,
        'atomic_metric_id': tpl.atomic_metric_id,
        'derived_metric_id': tpl.derived_metric_id,
        'metric_name': metric_name,
        'metric_kind': metric_kind,
        'metric_path': metric_path,
        'data_type': data_type,
        'unit': unit,
        'operators': tpl.operators or [],
        'param_config': tpl.param_config or {},
        'value_domain': tpl.value_domain or {},
        'param_enums': tpl.param_enums or [],
        'param_allow_null': tpl.param_allow_null,
        'status': tpl.status,
        'description': tpl.description or '',
    }


def _seed_baseline_versions(apps, schema_editor):
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    DerivedMetric = apps.get_model('metrics', 'DerivedMetric')
    MetricTemplateVersion = apps.get_model('metrics', 'MetricTemplateVersion')

    for tpl in MetricTemplate.objects.all():
        snapshot = _build_snapshot(tpl, AtomicMetric, DerivedMetric)
        MetricTemplateVersion.objects.get_or_create(
            template=tpl,
            version=1,
            defaults={
                'id': _new_id(),
                'snapshot': snapshot,
                'changed_fields': [],
                'change_kind': 'create',
                'change_note': '',
                'created_by': None,
            },
        )


def _unseed_baseline_versions(apps, schema_editor):
    MetricTemplateVersion = apps.get_model('metrics', 'MetricTemplateVersion')
    MetricTemplateVersion.objects.filter(change_kind='create', version=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0018_seed_safe_set_templates'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='metrictemplate',
            name='version',
            field=models.PositiveIntegerField(default=1, help_text='每次语义变更 +1；仅作展示计数，历史内容见 MetricTemplateVersion', verbose_name='当前版本号'),
        ),
        migrations.CreateModel(
            name='MetricTemplateVersion',
            fields=[
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False)),
                ('version', models.PositiveIntegerField(verbose_name='版本号')),
                ('snapshot', models.JSONField(verbose_name='配置快照')),
                ('changed_fields', models.JSONField(default=list, verbose_name='变更字段')),
                ('change_kind', models.CharField(help_text='create / update / rollback / import', max_length=16, verbose_name='变更类型')),
                ('change_note', models.CharField(blank=True, default='', max_length=255, verbose_name='变更说明')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='操作人')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='metrics.metrictemplate', verbose_name='所属模板')),
            ],
            options={
                'verbose_name': '指标模板版本',
                'verbose_name_plural': '指标模板版本',
                'db_table': 'metrics_metric_template_version',
                'ordering': ['-version'],
                'constraints': [models.UniqueConstraint(fields=('template', 'version'), name='uniq_tpl_version')],
            },
        ),
        migrations.RunPython(_seed_baseline_versions, _unseed_baseline_versions),
    ]
