# 补 4a08539 (2026-09-01) 留下的 Person.code 字段 schema 漂移.
#
# 来源追溯:
#   - commit 4a08539 "feat(campus): 人员编码改名为候选人编号, 规则统一为 C+8 位流水号"
#     改了 Person.code 字段 (max_length=32, unique=True, verbose_name='候选人编号') + 新增 save()
#     自动补号 C{seq:08d}
#   - 但该 commit 未生成 migration, 导致 apps/candidate/tests/test_migration_drift.py
#     ::test_makemigrations_check_global_no_drift 持续红
#   - 漂移债累计到 2026-09-04 (本次 P0 治理批次) 才补齐
#
# 行为变化:
#   - 应用此 migration 后, 线上 Person.code 列 schema 与 models.py 一致
#   - 已有数据兼容: max_length 32 ≥ 16 既存数据无截断; unique=True 既存重复需先清
#     (按 4a08539 commit message, dev 已用 renumber_persons 管理命令重编号 56 条为
#      C00000001..C00000056, 线上若有重复应按同样模式重编号)
#   - verbose_name 仅元数据, 不影响 DB
#
# 不创建新数据: 纯 AlterField.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campus_control', '0007_alter_controlrule_strength_choices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='code',
            field=models.CharField(max_length=32, unique=True, verbose_name='候选人编号'),
        ),
    ]
