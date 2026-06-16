"""
加载预置流程模板
Load Predefined Process Templates

读取 seeds/*.json 中的模板数据，自动创建：
- RecruitmentProcess（流程）
- ProcessStageLink（流程-阶段关联）
- StageRule（阶段规则）
- ProcessTemplate（流程模板）
- EntryConditionRule（进入条件规则，引用 EntryConditionRule）
- TimeLimitRule（阶段限时规则）
- AutomationRule（自动化规则）
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


SEEDS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / 'seeds'

# 模板文件顺序（按依赖）
TEMPLATE_FILES = [
    '03_social_tech_template.json',
    '04_campus_general_template.json',
    '05_headhunter_senior_template.json',
    '06_internal_transfer_template.json',
]


class Command(BaseCommand):
    help = 'Load 4 predefined process templates (社招-技术 / 校招-通用 / 猎头-高级 / 内部转岗)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='清空已存在的预置模板再重新创建',
        )
        parser.add_argument(
            '--file', type=str, default=None,
            help='只加载指定文件，例如 03_social_tech_template.json',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='只校验 JSON 不写入数据库',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.process.models import (
            ProcessStageLink,
            ProcessTemplate,
            RecruitmentProcess,
            RecruitmentStage,
            StageRule,
        )
        from apps.entry_condition.models import EntryConditionRule
        from apps.time_limit.models import TimeLimitRule
        from apps.automation.models import AutomationRule

        if options['reset']:
            self.stdout.write(self.style.WARNING('删除已有预置模板...'))
            ProcessTemplate.objects.filter(is_builtin=True).delete()
            RecruitmentProcess.objects.filter(is_template=True, template_code__in=[
                'SOCIAL_TECH', 'CAMPUS_GENERAL', 'HEADHUNTER_SENIOR', 'INTERNAL_TRANSFER'
            ]).delete()

        # 阶段字典
        stages = {s.code: s for s in RecruitmentStage.objects.all()}
        if not stages:
            raise CommandError(
                '阶段库为空！请先执行: python manage.py loaddata seeds/01_system_stages.json'
            )

        # 选择文件
        files = [options['file']] if options['file'] else TEMPLATE_FILES
        for fname in files:
            path = SEEDS_DIR / fname
            if not path.exists():
                self.stdout.write(self.style.ERROR(f'文件不存在: {path}'))
                continue
            self.load_template(path, stages, options['dry_run'])

        self.stdout.write(self.style.SUCCESS('所有模板加载完成'))

    def load_template(self, path: Path, stages: dict, dry_run: bool = False):
        from apps.process.models import (
            ProcessStageLink, ProcessTemplate, RecruitmentProcess, StageRule,
        )
        from apps.entry_condition.models import EntryConditionRule
        from apps.time_limit.models import TimeLimitRule
        from apps.automation.models import AutomationRule

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stdout.write(f'\n加载模板: {data["name"]} ({data["code"]})')

        if dry_run:
            self.stdout.write(self.style.NOTICE('  [DRY-RUN] 仅校验，不写入'))
            return

        # 1. 创建 RecruitmentProcess
        process, created = RecruitmentProcess.objects.update_or_create(
            template_code=data['code'],
            defaults={
                'name': data['name'],
                'code': f'W{self._next_process_code()}',
                'is_template': True,
                'is_enabled': True,
                'current_version': '1.0',
                'applicable_scope': data['snapshot'].get('applicable_scope', {}),
                'description': data['description'],
                'status': 'ENABLED',
            }
        )
        self.stdout.write(f'  流程: {process.name} ({"新建" if created else "已存在"})')

        # 2. 创建 ProcessTemplate
        template, _ = ProcessTemplate.objects.update_or_create(
            code=data['code'],
            defaults={
                'name': data['name'],
                'description': data['description'],
                'category': data['category'],
                'snapshot': data['snapshot'],
                'is_builtin': True,
                'is_active': True,
            }
        )
        self.stdout.write(f'  模板: {template.name}')

        # 3. 创建 ProcessStageLink + StageRule
        link_count = 0
        for stage_def in data['snapshot']['stages']:
            stage = stages.get(stage_def['stage_code'])
            if not stage:
                self.stdout.write(self.style.WARNING(
                    f'    跳过: 阶段 {stage_def["stage_code"]} 不存在'
                ))
                continue

            link, _ = ProcessStageLink.objects.update_or_create(
                process=process, stage=stage,
                defaults={
                    'order': stage_def['order'],
                    'is_required': stage_def.get('is_required', True),
                    'entry_rule_expression': self._build_expression(stage_def.get('entry_rules', [])),
                }
            )

            # StageRule
            rule_def = stage_def.get('rule', {})
            StageRule.objects.update_or_create(
                link=link,
                defaults={
                    'processing_rule': rule_def.get('processing_rule', 'DIRECT'),
                    'data_source': rule_def.get('data_source', ''),
                    'data_field': rule_def.get('data_field', ''),
                    'interview_rounds': rule_def.get('interview_rounds', 1),
                    'interview_format': rule_def.get('interview_format', 'SINGLE'),
                    'is_grab_mode': rule_def.get('processing_rule') == 'ROUND_ROBIN',
                    'grab_threshold': rule_def.get('grab_threshold', 30),
                    'auto_skip_n_plus_two': rule_def.get('auto_skip_n_plus_two', False),
                    'inherit_prior_consensus': rule_def.get('inherit_prior_consensus', False),
                }
            )
            link_count += 1

            # TimeLimitRule
            if 'time_limit_days' in rule_def:
                TimeLimitRule.objects.update_or_create(
                    link=link, name=f'{stage.name} 默认限时',
                    defaults={
                        'time_limit_days': rule_def['time_limit_days'],
                        'effective_scope': 'ALL',
                        'status': 'ENABLED',
                        'priority': 100,
                    }
                )

            # EntryConditionRule
            for idx, cond in enumerate(stage_def.get('entry_rules', []), 1):
                EntryConditionRule.objects.update_or_create(
                    link=link, name=f'{stage.name} 规则{idx}',
                    defaults={
                        'rule_json': [cond],
                        'logic': 'ALL',
                        'enabled': True,
                    }
                )

        self.stdout.write(f'  阶段-规则关联: {link_count} 条')

        # 4. AutomationRule
        for rule_def in data['snapshot'].get('automation_rules', []):
            stage = stages.get(rule_def.get('stage_code'))
            if not stage:
                continue
            AutomationRule.objects.update_or_create(
                name=rule_def['name'],
                process=process, stage=stage,
                defaults={
                    'trigger_type': rule_def.get('trigger_type', 'STAGE_ENTERED'),
                    'trigger_timing': rule_def.get('trigger_timing', 'IMMEDIATE'),
                    'condition_json': [rule_def.get('condition', '')],
                    'action_type': rule_def.get('action_type', 'AUTO_ADVANCE'),
                    'priority': rule_def.get('priority', 'P1'),
                    'enabled': rule_def.get('enabled', True),
                    'skip_check': rule_def.get('skip_check', False),
                }
            )
        self.stdout.write(f'  自动化规则: {len(data["snapshot"].get("automation_rules", []))} 条')

    def _build_expression(self, rules: list) -> str:
        if not rules:
            return ''
        return ' AND '.join(str(i + 1) for i in range(len(rules)))

    def _next_process_code(self) -> str:
        from apps.process.models import RecruitmentProcess
        existing = RecruitmentProcess.objects.filter(code__startswith='W').count()
        return f'{existing + 1:03d}'
