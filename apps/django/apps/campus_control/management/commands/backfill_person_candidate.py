"""存量校招生档案 · 编号回填到「招聘系统 · 候选人管理」（2026-10-23）

背景（兵哥口径：**编号自动获取，不需要人工选候选人**）:
  `PersonSerializer.create/update` 已实现在**新建/编辑**时自动认人并把档案编号换成候选人编号,
  但**存量数据**（本命令上线前就入库的档案）没有 candidate 关联、编号还是本地补的 C 序号
  ⇒ 招聘系统里「C00000001」和人员管理里「C00000001」可能指两个人 → 对不上账。

本命令做存量回填:
  - **匹配口径与新建/编辑完全一致** —— 直接复用 `serializers.auto_match_candidate`（唯一真源）,
    不另写一套匹配逻辑（另写一套必然漂移: 新建认得出、回填认不出, 反而制造新的不一致）。
  - 只改「编号来源」, 不改其他业务字段（姓名/部门/状态/入职日期…一律不动）。

分三类处理:
  1. **未关联候选人的档案** → 按 姓名(+手机号) 认人; 认得出且目标编号未被占用 → 关联 + 换编号;
  2. **已关联候选人但编号不一致的档案** → **不换人**, 只把编号纠正回该候选人的编号
     （对齐 `_auto_candidate` 的「已认定过, 不换人」; 换人会让档案挂到别人头上）;
  3. **认不出 / 目标编号已被占用 / 候选人已被别的档案关联** → 不动, 进人工复核清单
     （⚠️ 绝不猜人, 也绝不撞 unique 约束）。

安全设计:
  - **默认 dry-run**: 不带 `--apply` 只统计并出清单, 零写库。`--apply` 才真正写。
  - **人工复核清单**: 导 CSV 供人工在「候选人管理」侧确认后再处理。
  - **幂等**: 已同源的档案直接跳过, 可重复跑。
  - **写入用两趟 UPDATE**（先置临时前缀再置目标码）, 规避 unique=True 的瞬态冲突
     —— 与既有 `renumber_persons` 同款。
  - **占用判定用 `all_objects`**（含软删行）: code 的唯一索引覆盖软删行,
    只看活行会漏判占用 → UPDATE 时撞 IntegrityError。

用法:
  python manage.py backfill_person_candidate                       # dry-run（默认）
  python manage.py backfill_person_candidate --apply                # 真正回填
  python manage.py backfill_person_candidate --apply --review-csv /tmp/review.csv
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = '存量校招生档案编号回填: 关联「招聘系统 · 候选人管理」并把编号换成候选人编号'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='真正写库（默认只 dry-run 统计并出人工复核清单, 零写入）',
        )
        parser.add_argument(
            '--review-csv', type=str, default=None,
            help='人工复核清单 CSV 输出路径（认不出 / 编号被占用 / 候选人被占用的行）',
        )

    # ---------------------------------------------------------------- 扫描

    def _collect(self):
        """扫描待回填的档案, 返回 (可回填列表, 复核清单, 统计)。"""
        from apps.campus_control.models import Person
        from apps.campus_control.serializers import auto_match_candidate

        stats = {
            'scanned': 0,
            'already_same': 0,   # 已同源（编号 == 候选人编号）→ 跳过
            'will_link': 0,       # 新关联候选人
            'will_fix': 0,        # 已关联, 只纠正编号
            'review': 0,          # 进人工复核清单
        }
        todo = []      # [(person, cand, is_link)]
        review = []    # [[档案编号, 姓名, 电话, 候选人编号, 原因, 说明]]
        taken_codes = set()   # 本批次内已被占用的目标编号（防止两条档案抢同一个号）

        persons = Person.objects.select_related('candidate').order_by('id')
        for person in persons:
            stats['scanned'] += 1

            # ---- 情形 2: 已关联候选人 → 只纠正编号, 不换人 ----
            if person.candidate_id:
                cand = person.candidate
                if cand is None or not cand.code:
                    stats['already_same'] += 1
                    continue
                if cand.code == person.code:
                    stats['already_same'] += 1
                    continue
                blocked = self._occupied_by_other(person, cand.code)
                if blocked is not None:
                    stats['review'] += 1
                    review.append(self._review_row(
                        person, cand.code, '候选人编号已被占用',
                        f'编号 {cand.code} 已被档案「{blocked.name}」({blocked.code}) 占用',
                    ))
                    continue
                if cand.code in taken_codes:
                    stats['review'] += 1
                    review.append(self._review_row(
                        person, cand.code, '同批次目标编号重复',
                        f'本批次内已有另一条档案要占用 {cand.code}',
                    ))
                    continue
                taken_codes.add(cand.code)
                stats['will_fix'] += 1
                todo.append((person, cand, False))
                continue

            # ---- 情形 1: 未关联 → 按 姓名(+手机号) 认人 ----
            cand = auto_match_candidate(person.name, person.phone)
            if cand is None:
                stats['review'] += 1
                review.append(self._review_row(
                    person, '', '认不出候选人',
                    '候选人管理里无「唯一同名且手机号一致」的候选人（宁不同源, 也不挂错人）',
                ))
                continue

            blocked = self._occupied_by_other(person, cand.code)
            if blocked is not None:
                stats['review'] += 1
                review.append(self._review_row(
                    person, cand.code, '候选人编号已被占用',
                    f'编号 {cand.code} 已被档案「{blocked.name}」({blocked.code}) 占用',
                ))
                continue

            # 一个候选人只能对应一个档案
            linked = None
            if hasattr(cand, 'campus_persons'):
                linked = cand.campus_persons.exclude(pk=person.pk).first()
            if linked is not None:
                stats['review'] += 1
                review.append(self._review_row(
                    person, cand.code, '候选人已被其他档案关联',
                    f'候选人 {cand.code} 已关联档案「{linked.name}」({linked.code})',
                ))
                continue

            if cand.code in taken_codes:
                stats['review'] += 1
                review.append(self._review_row(
                    person, cand.code, '同批次目标编号重复',
                    f'本批次内已有另一条档案要占用 {cand.code}',
                ))
                continue

            taken_codes.add(cand.code)
            stats['will_link'] += 1
            todo.append((person, cand, True))

        return todo, review, stats

    def _occupied_by_other(self, person, code):
        """目标编号是否已被**别的**档案占用（含软删行 —— 唯一索引覆盖软删行）。

        返回占用者 Person 实例, 未被占用返回 None。
        """
        from apps.campus_control.models import Person

        return (
            Person.all_objects.filter(code=code).exclude(pk=person.pk).first()
        )

    def _review_row(self, person, cand_code, reason, detail):
        from apps.common.masking import mask_phone

        return [
            person.code,
            person.name,
            mask_phone(person.phone),
            cand_code,
            reason,
            detail,
        ]

    # ---------------------------------------------------------------- 写入

    @transaction.atomic
    def _apply(self, todo):
        """写库: 关联候选人 + 编号换成候选人编号（两趟 UPDATE 规避 unique 瞬态冲突）。"""
        from apps.campus_control.models import Person

        now = timezone.now()
        # 第一趟: 置临时前缀（_TBF + 序号）, 把目标编号腾出来
        for i, (person, cand, is_link) in enumerate(todo):
            Person.all_objects.filter(pk=person.pk).update(
                code=f'_TBF{i:08d}', updated_at=now,
            )

        # 第二趟: 写最终编号（+ 关联候选人）
        for i, (person, cand, is_link) in enumerate(todo):
            fields = {'code': cand.code, 'updated_at': now}
            if is_link:
                fields['candidate'] = cand
            Person.all_objects.filter(pk=person.pk).update(**fields)

        return len(todo)

    # ---------------------------------------------------------------- 输出

    def _write_review_csv(self, path, review):
        """导出人工复核清单（CSV Injection 防护走 SafeCsvWriter）。"""
        import io

        from apps.common.csv_safe import SafeCsvWriter

        buf = io.StringIO()
        writer = SafeCsvWriter(buf)
        writer.writerow([
            '档案编号', '姓名', '联系电话', '候选人编号', '未回填原因', '说明',
        ])
        writer.writerows(review)
        with open(path, 'w', newline='', encoding='utf-8-sig') as fh:
            fh.write(buf.getvalue())
        return len(review)

    def handle(self, *args, **options):
        apply = options['apply']
        review_csv = options['review_csv']

        todo, review, stats = self._collect()

        self.stdout.write(
            f'扫描档案 {stats["scanned"]} 条 | '
            f'新关联 {stats["will_link"]} 条 | '
            f'纠正编号 {stats["will_fix"]} 条 | '
            f'需人工复核 {stats["review"]} 条 | '
            f'已同源跳过 {stats["already_same"]} 条'
        )

        if not apply:
            self.stdout.write(self.style.NOTICE('[DRY-RUN] 未写入数据库（加 --apply 才真正回填）'))
        elif todo:
            done = self._apply(todo)
            self.stdout.write(self.style.SUCCESS(f'✅ 已回填 {done} 条档案编号'))

        # 人工复核清单
        # ⚠️ 即使清单为空也要落文件（表头齐全）——
        #   运维按「文件存在 = 本次已跑过」判断; 空清单则文件内容为空表,
        #   避免「跑第二遍 → 文件消失 → 脚本误判命令没执行」。
        if review_csv:
            n = self._write_review_csv(review_csv, review)
            self.stdout.write(self.style.WARNING(
                f'⚠️  人工复核清单已写入 {review_csv}（{n} 条）'
            ))
        elif review:
            self.stdout.write(self.style.WARNING(
                f'⚠️  {len(review)} 条需人工复核（用 --review-csv <路径> 导出清单）'
            ))
            for row in review[:20]:
                self.stdout.write(f'   · {row[0]} {row[1]} → {row[3]}：{row[4]}（{row[5]}）')
            if len(review) > 20:
                self.stdout.write(f'   … 另有 {len(review) - 20} 条')
        else:
            self.stdout.write(self.style.SUCCESS('无需人工复核的条目'))
