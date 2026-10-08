"""0015: 新增 scene_rule_version 快照表 (场景规则完整版本历史)。

- rule: FK → scene_rule (CASCADE)
- version: 对应版本号
- snapshot: 完整配置 (WizardService 消费的 snake_case 载荷)
- changed_fields / change_kind / change_note / created_by: 审计元数据
- UNIQUE(rule, version)

写入口集中在 services/rule_version_service.py (仅 INSERT); 删除走 FK CASCADE。
"""
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0014_scenerule_code_version'),
    ]

    operations = [
        migrations.CreateModel(
            name='SceneRuleVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.PositiveIntegerField(verbose_name='版本号')),
                ('snapshot', models.JSONField(verbose_name='配置快照')),
                ('changed_fields', models.JSONField(default=list, verbose_name='变更字段')),
                ('change_kind', models.CharField(max_length=16, verbose_name='变更类型')),
                ('change_note', models.CharField(blank=True, default='', max_length=255, verbose_name='变更说明')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('rule', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='versions', to='reason_library.scenerule', verbose_name='所属规则')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='操作人')),
            ],
            options={
                'db_table': 'scene_rule_version',
                'verbose_name': '场景规则版本',
                'verbose_name_plural': '场景规则版本',
                'ordering': ['-version'],
                'constraints': [
                    models.UniqueConstraint(fields=['rule', 'version'], name='uniq_scenerule_version'),
                ],
            },
        ),
    ]
