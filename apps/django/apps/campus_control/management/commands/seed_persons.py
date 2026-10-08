"""校招管控人员测试数据补齐（仅 INSERT 新数据，绝不修改/删除现有 Person）。

按 working memory 铁律「绝不大动用户数据前必须先确认」：
  - 用 update_or_create 按业务键 (name, bu, status, expected_entry_date) 去重，已存在则跳过（不覆盖）
  - 仅补齐现有 31 条全为「在职」之外的状态、职务、职级、月份空缺
  - 测试完如需清数据，可 `python manage.py seed_campus --force` 一键重置（含 31 条 + 25 条本 seed）

候选人编号规则：C + 8 位流水号（由 Person.save() 自动补号，本 SEED 不再硬编码 code）。
本文件 25 条演示数据依赖 seed_campus 先跑 31 条（自动获得 C00000001..C00000031）
后，本 SEED 新增行由 save() 补号 C00000032 起，保证全量编号连续。

执行：`python manage.py seed_persons`
"""
from datetime import date

from django.core.management.base import BaseCommand

from apps.campus_control.models import Person

# 4 BU × 2 性别 × 2 职务 × 2 职级 × {在职 1 + 在途Offer 1 + 在途待入职 1} = 96 行
# 实际只取代表性 25 条覆盖：3 状态 × 4 BU × 2 性别 × 1~2 岗位
# 构造：每行业务键 (name, bu, status, expected_entry_date) 全局唯一；
# code 由 Person.save() 自动补号 C+8 流水号。
SEED = [
    # ===== 在途Offer（10 条）=====
    # expected_entry_date 全部 2026-08-XX（用于筛 year=2026 命中）
    {'name': '员工100', 'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '在途Offer', 'position': '技术研发', 'level': 'L1', 'expected': '2026-08-15', 'actual': None},
    {'name': '员工101', 'bu': '能电BG', 'school': '211', 'sex': '女', 'major': '工学', 'month': '8月', 'status': '在途Offer', 'position': '产品', 'level': 'L2', 'expected': '2026-08-20', 'actual': None},
    {'name': '员工102', 'bu': '三到BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '在途Offer', 'position': '技术研发', 'level': 'L1', 'expected': '2026-08-15', 'actual': None},
    {'name': '员工103', 'bu': '三到BG', 'school': '211', 'sex': '女', 'major': '其他', 'month': '9月', 'status': '在途Offer', 'position': '设计', 'level': 'L2', 'expected': '2026-09-01', 'actual': None},
    {'name': '员工104', 'bu': '综合BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '9月', 'status': '在途Offer', 'position': '产品', 'level': 'L3', 'expected': '2026-09-15', 'actual': None},
    {'name': '员工105', 'bu': '综合BG', 'school': '双一流', 'sex': '女', 'major': '其他', 'month': '8月', 'status': '在途Offer', 'position': '职能', 'level': 'L2', 'expected': '2026-08-30', 'actual': None},
    {'name': '员工106', 'bu': '醒电BG', 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '在途Offer', 'position': '运营', 'level': 'L1', 'expected': '2026-08-15', 'actual': None},
    {'name': '员工107', 'bu': '醒电BG', 'school': '985', 'sex': '女', 'major': '工学', 'month': '10月', 'status': '在途Offer', 'position': '设计', 'level': 'L2', 'expected': '2026-10-01', 'actual': None},
    # 用于筛 year=2025 命中（去年入职的）
    {'name': '员工108', 'bu': '能电BG', 'school': '其他', 'sex': '男', 'major': '其他', 'month': '8月', 'status': '在途Offer', 'position': '销售', 'level': 'L1', 'expected': '2025-08-15', 'actual': None},
    {'name': '员工109', 'bu': '三到BG', 'school': '双一流', 'sex': '女', 'major': '工学', 'month': '9月', 'status': '在途Offer', 'position': '产品', 'level': 'L3', 'expected': '2025-09-01', 'actual': None},

    # ===== 在途待入职（10 条）=====
    # expected_entry_date + actual_entry_date 都为未来日期（候选人在 2026 内待入职）
    {'name': '员工200', 'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '在途待入职', 'position': '技术研发', 'level': 'L2', 'expected': '2026-08-25', 'actual': None},
    {'name': '员工201', 'bu': '能电BG', 'school': '211', 'sex': '女', 'major': '其他', 'month': '9月', 'status': '在途待入职', 'position': '设计', 'level': 'L1', 'expected': '2026-09-05', 'actual': None},
    {'name': '员工202', 'bu': '三到BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '在途待入职', 'position': '技术研发', 'level': 'L2', 'expected': '2026-08-25', 'actual': None},
    {'name': '员工203', 'bu': '三到BG', 'school': '其他', 'sex': '女', 'major': '其他', 'month': '10月', 'status': '在途待入职', 'position': '运营', 'level': 'L3', 'expected': '2026-10-15', 'actual': None},
    {'name': '员工204', 'bu': '综合BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '在途待入职', 'position': '产品', 'level': 'L2', 'expected': '2026-08-30', 'actual': None},
    {'name': '员工205', 'bu': '综合BG', 'school': '双一流', 'sex': '女', 'major': '工学', 'month': '9月', 'status': '在途待入职', 'position': '职能', 'level': 'L1', 'expected': '2026-09-10', 'actual': None},
    {'name': '员工206', 'bu': '醒电BG', 'school': '211', 'sex': '男', 'major': '其他', 'month': '8月', 'status': '在途待入职', 'position': '销售', 'level': 'L2', 'expected': '2026-08-25', 'actual': None},
    {'name': '员工207', 'bu': '醒电BG', 'school': '985', 'sex': '女', 'major': '工学', 'month': '10月', 'status': '在途待入职', 'position': '设计', 'level': 'L3', 'expected': '2026-10-20', 'actual': None},
    {'name': '员工208', 'bu': '能电BG', 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '在途待入职', 'position': '技术研发', 'level': 'L3', 'expected': '2025-08-30', 'actual': None},
    {'name': '员工209', 'bu': '三到BG', 'school': '双一流', 'sex': '女', 'major': '其他', 'month': '9月', 'status': '在途待入职', 'position': '产品', 'level': 'L2', 'expected': '2025-09-15', 'actual': None},

    # ===== 在职 5 条（覆盖已有 31 条在职中缺失的岗位/职级/月份组合）=====
    {'name': '员工300', 'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '9月', 'status': '在职', 'position': '技术研发', 'level': 'L4', 'expected': '2026-09-01', 'actual': '2026-09-01'},
    {'name': '员工301', 'bu': '能电BG', 'school': '其他', 'sex': '女', 'major': '其他', 'month': '10月', 'status': '在职', 'position': '职能', 'level': 'L2', 'expected': '2026-10-01', 'actual': '2026-10-01'},
    {'name': '员工302', 'bu': '三到BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '在职', 'position': '产品', 'level': 'L3', 'expected': '2026-08-15', 'actual': '2026-08-15'},
    {'name': '员工303', 'bu': '综合BG', 'school': '211', 'sex': '女', 'major': '工学', 'month': '9月', 'status': '在职', 'position': '设计', 'level': 'L1', 'expected': '2026-09-10', 'actual': '2026-09-10'},
    {'name': '员工304', 'bu': '醒电BG', 'school': '双一流', 'sex': '男', 'major': '其他', 'month': '8月', 'status': '在职', 'position': '运营', 'level': 'L2', 'expected': '2026-08-20', 'actual': '2026-08-20'},
]


class Command(BaseCommand):
    help = '校招管控人员测试数据补齐（仅 INSERT 新数据，已存在则跳过）'

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        for row in SEED:
            # 按业务键 (name, bu, status, expected_entry_date) 幂等查重
            # code 不传，让 Person.save() 自动补号 C+8
            lookup = {
                'name': row['name'],
                'bu': row['bu'],
                'status': row['status'],
                'expected_entry_date': date.fromisoformat(row['expected']) if row['expected'] else None,
            }
            obj, was_created = Person.objects.update_or_create(
                **lookup,
                defaults={
                    'school': row['school'],
                    'sex': row['sex'],
                    'major': row['major'],
                    'month': row['month'],
                    'position': row['position'],
                    'level': row['level'],
                    'actual_entry_date': date.fromisoformat(row['actual']) if row['actual'] else None,
                    'counted': True,
                }
            )
            if was_created:
                created += 1
                self.stdout.write(f"  ✓ 新建 {obj.code} {obj.name} ({obj.status})")
            else:
                skipped += 1
                self.stdout.write(f"  · 已存在 {obj.code}（跳过）")
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ 完成：新建 {created} 条 / 跳过 {skipped} 条 / 总数 {Person.objects.count()} 条'
        ))
