"""Item4 修订 (2026-09-21): 标签唯一性从全局收窄为规则内。

跨规则共享标签池是合法业务需求 (预置规则间复用同一系统标签), 全局 UNIQUE(tag_id)
会导致规则间互相"锁"标签。规则内唯一改由 wizard_service 保存时应用层校验
(写入口集中: wizard/save 是 assignments 唯一变更路径, snapshot 不复制绑定)。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0003_tag_unique_category'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='categoryassignment',
            name='uniq_tag',
        ),
    ]
