from django.db import migrations, models


def backfill_candidate_code(apps, schema_editor):
    """为存量候选人回填 C+8 位流水号编号（按 created_at, pk 顺序 C00000001..）。

    与 save() 的自动补号规则一致（对齐 campus_control.Person.code）。
    用 .update() 走 SQL 而非 instance.save()，绕开 save() 的 hash 重算与 FSM 逻辑。
    """
    Candidate = apps.get_model('candidate', 'Candidate')
    seq = 0
    for c in Candidate.objects.all().order_by('created_at', 'pk').iterator():
        seq += 1
        if not c.code:
            Candidate.objects.filter(pk=c.pk).update(code=f'C{seq:08d}')


def reverse_backfill(apps, schema_editor):
    """回滚：清空编号（随后 AddField 的 reverse 会直接删列，此处仅兜底）。"""
    Candidate = apps.get_model('candidate', 'Candidate')
    Candidate.objects.update(code='')


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0013_fulltext_search_indexes'),
    ]

    operations = [
        # 1) 先加普通列（不带 unique）：表内已有 >1 行时直接加 unique 列会因
        #    多行默认值 '' 立刻撞唯一约束，必须先加列、回填、再加唯一。
        migrations.AddField(
            model_name='candidate',
            name='code',
            field=models.CharField(
                blank=True, db_index=True, help_text='C+8位流水号, save() 未传时自动补号',
                max_length=20, verbose_name='候选人编号',
            ),
        ),
        # 2) 回填存量数据 C00000001..
        migrations.RunPython(backfill_candidate_code, reverse_backfill),
        # 3) 回填完成后再补 unique 约束
        migrations.AlterField(
            model_name='candidate',
            name='code',
            field=models.CharField(
                blank=True, db_index=True, help_text='C+8位流水号, save() 未传时自动补号',
                max_length=20, unique=True, verbose_name='候选人编号',
            ),
        ),
    ]
