"""校招管控：将现有全部 Person.code 重编号为「C + 8 位流水号」（C00000001..）。

背景：候选人编号规则统一为 C+8（见 models.Person.save 自动补号）。历史上 seed 数据使用
P 前缀（P001.. / P100..），与新规则不一致。本命令对现有数据做**原地重编号**：

  - 按 id 升序遍历，分配 C00000001..C000000NN，连续且唯一
  - 使用两趟 UPDATE（先置临时 _T 前缀，再置最终 C 前缀）避免 unique=True 瞬态冲突
  - 仅改 code 值，不删除/重建行 → PersonDimensionValue 等外键关联完整保留

执行：`python manage.py renumber_persons`
"""
from django.core.management.base import BaseCommand

from apps.campus_control.models import Person


class Command(BaseCommand):
    help = '将现有全部 Person.code 重编号为 C+8 位流水号（原地更新，保留外键关联）'

    def handle(self, *args, **options):
        persons = list(Person.objects.order_by('id'))
        total = len(persons)
        if total == 0:
            self.stdout.write(self.style.WARNING('无 Person 数据，跳过'))
            return

        # 第一趟：置临时前缀，规避与目标 C 码可能的瞬态唯一冲突
        for i, p in enumerate(persons):
            Person.objects.filter(pk=p.pk).update(code=f'_T{i:08d}')

        # 第二趟：写最终 C+8 编号
        for i, p in enumerate(persons):
            Person.objects.filter(pk=p.pk).update(code=f'C{i + 1:08d}')

        self.stdout.write(self.style.SUCCESS(
            f'✅ 已重编号 {total} 条 Person：C00000001 .. C{total:08d}'
        ))
        # 抽样校验连续性
        sample = list(Person.objects.order_by('code').values_list('code', flat=True)[:3])
        self.stdout.write(f'   样例：{sample}')
