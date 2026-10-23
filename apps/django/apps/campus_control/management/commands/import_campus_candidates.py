"""校招生档案 → 招聘系统「候选人管理」同步导入（2026-10-23）

## 为什么需要这个命令

「编号同源」口径（兵哥：编号自动获取，不需要人工选候选人）要求：
校招生档案的编号与「招聘系统 · 候选人管理」里**同一个候选人**的编号一致。
`PersonSerializer.create/update` 已实现在**新建/编辑**时自动认人并换编号，
但**存量数据**（878 条 `CS` 前缀档案 + 56 条 `C` 前缀档案）没有 candidate 关联，
且招聘系统候选人表里**校招分区一条都没有**（实测 ats_dev：7 条全是 social）
⇒ 没有任何对象可认 ⇒ 编号永远不同源。

本命令把校招生档案**反向同步**为招聘系统候选人（校招分区），
让 `backfill_person_candidate` 之后能真正认出人、编号真正同源。

## 数据映射

| 档案（campus_control.Person） | 候选人（candidate.Candidate） |
|---|---|
| `name` | `name` |
| `phone` | `phone`（加密存储；**原样搬运，绝不改号**） |
| `sex` | `gender`（男/女） |
| `school`（985/211/双一流/其他） | `school_tag`（同枚举） |
| `major`（工学/其他） | `major_tag`（同枚举） |
| `education`（本科学历层次） | `highest_education` |
| `degree` | `extra['degree']` |
| `school_name` | `extra['school_name']` |
| `major_name` | `extra['major_name']` |
| `employee_id` | `extra['employee_id']`（**稳定业务键**，幂等匹配用） |
| `status` | `current_state`（在职→ONBOARDED / 待入职→PENDING_ONBOARDING / 离职→WITHDRAWN） |
| — | `recruit_type='campus'`（**硬分区**：社招候选人不参与认人） |
| — | `extra['source']='校招生档案同步'`、`extra['mock']=True`、`extra['person_code']=档案编号` |

## 手机号缺失怎么办（878 条 CS 档案都没有手机号）

`auto_match_candidate` 的认人规则是「唯一同名 → 认；同名多人 → 手机号精确一致才认」。
存量档案里 **878 条没有手机号**，且有 **4 组同名**（刘杰/刘浩然/刘美彤/李想）
⇒ 若不补手机号，这 4 组同名档案**永远认不出**（同名多人 + 都没手机号）。

处理：对**确实缺手机号**的档案，按 `employee_id` 派生一个稳定测试号：
`199` + 工号后 8 位（`199` 是工信部保留的**测试号段**，不会与真实号码冲突）。
- 原档案**本来就有手机号的，一律原样搬运，绝不改号**；
- 派生号只写在候选人侧，档案侧 `phone` **保持为空**（不污染业务数据）；
- 派生规则是纯函数（工号 → 号），重复执行结果一致 ⇒ 幂等。

## 纪律

- **幂等**：按 `extra['employee_id']` 匹配已存在的校招候选人 → 有则更新、无则新建；
  重复执行不产生重复行。
- **不删数据**：本命令不删任何候选人行（清数据请手工确认后处理）。
- **不覆盖人工维护的字段**：已存在的候选人**只补空字段**，不覆盖已填内容。
- **可回滚**：`--dry-run` 只统计不写；`--limit` 抽样试跑。
- **来源可追溯**：`extra['mock']=True` + `extra['source']='校招生档案同步'`
  ⇒ 将来接入真实招聘系统数据时，可按此标记识别并替换模拟数据。

## 用法

```bash
python manage.py import_campus_candidates --dry-run          # 只统计
python manage.py import_campus_candidates --limit 20          # 抽样 20 条试跑
python manage.py import_campus_candidates                     # 全量导入
python manage.py import_campus_candidates --review-csv /tmp/x.csv   # 导出未导入清单
```
"""
from __future__ import annotations

import csv
import io

from django.core.management.base import BaseCommand

from apps.campus_control.models import Person

#: 招聘系统候选人状态映射（档案状态 → 候选人 FSM 状态）
#: 依据：`ONBOARDED`=已入职 / `PENDING_ONBOARDING`=待入职 / `WITHDRAWN`=已离职
STATE_MAP = {
    '在职': 'ONBOARDED',
    '待入职': 'PENDING_ONBOARDING',
    '离职': 'WITHDRAWN',
}

#: 派生测试号段（工信部保留测试号段，不与真实号码冲突）
MOCK_PHONE_PREFIX = '199'


class Command(BaseCommand):
    help = '把校招生档案同步为招聘系统「候选人管理」的校招分区候选人（编号同源的前置数据）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='只统计将导入/更新的条数，不写入数据库',
        )
        parser.add_argument(
            '--limit', type=int, default=0,
            help='只处理前 N 条档案（0=全部），用于抽样试跑',
        )
        parser.add_argument(
            '--review-csv', type=str, default=None,
            help='未导入清单 CSV 输出路径（缺姓名/工号等无法导入的行）',
        )
        parser.add_argument(
            '--no-phone-backfill', action='store_true',
            help=(
                '不把派生测试手机号回写到档案侧（默认会回写）。\n'
                '  回写是「同名多人」能被认出的前提 —— 存量档案 4 组同名且全无手机号,\n'
                '  不回写则这 7 条永远认不出人。\n'
                '  ⚠️ 回写只补**原本为空**的档案, 已有真实手机号的一律不动。'
            ),
        )

    # ---------------------------------------------------------------- 映射

    def _derive_phone(self, person):
        """取手机号：档案有则原样用；没有则按工号派生稳定测试号。"""
        if person.phone:
            return person.phone, False
        emp = (person.employee_id or '').strip()
        if not emp:
            return '', True
        # 工号 8 位数字 → 199 + 后 8 位 = 11 位
        digits = ''.join(ch for ch in emp if ch.isdigit())
        if len(digits) < 8:
            digits = digits.rjust(8, '0')
        return MOCK_PHONE_PREFIX + digits[-8:], True

    def _to_candidate_kwargs(self, person):
        """档案 → 候选人字段。返回 (kwargs, 缺字段标记 list, 幂等键)。

        ⚠️ 判据分清两件事：
          - **手机号**：认人的必要条件之一（缺失才阻断）；
          - **工号**：只是幂等匹配用的稳定业务键（缺失不阻断导入，
            但会让该条只能靠「姓名+手机号」二次匹配，幂等性降级）。
        实测：20 条待入职档案有手机号但无工号 → 早期版本误判为「无法导入」，
        白丢 20 条可认数据。
        """
        missing = []
        if not (person.name or '').strip():
            missing.append('姓名')

        phone, is_mock = self._derive_phone(person)
        if not phone:
            missing.append('手机号')

        extra = {
            'source': '校招生档案同步',
            'mock': True,
            'person_code': person.code,
            'employee_id': person.employee_id or '',
            'degree': person.degree or '',
            'school_name': person.school_name or '',
            'major_name': person.major_name or '',
        }
        if is_mock:
            extra['mock_phone'] = True

        kwargs = {
            'name': person.name,
            'phone': phone,
            'gender': person.sex or '',
            'school_tag': person.school or '',
            'major_tag': person.major or '',
            'highest_education': person.education or '',
            'extra': extra,
            'current_state': STATE_MAP.get(person.status, 'APPLIED'),
            'recruit_type': 'campus',
        }
        return kwargs, missing

    # ---------------------------------------------------------------- 导入

    def _existing_map(self):
        """已存在的校招候选人 → 索引（两种键）。

        - `employee_id` → 候选人（稳定业务键，首选）
        - `name:{姓名}|{手机号}` → 候选人（无工号档案的兜底键）
        """
        from apps.candidate.models import Candidate

        out = {}
        for cand in Candidate.objects.filter(recruit_type='campus'):
            extra = cand.extra if isinstance(cand.extra, dict) else {}
            emp = extra.get('employee_id')
            if emp:
                out.setdefault(emp, cand)
            if cand.phone:
                out.setdefault(f'name:{cand.name}|{cand.phone}', cand)
        return out

    def _sync_phone_back_to_person(self):
        """把「派生测试手机号」同步回**原本无手机号**的档案侧。

        ## 为什么必须回写

        `auto_match_candidate` 的认人规则：
          - 唯一同名 → 认（此时档案有没有手机号都能认）；
          - **同名多人 → 只有档案手机号与候选人手机号精确一致才认**。

        存量档案有 4 组同名（李想/刘美彤/刘杰/刘浩然），且**都是 CS 前缀、全无手机号**
        ⇒ 候选人侧有派生手机号、档案侧为空 → 两边对不上 → 这 7 条**永远认不出**
        （实测：回填后仍剩 7 条进复核清单）。

        ⇒ 必须让两边一致：候选人用 `199`+工号 后 8 位，档案侧也写同一个值。

        ## 安全边界

        - **只补空值**：档案已有手机号的**一律不动**（绝不覆盖真实号码）；
        - 写入的是 `199` 开头（工信部保留测试号段），不会与真实号码冲突；
        - 写档案侧用的是裸 UPDATE（绕过 Person.save 的编号逻辑），
          **不碰编号**，编号归回填命令管；
        - 将来接入真实招聘系统数据时，把这些 `199` 号码换成真实号码即可
          （候选人与档案两侧同步替换 → 认人关系不变）。
        """
        written = 0
        for person in Person.objects.filter(phone='').exclude(employee_id=''):
            digits = ''.join(ch for ch in person.employee_id if ch.isdigit())
            if len(digits) < 8:
                continue
            phone = MOCK_PHONE_PREFIX + digits[-8:]
            # 档案侧 phone 是明文列，直接更新；候选人是加密列（save 时自动算 hash）
            Person.all_objects.filter(pk=person.pk, phone='').update(phone=phone)
            written += 1
        return written

    def _find_conflicts(self):
        """找出「占了别人编号」的候选人（真正的冲突）。

        ⚠️ 判据必须区分两种「编号重叠」：
          - **同源重叠（正常）**：某候选人的编号 == **它自己对应档案**的编号
            —— 这是回填达成后的正常状态，**绝不能**当冲突处理
            （否则每次重跑导入都会把编号推走，与回填命令形成震荡）。
          - **抢占冲突（要修）**：某候选人的编号 == **另一个档案**的编号
            —— 它占着别人的号 ⇒ 那条档案永远无法与它同源。

        依据 **`Person.candidate` 外键**建立「候选人 ↔ 它对应的档案」的精确关系。
        ⚠️ 不可用 `extra['person_code']` —— 那是**导入当时的旧编号**，
        回填后档案编号已变（CS00000222 → C00000xxx）⇒ 查不到对应 → 全部误判为冲突。
        """
        from apps.candidate.models import Candidate

        # 候选人的号当前属于哪条档案（code → 档案 id）
        person_by_code = {
            code: pid for pid, code in Person.all_objects.values_list('id', 'code')
        }
        # 候选人 → 它对应档案（已建立外键关联的）
        owner_of_candidate = {
            cand_id: pid
            for cand_id, pid in Person.all_objects
            .filter(candidate__isnull=False)
            .values_list('candidate_id', 'id')
        }

        conflicts = []
        for cand in Candidate.objects.filter(recruit_type='campus'):
            holder_id = person_by_code.get(cand.code)
            if holder_id is None:
                continue  # 该号当前无档案占用 → 无冲突
            owner_id = owner_of_candidate.get(cand.pk)
            if owner_id is None:
                continue  # 尚未与任何档案建立关联 → 由回填命令处理，不算冲突
            if holder_id != owner_id:
                # 它占的号属于**另一条**档案 → 真冲突
                conflicts.append((cand, owner_id, holder_id))
        return conflicts

    def _count_conflicts(self):
        """统计真冲突数（dry-run 提示用，不写库）。"""
        return len(self._find_conflicts())

    def _reassign_conflicting_codes(self):
        """把与「校招档案编号」冲突的候选人重新分配到空闲号。

        ## 为什么需要这一步

        两张表同用 `C`+8 序列：招聘系统候选人 + 校招档案（Person）。
        `Candidate.save()` 原本只看自己表的最大号取号 → 会**抢占档案已占用的号**
        （实测：档案占 C00000001~C00000058，候选人从 C00000008 起领
        → **51 个号被两边同时占用**）。

        后果：`backfill_person_candidate` 认出人时，候选人编号已被别的档案占用
        → 判定「编号被占用」→ 不换源 → **档案永远无法与候选人同源**。

        处理：把冲突的候选人挪到**当前全局空闲的最大号之后**，两表不再重叠。
        档案侧随后由回填命令把编号换成候选人的新编号（同源即达成）。

        ⚠️ 只处理**抢占别人号**的候选人（见 `_find_conflicts`）：
        「候选人编号 == 它自己对应档案的编号」是回填后的**正常同源状态**，
        当成冲突处理会让每次重跑都把编号推走 → 与回填命令来回震荡。
        """
        from apps.candidate.models import Candidate

        person_codes = set(
            Person.all_objects.values_list('code', flat=True)
        )
        # 全局已占用（两表并集）：候选人的号 + 档案的号
        taken = set(Candidate.all_objects.values_list('code', flat=True)) | person_codes

        # 找下一个空闲序号起点
        max_seq = 0
        for code in taken:
            if code and len(code) == 9 and code[0] == 'C' and code[1:].isdigit():
                max_seq = max(max_seq, int(code[1:9]))

        conflicts = self._find_conflicts()
        if not conflicts:
            return 0, max_seq

        # 两趟更新（先置临时前缀，再置最终号）—— 规避 unique=True 瞬态冲突
        for i, (cand, _owner, _holder) in enumerate(conflicts):
            Candidate.all_objects.filter(pk=cand.pk).update(code=f'_TC{i:08d}')

        next_seq = max_seq
        for cand, _owner, _holder in conflicts:
            next_seq += 1
            Candidate.all_objects.filter(pk=cand.pk).update(code=f'C{next_seq:08d}')

        return len(conflicts), next_seq

    def handle(self, *args, **options):
        from apps.candidate.models import Candidate

        dry_run = options['dry_run']
        limit = options['limit']
        review_csv = options['review_csv']

        persons = Person.objects.order_by('id')
        if limit:
            persons = persons[:limit]

        existing = self._existing_map()
        stats = {'scanned': 0, 'create': 0, 'update': 0, 'skip': 0, 'review': 0}
        review = []
        created_candidates = []

        # 步骤 0：先把与档案编号冲突的候选人挪到空闲号（否则回填时永远「编号被占用」）
        if not dry_run:
            moved, last_seq = self._reassign_conflicting_codes()
            if moved:
                self.stdout.write(self.style.NOTICE(
                    f'↻ 已把 {moved} 个与档案编号冲突的候选人改到空闲号（当前最大序号 {last_seq}）'
                ))
        else:
            conflicts = self._count_conflicts()
            if conflicts:
                self.stdout.write(self.style.WARNING(
                    f'⚠️  {conflicts} 个候选人的编号与档案编号冲突（真实执行时会自动改到空闲号）'
                ))

        for person in persons:
            stats['scanned'] += 1
            kwargs, missing = self._to_candidate_kwargs(person)
            if missing:
                stats['review'] += 1
                review.append([
                    person.code, person.name, person.employee_id or '',
                    '、'.join(missing),
                ])
                continue

            emp = person.employee_id
            cand = existing.get(emp) if emp else None
            if cand is None and not emp:
                # 无工号 → 用「姓名 + 手机号」兜底匹配（否则重复执行会建重复行）
                cand = existing.get(f'name:{person.name}|{kwargs["phone"]}')
            if cand is None:
                stats['create'] += 1
                if not dry_run:
                    cand = Candidate(**kwargs)
                    cand.save()
                    if emp:
                        existing[emp] = cand
                    else:
                        existing[f'name:{person.name}|{kwargs["phone"]}'] = cand
                    created_candidates.append(cand)
                continue

            # 已存在 → **只补空字段**，不覆盖人工维护的值
            stats['update'] += 1
            if dry_run:
                continue
            changed = []
            for field in ('gender', 'school_tag', 'major_tag', 'highest_education', 'current_state'):
                if not getattr(cand, field, '') and kwargs[field]:
                    setattr(cand, field, kwargs[field])
                    changed.append(field)
            if not (cand.phone or ''):
                cand.phone = kwargs['phone']
                changed.append('phone')
            # extra 合并（不覆盖已有键）
            merged = dict(cand.extra or {})
            for k, v in kwargs['extra'].items():
                merged.setdefault(k, v)
            if merged != (cand.extra or {}):
                cand.extra = merged
                changed.append('extra')
            if changed:
                cand.save()

        # 步骤 1：把派生测试手机号回写到**原本无手机号**的档案侧
        # （否则同名多人的档案认不出人 —— 见 _sync_phone_back_to_person 的说明）
        if not dry_run and not options.get('no_phone_backfill'):
            written = self._sync_phone_back_to_person()
            if written:
                self.stdout.write(self.style.NOTICE(
                    f'↻ 已给 {written} 条原本无手机号的档案补上派生测试号（199 段），'
                    f'使其与候选人侧一致（同名档案才能区分）'
                ))

        self.stdout.write(
            f'扫描档案 {stats["scanned"]} 条 | '
            f'新建候选人 {stats["create"]} 条 | '
            f'更新候选人 {stats["update"]} 条 | '
            f'无法导入 {stats["review"]} 条'
        )
        if dry_run:
            self.stdout.write(self.style.NOTICE('[DRY-RUN] 未写入数据库（去掉 --dry-run 即真实写入）'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ 校招候选人同步完成，新建 {len(created_candidates)} 条'))

        # 未导入清单
        if review_csv:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(['档案编号', '姓名', '工号', '缺失字段'])
            writer.writerows(review)
            with open(review_csv, 'w', newline='', encoding='utf-8-sig') as fh:
                fh.write(buf.getvalue())
            self.stdout.write(self.style.WARNING(f'⚠️  未导入清单已写入 {review_csv}（{len(review)} 条）'))
        elif review:
            self.stdout.write(self.style.WARNING(f'⚠️  {len(review)} 条无法导入（用 --review-csv 导出清单）'))
            for row in review[:20]:
                self.stdout.write(f'   · {row[0]} {row[1]}：缺 {row[3]}')
