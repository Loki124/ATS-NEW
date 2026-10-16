from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campus_rotation', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='classroom',
            name='capacity',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='容量上限'),
        ),
    ]
