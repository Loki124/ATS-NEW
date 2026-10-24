"""导入校招生全生命周期真实业务数据（2026-10-23）。

## 数据来源

逆向自 workbuddy.link《校招生管理系统》演示环境的前端产物：

- `js/real-data.js` —— 由《校招生轮岗管理.xlsx》生成（2026-09-07）
  （878 名校招生 / 10 名班主任 / 177 名导师 / 8 名 HRBP / 1026 所院校 /
  49 条异常记录 / 125 条待分配 / 23 行 BG·BU 计划 / 296 行院校 offer 统计）
- `js/rotres-data.js` —— 由《基地轮岗资源盘点(直播间&客服）.xlsx》生成
  （116 个直播间台账 / 133 行盘点明细）

抽取结果落盘在 `management/commands/data/campus_lifecycle_seed.json`（**仓库内可追溯**），
本命令只读该文件，不联网、不依赖目标站存活。

## 导入映射（逐字段口径见下）

| 源集合 | 目标 | 关键口径 |
|---|---|---|
| `teachers` / `mentors` / `hrbps` | `core.User` + `user_roles` | 账号 = 工号；姓名写 `first_name` 与 `username`；**密码不可用**（需 HR 单独开号） |
| `students` | `campus_control.Person` | 编号 `CS` + 8 位（**不复用候选人 C 序列**，避免与候选人编号撞号）；工号补 8 位（`25` + 6 位） |
| `schools` | `library.School` | 名称唯一幂等；`tags` 存校准标签；`is_customized=True` 的**不覆盖**（人工改过） |
| `exceptions` | `campus_assessment.FeedbackRecord` | 真实异常记录 → 反馈记录（处理方式 / 证据 / 处理人一一对应） |
| `pendings` | `campus_placement.PositionDemand` + `PositionApplication` | 待分配校招生 → 岗位需求（按意向部门去重）+ 第一志愿 |
| `rotRes.names` | `campus_rotation.RotationResource` | 116 个直播间台账 → 直播间形态资源（平台 / 地点） |

## 几条必须写下来的口径决策（都是「不编造」的选择）

1. **院校标签**：`985 / 211 / 双一流` 原样保留；`一本院校 / 省重点 / 二本院校 / 普通`
   一律归 `其他`（`SCHOOLS` 枚举只有四档，源数据另有四档标签 → 不可无损映射，
   **归入"其他"而不是自造新枚举**，否则下拉与管控口径会漂）。
2. **专业标签**：源数据是专业**名称**（如「工商管理」），本仓 `major` 存的是
   **标签**（`工学 / 其他`）→ 用关键词表判定是否为工科；专业名称存 `major_name`。
3. **BG（部门）**：源数据 6 个 BG（能电 / 三到 / 醒电 / 能人 / 能智 / 能本），
   本仓 `DEPTS` 原先只有 4 个 → 已按源数据补齐（见 `constants.DEPTS` 注释）。
4. **直播间**：`names` 台账是**逐个直播间**（116 行），`rooms` 盘点是**部门级聚合**
   （133 行，合计间数 116 / 现有主播 545）。本仓 `RotationResource` 是逐个直播间粒度
   → 导入 116 行台账；`rooms` 的社招/校招人数是**部门级**数字，逐间分摊属编造
   → **不写进逐间资源**，改为写入 `remark` 注明该 BU 的盘点口径，并写入导入摘要。
5. **轮岗经历**（`students[].rotations`，778 条）与**轮岗计划 / 定岗计划**
   （`rotPlan` / `finalPlan`）：本仓已有 `RotationArrangement` 状态机模型，
   其字段与来源口径差异大（阶段 / 审批 / 班级 / 导师关系），本命令**不导入**
   → 摘要中如实登记条数，避免"看起来导全了"。

## 纪律

- **幂等**：以稳定业务键 upsert（工号 / 编号 / 院校名 / 资源名），重复执行不产生重复行。
- **不破坏既有数据**：已存在的 Person（同工号）**只补空字段**，不覆盖人工维护的值。
- **可回滚**：支持 `--dry-run`（只统计不写）与 `--limit`（抽样试跑）。
- **摘要**：每个集合输出「新增 / 更新 / 跳过 / 冲突」四类计数 + 警告清单。
"""
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone

# ---------------------------------------------------------------------------
# 口径常量
# ---------------------------------------------------------------------------

#: 院校标签映射（源 → 本仓 `SCHOOLS` 四档；不可无损映射的一律归「其他」）
SCHOOL_TAG_MAP = {
    '985': '985',
    '211': '211',
    '双一流': '双一流',
    '一本院校': '其他',
    '省重点': '其他',
    '二本院校': '其他',
    '普通': '其他',
    '其他': '其他',
}

#: 学历映射（源 → 本仓 `EDUCATIONS`）
EDUCATION_MAP = {
    '本科': '本科',
    '研究生': '硕士',
    '硕士': '硕士',
    '博士': '博士',
    '大专': '大专',
    '高中': '高中及以下',
}

#: 学位映射（源 → 本仓 `DEGREES`）
DEGREE_MAP = {
    '本科': '学士',
    '研究生': '硕士',
    '硕士': '硕士',
    '博士': '博士',
}

#: 判定「工学」专业的关键词（源数据是专业**名称**，本仓 `major` 存**标签**）
ENGINEERING_KEYWORDS = (
    '工程', '计算机', '软件', '电子', '机械', '电气', '自动化', '通信', '土木',
    '建筑', '材料', '化学', '化工', '生物', '医学', '药', '能源', '矿业',
    '冶金', '航空', '航天', '车辆', '仪器', '水利', '环境', '食品', '纺织',
    '地质', '海洋', '农业', '林业', '测绘', '控制', '光电', '高分子',
)

#: 源状态 → 本仓 `STATUS`
STATUS_MAP = {'在职': '在职', '离职': '离职', '待入职': '待入职'}

#: 平台中文名 → 本仓 `LIVE_ROOM_PLATFORM` 字典 key（缺字典项时留空）
PLATFORM_MAP = {'抖音': 'DOUYIN', '快手': 'KUAISHOU'}

#: 单直播间主播均值上限（逆向清单 A12：默认 7 人/间 = 社招 3 + 校招 4）
ROOM_MEAN_CAP = 7


def _text(value) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _date(value):
    """'2026-08-27' → date；空/非法 → None。"""
    text = _text(value)[:10]
    if not text:
        return None
    try:
        from datetime import date as _date_cls
        y, m, d = (int(x) for x in text.split('-'))
        return _date_cls(y, m, d)
    except (ValueError, TypeError):
        # 日期串非法（位数不对 / 非数字 / 月日越界）→ 当作「无日期」处理。
        # 🔴 这里**必须窄化**：仓库盲捕获护栏（tests/test_no_blind_except.py）禁止
        #    新增 `except Exception`（HARD_LIMIT 锁定下限），宽捕获需带 noqa 许可标记。
        return None


def _is_engineering(major_name: str) -> str:
    return '工学' if any(k in (major_name or '') for k in ENGINEERING_KEYWORDS) else '其他'


class Command(BaseCommand):
    help = '导入校招生全生命周期真实业务数据（来源：workbuddy.link 校招生管理系统演示环境前端产物）'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='只统计不写库')
        parser.add_argument('--limit', type=int, default=0, help='每个集合最多处理 N 条（0=不限）')
        parser.add_argument(
            '--only', default='',
            help='只跑指定集合，逗号分隔（users/students/schools/feedbacks/pendings/resources）',
        )
        parser.add_argument('--skip-users', action='store_true', help='不创建 core.User')
        parser.add_argument('--skip-schools', action='store_true', help='不导入院校库')

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        from apps.campus_control.models import Person

        seed_path = Path(__file__).resolve().parent / 'data' / 'campus_lifecycle_seed.json'
        if not seed_path.exists():
            self.stderr.write(self.style.ERROR(f'种子文件缺失: {seed_path}'))
            return
        seed = json.loads(seed_path.read_text(encoding='utf-8'))

        only = {s.strip() for s in _text(options.get('only')).split(',') if s.strip()}
        limit = options.get('limit') or 0
        dry_run = bool(options.get('dry_run'))

        def pick(items):
            items = list(items or [])
            return items[:limit] if limit else items

        summary = {
            'dry_run': dry_run,
            'users': {'新增': 0, '更新': 0, '跳过': 0, '冲突': 0},
            'students': {'新增': 0, '更新': 0, '跳过': 0, '冲突': 0},
            'schools': {'新增': 0, '更新': 0, '跳过': 0, '冲突': 0},
            'feedbacks': {'新增': 0, '更新': 0, '跳过': 0, '冲突': 0},
            'pendings': {'新增': 0, '更新': 0, '跳过': 0, '冲突': 0},
            'resources': {'新增': 0, '更新': 0, '跳过': 0, '冲突': 0},
        }
        warnings = []

        # 名册 → core.User（须先建，才能把班主任/导师/HRBP 挂到 Person 上）
        user_index = {}
        if not only or 'users' in only:
            if not options.get('skip_users'):
                user_index = self._import_users(seed, pick, summary, warnings, dry_run)
            else:
                warnings.append('已跳过 core.User 导入（--skip-users）')
        else:
            user_index = self._existing_user_index()

        created_emps = set()
        if not only or 'students' in only:
            created_emps = self._import_students(seed, pick, summary, warnings, dry_run, user_index)

        if not only or 'schools' in only:
            if not options.get('skip_schools'):
                self._import_schools(seed, pick, summary, warnings, dry_run)
            else:
                warnings.append('已跳过院校库导入（--skip-schools）')

        if not only or 'feedbacks' in only:
            self._import_feedbacks(seed, pick, summary, warnings, dry_run, created_emps)

        if not only or 'pendings' in only:
            self._import_pendings(seed, pick, summary, warnings, dry_run, created_emps)

        if not only or 'resources' in only:
            self._import_resources(seed, pick, summary, warnings, dry_run)

        # ---- 输出摘要 ----
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('===== 校招生生命周期数据导入摘要 ====='))
        self.stdout.write(f"模式: {'试运行（不写库）' if dry_run else '实际写入'}"
                          f"{'，每集合限 ' + str(limit) + ' 条' if limit else ''}")
        for name, stat in summary.items():
            if name == 'dry_run':
                continue
            self.stdout.write(
                f"  {name:<10} 新增 {stat['新增']:>4} | 更新 {stat['更新']:>4} | "
                f"跳过 {stat['跳过']:>4} | 冲突 {stat['冲突']:>4}"
            )
        # 未导入项如实登记
        stu = seed.get('students') or []
        rot_count = sum(len(s.get('rotations') or []) for s in stu)
        self.stdout.write(self.style.WARNING('未导入（口径不匹配，勿以为已导全）：'))
        self.stdout.write(f"  · 轮岗经历 {rot_count} 条（源为学生内嵌数组，本仓 RotationArrangement 是带审批状态机的独立模型）")
        self.stdout.write(f"  · 轮岗计划 {len(seed.get('rotPlan') or [])} 行 / 定岗计划 {len(seed.get('finalPlan') or [])} 行"
                          '（源表含分组表头行，无稳定业务键）')
        self.stdout.write(f"  · 直播间盘点明细 {len((seed.get('rotRes') or {}).get('rooms') or [])} 行"
                          '（部门级聚合，逐间分摊属编造 → 仅按 BU 口径写入 remark）')
        self.stdout.write(f"  · BG·BU 计划 {len(seed.get('orgPlan') or [])} 行 / 院校 offer 统计 {len(seed.get('offerStats') or [])} 行"
                          '（统计接口实时聚合，不落库）')
        if warnings:
            self.stdout.write(self.style.WARNING(f'警告 {len(warnings)} 条：'))
            for w in warnings[:30]:
                self.stdout.write(f'  - {w}')
            if len(warnings) > 30:
                self.stdout.write(f'  … 其余 {len(warnings) - 30} 条省略')
        self.stdout.write('')

    # ------------------------------------------------------------------
    # 名册 → core.User
    # ------------------------------------------------------------------
    def _existing_user_index(self):
        from apps.core.models import User
        index = {}
        for u in User.objects.all():
            if u.employee_id:
                index[u.employee_id] = u
            index.setdefault(_text(u.first_name) or _text(u.username), u)
        return index

    def _import_users(self, seed, pick, summary, warnings, dry_run):
        from apps.core.models import User
        from apps.core.models_permission_v2 import RoleV2, UserRoleV2

        roster = []
        for t in (seed.get('teachers') or []):
            roster.append((t, 'HEAD_TEACHER', '班主任'))
        for m in (seed.get('mentors') or []):
            roster.append((m, 'CAMPUS_MENTOR', '校园导师'))
        for h in (seed.get('hrbps') or []):
            roster.append((h, 'HRBP', 'HRBP'))

        index = {}
        existing = self._existing_user_index()
        for raw, role_code, role_name in pick(roster):
            name = _text(raw.get('name'))
            emp = _text(raw.get('empNo'))
            if not name:
                summary['users']['跳过'] += 1
                continue
            hit = existing.get(emp) or existing.get(name)
            if hit is not None:
                summary['users']['更新'] += 1
                index[name] = hit
                index[emp] = hit
                continue
            if dry_run:
                summary['users']['新增'] += 1
                index[name] = None
                index[emp] = None
                continue
            # 🔴 并发安全：另一个会话可能同时在导同一批名册 → 先按 username 复查，
            #    撞唯一约束（1062）时复用已存在的那行，不重复建人。
            username = emp or name
            existing_user = User.objects.filter(username=username).first()
            if existing_user is not None:
                summary['users']['更新'] += 1
                index[name] = existing_user
                index[emp] = existing_user
                continue
            try:
                user = User.objects.create(
                    username=username,
                    first_name=name,
                    last_name='',
                    employee_id=emp or None,
                    is_active=True,
                )
            except IntegrityError:
                user = User.objects.filter(username=username).first()
                if user is None:
                    summary['users']['冲突'] += 1
                    warnings.append(f'名册「{name}」建号失败：用户名冲突且无法复用')
                    continue
                summary['users']['更新'] += 1
                index[name] = user
                index[emp] = user
                continue
            # 🔴 密码**不可用**：导入的名册只用于「人 - 档案」的关联与隔离，
            #    不给任何默认可登录口令；需要登录的账号由 HR 单独开号并设密。
            user.set_unusable_password()
            user.save(update_fields=['password'])
            # 角色：RoleV2 行不存在则补（与 tests/test_campus_isolation.py 的自包含建角色同款）
            if not RoleV2.objects.filter(role_code=role_code, system_code='recruit').exists():
                RoleV2.objects.create(
                    system_code='recruit', role_code=role_code, role_name=role_name,
                    description=f'校招生全生命周期移植导入：{role_name}',
                    is_system=0, status=1, default_data_scope_type='ALL',
                )
            UserRoleV2.objects.get_or_create(
                user=user, role_code=role_code, system_code='recruit',
                defaults={'granted_by_id': None, 'granted_at': timezone.now()},
            )
            summary['users']['新增'] += 1
            index[name] = user
            index[emp] = user
        return index

    # ------------------------------------------------------------------
    # 校招生 → Person
    # ------------------------------------------------------------------
    def _import_students(self, seed, pick, summary, warnings, dry_run, user_index):
        """导入校招生主数据；返回**本次新建**的工号集合（供反馈/待分配按工号回查）。"""
        from apps.campus_control.constants import DEPTS, SCHOOLS
        from apps.campus_control.models import Person
        from apps.campus_rotation.models import ClassRoom

        students = pick(seed.get('students') or [])
        created_emps = set()
        if not students:
            return created_emps

        # 班级：按源数据班级名建档（班主任取名册里带该班的班主任）
        class_by_name = {c.name: c for c in ClassRoom.objects.all()}
        teacher_classes = {}
        for t in (seed.get('teachers') or []):
            for cls in (t.get('classes') or []):
                teacher_classes.setdefault(cls, []).append(_text(t.get('name')))

        # 编号序列：CS + 8 位，从现有最大序号续号（不复用候选人 C 序列）
        # 🔴 并发安全：取号在事务内对 Person 表加锁（select_for_update），
        #    否则「另一个会话同时导同一批人」会让两人拿到同一个编号 → 撞唯一约束。
        with transaction.atomic():
            max_seq = 0
            for code in Person.all_objects.select_for_update().filter(code__startswith='CS').values_list('code', flat=True):
                digits = code[2:]
                if digits.isdigit():
                    max_seq = max(max_seq, int(digits))
            seq = max_seq

        existing_by_emp = {}
        for p in Person.all_objects.all():
            if p.employee_id:
                existing_by_emp[p.employee_id] = p

        for s in students:
            name = _text(s.get('name'))
            raw_emp = _text(s.get('employeeId'))
            if not name:
                summary['students']['跳过'] += 1
                continue
            emp = ('25' + raw_emp.zfill(6))[:8] if raw_emp else ''
            # BG 取值口径（对齐 Person 字段语义）：
            #   bu        = 现在轮岗在哪个 BG → currentDept.l1（缺失时回退 intentDept.l1）
            #   intent_bu = 投递时意向去哪个 BG → intentDept.l1
            current_bg = _text((s.get('currentDept') or {}).get('l1'))
            intent_bg = _text((s.get('intentDept') or {}).get('l1'))
            dept = current_bg or intent_bg
            if dept and dept not in DEPTS:
                warnings.append(f'BG「{dept}」不在 DEPTS 枚举（已归入「综合BG」）：{name}')
                dept = '综合BG'
            if intent_bg and intent_bg not in DEPTS:
                intent_bg = ''
            if dept == intent_bg:
                # 当前 BG 与意向 BG 相同 → intent_bu 无信息量，留空（避免"意向=当前"的假数据）
                intent_bg = ''
            entry = _date(s.get('entryDate'))
            status = STATUS_MAP.get(_text(s.get('status')), '在职')
            tag = SCHOOL_TAG_MAP.get(_text(s.get('schoolTag')), '其他')
            edu_raw = _text(s.get('degree'))
            education = EDUCATION_MAP.get(edu_raw, '其他')
            degree = DEGREE_MAP.get(edu_raw, '其他')
            major_name = _text(s.get('major'))
            class_name = _text(s.get('class'))

            if emp and emp in existing_by_emp:
                person = existing_by_emp[emp]
                # 🔴 只补空字段，不覆盖人工维护的值
                changed = []
                if not person.school_name and _text(s.get('school')):
                    person.school_name = _text(s.get('school'))[:64]
                    changed.append('school_name')
                if not person.intent_bu and intent_bg:
                    person.intent_bu = intent_bg[:16]
                    changed.append('intent_bu')
                if not person.major_name and major_name:
                    person.major_name = major_name[:64]
                    changed.append('major_name')
                if not person.batch and _text(s.get('batch')):
                    person.batch = _text(s.get('batch'))[:32]
                    changed.append('batch')
                if changed and not dry_run:
                    person.save(update_fields=changed + ['updated_at'])
                summary['students']['更新'] += 1
                continue

            seq += 1
            created_emps.add(emp)
            if dry_run:
                summary['students']['新增'] += 1
                continue

            # 班主任 / 导师 / HRBP：按姓名匹配名册
            head_teacher = user_index.get(_text(s.get('teacherName')))
            mentor = None
            for r in (s.get('rotations') or []):
                cand = user_index.get(_text(r.get('supervisor')))
                if cand is not None:
                    mentor = cand
                    break
            hrbp = None
            dept_l2 = _text((s.get('intentDept') or {}).get('l2'))
            for h in (seed.get('hrbps') or []):
                if dept_l2 and dept_l2 in (_text(h.get('name')), *[_text(x) for x in (h.get('scopeBus') or [])]):
                    hrbp = user_index.get(_text(h.get('name')))
                    break

            classroom = class_by_name.get(class_name)
            if class_name and classroom is None:
                owners = teacher_classes.get(class_name) or []
                classroom = ClassRoom.objects.create(
                    name=class_name[:64],
                    head_teacher=user_index.get(owners[0]) if owners else None,
                    batch=_text(s.get('batch'))[:32],
                    remark='校招生生命周期数据导入：按《校招生轮岗管理.xlsx》班级名建档',
                )
                class_by_name[class_name] = classroom

            # 并发安全：创建前再复查一次（同工号可能已被另一个会话建好）
            race = Person.all_objects.filter(employee_id=emp).first() if emp else None
            if race is not None:
                summary['students']['更新'] += 1
                continue
            Person.objects.create(
                code=f'CS{seq:08d}',
                name=name[:64],
                bu=dept or DEPTS[0],
                intent_bu=intent_bg,
                school=tag,
                school_name=_text(s.get('school'))[:64],
                sex=_text(s.get('gender')) or '男',
                major=_is_engineering(major_name),
                major_name=major_name[:64],
                education=education,
                degree=degree,
                status=status,
                actual_entry_date=entry if status in ('在职', '离职') else None,
                expected_entry_date=entry,
                employee_id=emp,
                batch=_text(s.get('batch'))[:32],
                class_room=classroom,
                head_teacher=head_teacher,
                mentor=mentor,
                hrbp=hrbp,
                counted=True,
            )
            summary['students']['新增'] += 1

        return created_emps

    # ------------------------------------------------------------------
    # 院校库
    # ------------------------------------------------------------------
    def _import_schools(self, seed, pick, summary, warnings, dry_run):
        import hashlib

        from apps.library.models import School

        rows = pick(seed.get('schools') or [])
        existing = {s.name: s for s in School.all_objects.all()}
        for row in rows:
            name = _text(row.get('name'))
            if not name:
                summary['schools']['跳过'] += 1
                continue
            hit = existing.get(name)
            if hit is not None:
                # 🔴 存量院校库的 tags 词汇更丰富（双万计划 / 卓越工程师 / 中央部属 …），
                #   源数据的 tag 是**校招口径**的院校标签（211 / 一本院校 / 省重点 …）——
                #   两种词汇**不混写**（混写会让院校页的标签筛选出现两套语义）。
                #   → 存量只补空省份，标签保持库内原样。
                if not hit.province and row.get('province') and not dry_run:
                    hit.province = _text(row.get('province'))[:50]
                    hit.save(update_fields=['province', 'updated_at'])
                    summary['schools']['更新'] += 1
                else:
                    summary['schools']['跳过'] += 1
                continue
            summary['schools']['新增'] += 1
            if dry_run:
                continue
            # 编号：教育部院校代码是 10 位数字，本仓存量用的也是该口径；
            # 源数据没有教育部代码 → 用名称哈希生成**稳定**的 10 位数字码，
            # 保证重复导入幂等（不会因序号漂移产生重复行）。
            digest = hashlib.sha1(name.encode('utf-8')).hexdigest()
            code = str(int(digest[:12], 16) % 10_000_000_000).zfill(10)
            if School.all_objects.filter(code=code).exists():
                code = str((int(digest[:12], 16) + 1) % 10_000_000_000).zfill(10)
            School.objects.create(
                name=name[:200],
                code=code,
                province=_text(row.get('province'))[:50],
                tags=_text(row.get('tag'))[:300],
                status='ACTIVE',
                is_customized=False,
            )

    # ------------------------------------------------------------------
    # 异常记录 → 反馈记录
    # ------------------------------------------------------------------
    def _import_feedbacks(self, seed, pick, summary, warnings, dry_run, known_new_emps=frozenset()):
        try:
            from apps.campus_assessment.models import FeedbackRecord
        except (ImportError, LookupError) as exc:
            # app 未注册 / 模型不存在 → 如实登记「未导入」并返回，不静默跳过。
            # 🔴 窄化到具体异常：仓库盲捕获护栏（tests/test_no_blind_except.py）
            #    禁止新增 `except Exception`（宽捕获需带 `# noqa: BLE001` 许可标记）。
            warnings.append(f'反馈记录未导入（campus_assessment 不可用：{exc}）')
            return
        from apps.campus_control.models import Person
        from apps.core.models import User

        rows = pick(seed.get('exceptions') or [])
        users = {(_text(u.first_name) or _text(u.username)): u for u in User.objects.all()}
        # ⚠️ Person.employee_id 落库时**已经是 8 位**（'25' + 6 位补零），
        #    这里直接取用，**不可再补零**（二次补零会得到 '25025008' 这种废键，
        #    导致「找不到校招生」的全量误报）。
        person_by_emp = {
            _text(p.employee_id): p
            for p in Person.objects.all() if p.employee_id
        }
        # 姓名兜底：源异常记录里有 1 条**离职名册**行（X009）没有工号 → 按姓名回查
        person_by_name = {p.name: p for p in Person.objects.all() if p.name}
        # 试运行模式下 Person 还没落库 → 姓名兜底要用**种子名单**判定可解析
        seed_names = {_text(x.get('name')) for x in (seed.get('students') or []) if _text(x.get('name'))}
        existing = {
            (f.date.isoformat() if f.date else '', f.person_id, _text(f.content)[:60]): f
            for f in FeedbackRecord.objects.all()
        }

        for row in rows:
            raw_emp = _text(row.get('empNo'))
            emp = ('25' + raw_emp.zfill(6))[:8] if raw_emp else ''
            person = person_by_emp.get(emp)
            if person is None and not raw_emp:
                person = person_by_name.get(_text(row.get('name')))
                if person is None and _text(row.get('name')) in seed_names:
                    # 试运行：该校招生本轮才创建 → 姓名可解析，按新增计
                    summary['feedbacks']['新增'] += 1
                    continue
            if person is None:
                if emp in known_new_emps:
                    # 试运行模式：该校招生本轮才创建 → 按「可解析」计，不算冲突
                    summary['feedbacks']['新增'] += 1
                    continue
                summary['feedbacks']['冲突'] += 1
                warnings.append(f'异常记录 {row.get("id")} 找不到校招生（工号 {emp}）')
                continue
            # 日期回退链：报告日期 → 入职日期 → 该校招生的实际入职日期
            #（源数据有 1 条「离职名册」行既无报告日期也无入职日期；
            #   落库需要非空日期 → 回退到人员入职日期，仍为空则跳过并登记）
            date = (
                _date(row.get('reportDate'))
                or _date(row.get('entryDate'))
                or person.actual_entry_date
            )
            if date is None:
                summary['feedbacks']['冲突'] += 1
                warnings.append(
                    f"异常记录 {row.get('id')} 无任何可用日期（报告日期/入职日期/人员入职日期均为空），已跳过"
                )
                continue
            key = (date.isoformat() if date else '', person.id, _text(row.get('issue'))[:60])
            if key in existing:
                summary['feedbacks']['更新'] += 1
                continue
            summary['feedbacks']['新增'] += 1
            if dry_run:
                continue
            evidence = _text(row.get('evidence'))
            handled_at = _date(row.get('handleDate'))
            FeedbackRecord.objects.create(
                person=person,
                date=date,
                reporter=users.get(_text(row.get('reporter'))),
                category='issue',
                type=_text(row.get('handleType'))[:32] or '问题记录',
                content=_text(row.get('issue')) or (
                    f"源记录未填问题描述（处理方式：{_text(row.get('handleType2')) or _text(row.get('handleType'))}）"
                ),
                handling=_text(row.get('handleType2')) or _text(row.get('handleType')),
                status='已闭环' if handled_at else '处理中',
                attachments=[evidence] if evidence else [],
                handler=users.get(_text(row.get('handler'))),
                handled_at=handled_at,
            )

    # ------------------------------------------------------------------
    # 待分配 → 岗位需求 + 志愿
    # ------------------------------------------------------------------
    def _import_pendings(self, seed, pick, summary, warnings, dry_run, known_new_emps=frozenset()):
        try:
            from apps.campus_placement.models import PositionApplication, PositionDemand
        except (ImportError, LookupError) as exc:
            # app 未注册 / 模型不存在 → 如实登记「未导入」并返回，不静默跳过。
            # 🔴 窄化到具体异常：仓库盲捕获护栏（tests/test_no_blind_except.py）
            #    禁止新增 `except Exception`（宽捕获需带 `# noqa: BLE001` 许可标记）。
            warnings.append(f'待分配未导入（campus_placement 不可用：{exc}）')
            return
        from apps.campus_control.models import Person

        rows = pick(seed.get('pendings') or [])
        person_by_id = {}
        for s in (seed.get('students') or []):
            person_by_id[_text(s.get('id'))] = s
        emp_to_person = {
            _text(p.employee_id): p
            for p in Person.objects.all() if p.employee_id
        }
        demand_cache = {}
        existing_apps = {
            (a.person_id, a.position_id): a
            for a in PositionApplication.objects.select_related('position')
        }

        for row in rows:
            src = person_by_id.get(_text(row.get('studentId')))
            if src is None:
                summary['pendings']['冲突'] += 1
                continue
            emp = ('25' + _text(src.get('employeeId')).zfill(6))[:8]
            person = emp_to_person.get(emp)
            if person is None:
                if emp in known_new_emps:
                    summary['pendings']['新增'] += 1
                    continue
                summary['pendings']['冲突'] += 1
                warnings.append(f'待分配 {row.get("id")} 找不到校招生（工号 {emp}）')
                continue
            intents = [_text(x) for x in (row.get('intentDepts') or []) if _text(x)]
            if not intents:
                summary['pendings']['跳过'] += 1
                continue
            dept_key = '、'.join(intents)
            demand = demand_cache.get(dept_key)
            if demand is None:
                demand = PositionDemand.objects.filter(name=f'待分配 · {dept_key}').first()
                demand_cache[dept_key] = demand
            if demand is None:
                summary['pendings']['新增'] += 1
                if dry_run:
                    continue
                demand = PositionDemand.objects.create(
                    name=f'待分配 · {dept_key}'[:128],
                    dept=intents[0][:64],
                    business_dept='、'.join(intents)[:64],
                    headcount=1,
                    need_status='待审核',
                    need_desc='由《校招生轮岗管理.xlsx》待分配名单导入（意向部门尚未确认）',
                    scope_type='all',
                )
            if (person.id, demand.id) in existing_apps:
                summary['pendings']['更新'] += 1
                continue
            if not dry_run:
                PositionApplication.objects.get_or_create(
                    person=person, position=demand, order=1,
                    defaults={'channel': '志愿', 'status': '已填报'},
                )
            summary['pendings']['新增'] += 1

    # ------------------------------------------------------------------
    # 直播间台账 → 轮岗资源
    # ------------------------------------------------------------------
    def _import_resources(self, seed, pick, summary, warnings, dry_run):
        from apps.campus_rotation.models import RotationResource

        rot = seed.get('rotRes') or {}
        names = pick(rot.get('names') or [])
        rooms = rot.get('rooms') or []
        if not names:
            return

        # BU 级盘点口径（rooms 是部门级聚合，逐间分摊属编造 → 只写 remark）
        bu_stats = {}
        for r in rooms:
            bu = _text(r.get('bu'))
            acc = bu_stats.setdefault(bu, {'rooms': 0, 'ppl': 0, 'social': 0, 'stu': 0})
            acc['rooms'] += int(r.get('rooms') or 0)
            acc['ppl'] += int(r.get('ppl') or 0)
            acc['social'] += int(r.get('social') or 0)
            acc['stu'] += int(r.get('stu') or 0)

        existing = {r.name: r for r in RotationResource.all_objects.all()}
        for row in names:
            name = _text(row.get('name'))
            if not name:
                summary['resources']['跳过'] += 1
                continue
            bu = _text(row.get('bu'))
            stat = bu_stats.get(bu)
            remark = (
                f"导入自《基地轮岗资源盘点(直播间&客服）.xlsx》台账；"
                f"平台{_text(row.get('platform')) or '未填'}；"
                f"序号{row.get('seq')}"
            )
            if stat:
                remark += (
                    f"；BU {bu} 盘点口径：直播间 {stat['rooms']} 间 / 现有主播 {stat['ppl']} 人"
                    f"（社招 {stat['social']} / 校招 {stat['stu']}，部门级数字未分摊到单间）"
                )
            if name in existing:
                summary['resources']['更新'] += 1
                continue
            summary['resources']['新增'] += 1
            if dry_run:
                continue
            RotationResource.objects.create(
                name=name[:128],
                resource_type=RotationResource.ResourceType.LIVE_ROOM,
                platform=PLATFORM_MAP.get(_text(row.get('platform')), ''),
                location=_text(row.get('loc'))[:64],
                capacity=ROOM_MEAN_CAP,
                social_count=0,
                is_active=True,
                remark=remark[:2000],
            )
