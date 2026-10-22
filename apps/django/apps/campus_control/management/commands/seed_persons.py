"""校招管控人员测试数据补齐（**只增改，绝不删**）。

写入策略铁律（与 working memory「绝不大动用户数据」一致）：
  - 幂等：按「姓名 / 历史姓名」匹配存量行 → **原地更新**（改名 + 补字段）；
    未命中才新建（code 由 Person.save() 自动补号 C+8）。
  - **不做 wipe**：本命令不删任何行（清数据请走 `seed_campus --force`，需显式确认）。
  - 2026-10-21（二期）数据真实化：姓名由「员工N」改为真实姓名（性别一致），
    在职人员补 8 位工号（YYMM+4 位序号）与实际入职日期。

候选人编号规则：C + 8 位流水号（由 Person.save() 自动补号，本 SEED 不硬编码 code）。
本文件 25 条演示数据与 seed_campus 的 31 条互不冲突（姓名/历史姓名均唯一）。

执行：`python manage.py seed_persons`
"""
from django.core.management.base import BaseCommand

from apps.campus_control.models import Person
from apps.campus_control.sample_data import derive_realistic_fields
from apps.campus_control.seed_upsert import upsert_person_rows

# 3 状态 × 4 BU × 2 性别 × 1~2 岗位 的代表性 25 条
# 字段：legacy_name（改名前老姓名）/ name（真实姓名）/ 工号 / 入职日期
# 「在职」5 条才补工号与实际入职日期（未入职者不分配工号）。
_RAW = [
    # ===== 待入职（offer 阶段 10 条）=====
    # expected_entry_date 全部 2026-08-XX（用于筛 year=2026 命中）
    {'legacy_name': '员工100', 'name': '秦立言', 'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '待入职', 'position': '技术研发', 'level': 'L1', 'expected': '2026-08-15', 'actual': None},
    {'legacy_name': '员工101', 'name': '于静姝', 'bu': '能电BG', 'school': '211', 'sex': '女', 'major': '工学', 'month': '8月', 'status': '待入职', 'position': '产品', 'level': 'L2', 'expected': '2026-08-20', 'actual': None},
    {'legacy_name': '员工102', 'name': '沈怀瑾', 'bu': '三到BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '待入职', 'position': '技术研发', 'level': 'L1', 'expected': '2026-08-15', 'actual': None},
    {'legacy_name': '员工103', 'name': '韩雨薇', 'bu': '三到BG', 'school': '211', 'sex': '女', 'major': '其他', 'month': '9月', 'status': '待入职', 'position': '设计', 'level': 'L2', 'expected': '2026-09-01', 'actual': None},
    {'legacy_name': '员工104', 'name': '陆文昊', 'bu': '综合BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '9月', 'status': '待入职', 'position': '产品', 'level': 'L3', 'expected': '2026-09-15', 'actual': None},
    {'legacy_name': '员工105', 'name': '白欣然', 'bu': '综合BG', 'school': '双一流', 'sex': '女', 'major': '其他', 'month': '8月', 'status': '待入职', 'position': '职能', 'level': 'L2', 'expected': '2026-08-30', 'actual': None},
    {'legacy_name': '员工106', 'name': '崔明哲', 'bu': '醒电BG', 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '待入职', 'position': '运营', 'level': 'L1', 'expected': '2026-08-15', 'actual': None},
    {'legacy_name': '员工107', 'name': '谭梦瑶', 'bu': '醒电BG', 'school': '985', 'sex': '女', 'major': '工学', 'month': '10月', 'status': '待入职', 'position': '设计', 'level': 'L2', 'expected': '2026-10-01', 'actual': None},
    # 用于筛 year=2025 命中（去年入职的）
    {'legacy_name': '员工108', 'name': '姚子豪', 'bu': '能电BG', 'school': '其他', 'sex': '男', 'major': '其他', 'month': '8月', 'status': '待入职', 'position': '销售', 'level': 'L1', 'expected': '2025-08-15', 'actual': None},
    {'legacy_name': '员工109', 'name': '钟佳宁', 'bu': '三到BG', 'school': '双一流', 'sex': '女', 'major': '工学', 'month': '9月', 'status': '待入职', 'position': '产品', 'level': 'L3', 'expected': '2025-09-01', 'actual': None},

    # ===== 待入职（待入职阶段 10 条）=====
    # expected_entry_date 为未来日期（候选人在 2026 内待入职）
    {'legacy_name': '员工200', 'name': '蒋思远', 'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '待入职', 'position': '技术研发', 'level': 'L2', 'expected': '2026-08-25', 'actual': None},
    {'legacy_name': '员工201', 'name': '沈知微', 'bu': '能电BG', 'school': '211', 'sex': '女', 'major': '其他', 'month': '9月', 'status': '待入职', 'position': '设计', 'level': 'L1', 'expected': '2026-09-05', 'actual': None},
    {'legacy_name': '员工202', 'name': '卢景行', 'bu': '三到BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '待入职', 'position': '技术研发', 'level': 'L2', 'expected': '2026-08-25', 'actual': None},
    {'legacy_name': '员工203', 'name': '毕雨晴', 'bu': '三到BG', 'school': '其他', 'sex': '女', 'major': '其他', 'month': '10月', 'status': '待入职', 'position': '运营', 'level': 'L3', 'expected': '2026-10-15', 'actual': None},
    {'legacy_name': '员工204', 'name': '宋承轩', 'bu': '综合BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '待入职', 'position': '产品', 'level': 'L2', 'expected': '2026-08-30', 'actual': None},
    {'legacy_name': '员工205', 'name': '薛楚楚', 'bu': '综合BG', 'school': '双一流', 'sex': '女', 'major': '工学', 'month': '9月', 'status': '待入职', 'position': '职能', 'level': 'L1', 'expected': '2026-09-10', 'actual': None},
    {'legacy_name': '员工206', 'name': '傅明轩', 'bu': '醒电BG', 'school': '211', 'sex': '男', 'major': '其他', 'month': '8月', 'status': '待入职', 'position': '销售', 'level': 'L2', 'expected': '2026-08-25', 'actual': None},
    {'legacy_name': '员工207', 'name': '侯若曦', 'bu': '醒电BG', 'school': '985', 'sex': '女', 'major': '工学', 'month': '10月', 'status': '待入职', 'position': '设计', 'level': 'L3', 'expected': '2026-10-20', 'actual': None},
    {'legacy_name': '员工208', 'name': '阎天成', 'bu': '能电BG', 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '待入职', 'position': '技术研发', 'level': 'L3', 'expected': '2025-08-30', 'actual': None},
    {'legacy_name': '员工209', 'name': '雷悦宁', 'bu': '三到BG', 'school': '双一流', 'sex': '女', 'major': '其他', 'month': '9月', 'status': '待入职', 'position': '产品', 'level': 'L2', 'expected': '2025-09-15', 'actual': None},

    # ===== 在职 5 条（覆盖已有 31 条在职中缺失的岗位/职级/月份组合）=====
    {'legacy_name': '员工300', 'name': '顾亦凡', 'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '9月', 'status': '在职', 'position': '技术研发', 'level': 'L4', 'expected': '2026-09-01', 'actual': '2026-09-01', 'employee_id': '26090001'},
    {'legacy_name': '员工301', 'name': '苏沐瑶', 'bu': '能电BG', 'school': '其他', 'sex': '女', 'major': '其他', 'month': '10月', 'status': '在职', 'position': '职能', 'level': 'L2', 'expected': '2026-10-01', 'actual': '2026-10-01', 'employee_id': '26100001'},
    {'legacy_name': '员工302', 'name': '汪清越', 'bu': '三到BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '在职', 'position': '产品', 'level': 'L3', 'expected': '2026-08-15', 'actual': '2026-08-15', 'employee_id': '26080001'},
    {'legacy_name': '员工303', 'name': '郝映雪', 'bu': '综合BG', 'school': '211', 'sex': '女', 'major': '工学', 'month': '9月', 'status': '在职', 'position': '设计', 'level': 'L1', 'expected': '2026-09-10', 'actual': '2026-09-10', 'employee_id': '26090002'},
    {'legacy_name': '员工304', 'name': '龚嘉泽', 'bu': '醒电BG', 'school': '双一流', 'sex': '男', 'major': '其他', 'month': '8月', 'status': '在职', 'position': '运营', 'level': 'L2', 'expected': '2026-08-20', 'actual': '2026-08-20', 'employee_id': '26080002'},
]

# 组装成 seed_upsert 需要的行：补院校名称/学历/联系电话（按序号确定性派生）
SEED = []
for _i, _row in enumerate(_RAW, 31):
    _row = dict(_row)
    _row.update(derive_realistic_fields(_i, _row['school']))
    _row['counted'] = True
    SEED.append(_row)


class Command(BaseCommand):
    help = '校招管控人员演示数据补齐（幂等：命中存量行则原地更新，只增不删）'

    def handle(self, *args, **options):
        created, updated = upsert_person_rows(SEED)
        self.stdout.write(
            f'\n✅ 完成：新建 {created} 条 / 原地更新 {updated} 条 / 总数 {Person.objects.count()} 条'
        )
