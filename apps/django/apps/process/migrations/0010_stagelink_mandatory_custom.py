from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('process', '0009_interview_round'),
    ]

    operations = [
        migrations.AddField(
            model_name='processstagelink',
            name='is_mandatory',
            field=models.BooleanField(
                db_index=True,
                default=False,
                verbose_name='系统必含(不可删)',
            ),
        ),
        migrations.AddField(
            model_name='processstagelink',
            name='custom_name',
            field=models.CharField(
                blank=True,
                default='',
                max_length=20,
                verbose_name='流程内显示名(覆盖)',
            ),
        ),
    ]
