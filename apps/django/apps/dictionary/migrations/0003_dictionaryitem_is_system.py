from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0002_dictionaryitem_description_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dictionaryitem',
            name='is_system',
            field=models.BooleanField(
                db_index=True,
                default=False,
                verbose_name='系统预置项',
            ),
        ),
    ]
