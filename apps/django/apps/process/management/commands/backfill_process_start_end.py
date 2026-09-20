"""
回填存量招聘流程的起止阶段关联 (Start/End ProcessStageLink)

背景:
  新建流程时 RecruitmentStageSerializer.create() 会自动注入初评(P001, is_start) 与
  正式录用(P099, is_end) 两条 ProcessStageLink (is_mandatory=True)。但该逻辑只在
  create() 内执行, 早于该特性 (commit 3ff8220) 创建、或经非 create 路径产生的流程
  缺这两条 link → 起止阶段在流程内不出现。

  2026-09-20 起止阶段改为「系统内置」: 初评/正式录用由迁移 0012 幂等预置为
  is_builtin + is_start/is_end 的全局唯一阶段。本命令把这两个阶段回填进存量流程的
  ProcessStageLink, 闭合「存量流程缺起止 link」的生产缺口 (BR-001)。

特性:
  - 幂等: 每个流程先 exists() 再建, 可重跑无害。
  - --dry-run: 只统计/打印将创建的条数, 不写库。
  - 取全局唯一起止阶段 (与 create() 同口径, 规避 code 漂移)。
  - 回填后 renormalize_process_orders 归一化顺序 (start 最前 / end 最后)。

用法:
  python manage.py backfill_process_start_end            # 真实回填
  python manage.py backfill_process_start_end --dry-run  # 仅统计
"""
from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '回填存量招聘流程缺失的起止阶段关联 (初评/正式录用)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='只统计将创建的条数, 不写入数据库',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.process.models import (
            ProcessStageLink,
            RecruitmentProcess,
            RecruitmentStage,
        )
        from apps.process.serializers import renormalize_process_orders

        dry_run = options['dry_run']

        # 全局唯一起止阶段 (与 create() 同口径)
        start_stage = RecruitmentStage.objects.filter(
            is_start=True, deleted_at__isnull=True,
        ).first()
        end_stage = RecruitmentStage.objects.filter(
            is_end=True, deleted_at__isnull=True,
        ).first()
        if not start_stage or not end_stage:
            raise CommandError(
                '找不到系统内置起止阶段! 请先执行迁移 0012 预置初评/正式录用 '
                '(is_start/is_end)。'
            )

        # 所有未软删的流程 (含模板, 幂等无害)
        processes = RecruitmentProcess.objects.filter(
            deleted_at__isnull=True,
        ).select_related()

        total = processes.count()
        missing_start = 0
        missing_end = 0
        fixed_start = 0
        fixed_end = 0

        self.stdout.write(
            f'扫描流程 {total} 个 | 起止阶段: '
            f'{start_stage.code}({start_stage.name}) / {end_stage.code}({end_stage.name})'
        )
        if dry_run:
            self.stdout.write(self.style.NOTICE('[DRY-RUN] 仅统计, 不写入'))

        for proc in processes:
            # 注意: 唯一约束 (process_id, stage_id) 在 DB 层不考虑软删,
            # 故「缺」须同时排除「软删的旧 link 占槽」——有软删行则复活而非新建。
            start_link = ProcessStageLink.objects.filter(
                process=proc, stage=start_stage,
            ).first()
            end_link = ProcessStageLink.objects.filter(
                process=proc, stage=end_stage,
            ).first()

            if start_link and start_link.deleted_at is None \
                    and end_link and end_link.deleted_at is None:
                continue  # 起止均活跃, 跳过

            if not (start_link and start_link.deleted_at is None):
                missing_start += 1
                if not dry_run:
                    if start_link and start_link.deleted_at is not None:
                        start_link.deleted_at = None  # 复活软删旧行
                        start_link.is_mandatory = True
                        start_link.order = 0
                        start_link.save(
                            update_fields=['deleted_at', 'is_mandatory', 'order'])
                    else:
                        ProcessStageLink.objects.create(
                            process=proc, stage=start_stage,
                            order=0, is_mandatory=True,
                        )
                    fixed_start += 1

            if not (end_link and end_link.deleted_at is None):
                missing_end += 1
                if not dry_run:
                    if end_link and end_link.deleted_at is not None:
                        end_link.deleted_at = None
                        end_link.is_mandatory = True
                        end_link.save(update_fields=['deleted_at', 'is_mandatory'])
                    else:
                        max_order = ProcessStageLink.objects.filter(
                            process=proc, deleted_at__isnull=True,
                        ).aggregate(m=Max('order'))['m'] or -1
                        ProcessStageLink.objects.create(
                            process=proc, stage=end_stage,
                            order=max_order + 1, is_mandatory=True,
                        )
                    fixed_end += 1

            # 归一化顺序 (start 最前 / end 最后 / 其余连续)
            if not dry_run:
                renormalize_process_orders(proc)

        # 汇总
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY-RUN] 将修复: 缺初评 {missing_start} 个流程, '
                f'缺正式录用 {missing_end} 个流程'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'回填完成: 修复初评 link {fixed_start} 条, '
                f'修复正式录用 link {fixed_end} 条'
            ))
            if fixed_start == 0 and fixed_end == 0:
                self.stdout.write(self.style.SUCCESS('无缺失, 无需回填'))
