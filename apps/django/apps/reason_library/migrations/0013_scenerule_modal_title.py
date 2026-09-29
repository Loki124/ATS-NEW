"""0013: 占位迁移 — modal_title 字段定义已下沉至 0001 (建表即含)。

原因: 0002 的 seed 动态 import 当前代码的 seed_initial_data (用真实模型, 含
modal_title 字段), 若该列在 0013 才建, 全新库 migrate 到 0002 时会因
INSERT 含 modal_title 报 no such column。故把字段下沉进 0001 CreateModel。
本迁移保留以维持 dev/生产库 django_migrations 记录链完整 (已应用, 不再重复建列)。

与 0008 (max_selectable_tags) / 0011_ensure (color) 同源的 schema 漂移修复。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0012_delete_sibling_preset_rules'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
