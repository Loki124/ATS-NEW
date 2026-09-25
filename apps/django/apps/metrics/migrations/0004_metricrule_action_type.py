from django.db import migrations, models


def _backfill_action_type(apps, schema_editor):
    """把遗留布尔 blocking 回填到 action_type（True→VETO，False→DEDUCT）。

    回填在 AddField 之后执行：action_type 此时已有 default='DEDUCT'，
    仅把旧 blocking=True 的行升级为 VETO，其余保持 DEDUCT（等价原 False）。
    """
    MetricRule = apps.get_model('metrics', 'metricrule')
    MetricRule.objects.filter(blocking=True).update(action_type='VETO')
    MetricRule.objects.filter(blocking=False).update(action_type='DEDUCT')


def _reverse_backfill(apps, schema_editor):
    """反向：把 action_type 写回 blocking（VETO→True，其余→False）。"""
    MetricRule = apps.get_model('metrics', 'metricrule')
    MetricRule.objects.filter(action_type='VETO').update(blocking=True)
    MetricRule.objects.exclude(action_type='VETO').update(blocking=False)


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0003_metricrule_blocking'),
    ]

    operations = [
        migrations.AddField(
            model_name='metricrule',
            name='action_type',
            field=models.CharField(
                choices=[('VETO', '必须满足'), ('DEDUCT', '优先考虑'), ('BONUS', '加分项')],
                db_index=True, default='DEDUCT',
                help_text='VETO=必须满足(不满足即拒绝业务动作)；'
                          'DEDUCT=优先考虑(不满足仅记录/降权不阻断)；'
                          'BONUS=加分项(满足给正向加权)',
                max_length=16, verbose_name='动作类型',
            ),
        ),
        migrations.RunPython(_backfill_action_type, _reverse_backfill),
    ]
