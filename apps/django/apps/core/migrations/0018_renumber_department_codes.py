"""统一既有部门编号为 D+6 位流水号格式 (2026-09-18).

背景: 部门编号原为手填、格式不统一 (ROOT/TECH/techBG/HR-001 等混存)。
自 0018 之前的提交起, 新建部门已由 Department.save() 自动生成 D######,
本迁移把**既有**所有部门编号统一归一为 D######, 使全表格式一致。

规则: D + 6 位零填充流水号 (D000001 起), 按 parent_id 升序(null 在前, 即根部门优先)
再按 path 排序, 保证父部门编号小于子部门, 结果确定且可复现。

实现: 两遍写入 ——
  1) 先赋临时编码 TMP{n:010d}, 避免与任何已有的 D###### 编号发生 unique 冲突;
  2) 再赋最终 D{n:06d}。
幂等: 已为 D###### 的库重跑时, 第一遍改为 TMP、第二遍改回 D, 终值不变。

reverse: 无法还原原始编号, 设为 no-op (仅允许 migrate 回退不报错)。
"""
from django.db import migrations


def _renumber(apps, schema_editor):
    Department = apps.get_model('core', 'Department')
    # parent_id 升序 (null 在前 = 根部门优先), 同层按 path 稳定排序
    depts = list(Department.objects.all().order_by('parent_id', 'path'))

    # 第一遍: 临时编码, 规避 unique 冲突
    for i, d in enumerate(depts, start=1):
        d.code = f'TMP{i:010d}'
        d.save(update_fields=['code'])

    # 第二遍: 最终 D###### 编码
    for i, d in enumerate(depts, start=1):
        d.code = f'D{i:06d}'
        d.save(update_fields=['code'])


def _noop_reverse(apps, schema_editor):
    # 原始编号无法恢复, 不执行任何操作
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_management_unit_person_data_range'),
    ]

    operations = [
        migrations.RunPython(_renumber, _noop_reverse),
    ]
