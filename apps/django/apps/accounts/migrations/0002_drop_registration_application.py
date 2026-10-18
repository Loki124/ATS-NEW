"""删除 RegistrationApplication 模型与 registration_applications 表。

2026-10-18 兵哥：自助注册功能整体下线，注册申请审核链路（模型/视图/前端）一并移除，
故本迁移 DropModel 该表。EmailVerificationCode 保留（邮箱验证码免密登录复用）。

⚠️ 本迁移含**物理删表**（表内数据不可恢复）。apply 前请确认已备份/无需保留该表数据。
   若需保留历史申请数据，请在执行前 `CREATE TABLE registration_applications_backup
   AS SELECT * FROM registration_applications`。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='RegistrationApplication',
        ),
    ]
