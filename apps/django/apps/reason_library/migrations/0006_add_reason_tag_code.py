"""0006: 占位迁移 — code 字段定义已下沉至 0001 (建表即含)。

原因: 0002 的 seed 动态 import 当前代码的 seed_initial_data (用真实模型,
含 code 字段), 而 code 列若在 0006 才建, 全新库 migrate 到 0002 时会因
SELECT code 失败。故把 code 下沉进 0001 CreateModel。
本迁移保留以维持 dev 库 django_migrations 记录链完整 (已 fake 应用)。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0005_relax_tag_unique_to_rule_scope'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
