"""Item4: 同一原因标签仅允许归属于一个分类 (UNIQUE(tag)).

迁移步骤:
1. RunPython 去重 — 同一 tag 在多分类重复时仅保留 id 最小的一条, 其余软删式物理删除。
2. RemoveConstraint uniq_cat_tag (UNIQUE(category, tag))。
3. AddConstraint uniq_tag (UNIQUE(tag)) — 全局唯一, 不可跨分类重复。
"""
from django.db import migrations, models
from django.db.models import UniqueConstraint


def dedupe_category_assignment(apps, schema_editor):
    """同一 tag 只保留一条 (id 最小), 其余删除。"""
    CategoryAssignment = apps.get_model('reason_library', 'CategoryAssignment')
    # 取每个 tag 的保留 id (最小)
    from django.db.models import Min
    keep = (
        CategoryAssignment.objects.values('tag_id')
        .annotate(min_id=Min('id'))
        .values_list('min_id', flat=True)
    )
    # 删除非保留行
    deleted, _ = CategoryAssignment.objects.exclude(id__in=list(keep)).delete()
    # delete() 返回 (count, {model: count}) — 仅打印数量供排查
    print(f'[0003] dedupe category_assignment removed={deleted}')


def reverse_dedupe(apps, schema_editor):
    # 去重不可反向 — 仅恢复约束结构用 noop
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0002_seed_initial_data'),
    ]

    operations = [
        migrations.RunPython(dedupe_category_assignment, reverse_dedupe),
        migrations.RemoveConstraint(
            model_name='categoryassignment',
            name='uniq_cat_tag',
        ),
        migrations.AddConstraint(
            model_name='categoryassignment',
            constraint=UniqueConstraint(
                fields=['tag'],
                name='uniq_tag',
            ),
        ),
    ]
