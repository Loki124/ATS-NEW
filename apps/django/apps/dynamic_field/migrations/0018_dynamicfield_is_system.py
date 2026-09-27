from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_field', '0017_alter_dynamicfield_field_type_person_department'),
    ]

    operations = [
        migrations.AddField(
            model_name='dynamicfield',
            name='is_system',
            field=models.BooleanField(default=False, db_index=True, help_text='系统内置字段(种子预置, 不可删除)'),
        ),
    ]
