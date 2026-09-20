from django.db import migrations


def _reclassify_start_end(apps, schema_editor):
    """BR-001 起止阶段归类为系统级「起止阶段」类型 (START_END)：
    初评(P001)/正式录用(P099) 的 stage_type 由 SCREEN/OFFER 改为 START_END。
    功能属性（default_features）保留，仅更换分类标签。幂等。"""
    RecruitmentStage = apps.get_model('process', 'RecruitmentStage')
    RecruitmentStage.objects.filter(code__in=['P001', 'P099']).update(stage_type='START_END')


def _revert(apps, schema_editor):
    RecruitmentStage = apps.get_model('process', 'RecruitmentStage')
    RecruitmentStage.objects.filter(code='P001').update(stage_type='SCREEN')
    RecruitmentStage.objects.filter(code='P099').update(stage_type='OFFER')


class Migration(migrations.Migration):

    dependencies = [
        ('process', '0010_stagelink_mandatory_custom'),
    ]

    operations = [
        migrations.RunPython(_reclassify_start_end, _revert),
    ]
