"""流程模板应用服务

将 ProcessTemplate.snapshot 还原为完整的 RecruitmentProcess：
- 创建流程主记录
- 遍历 snapshot.stages 创建 ProcessStageLink
- 还原 stage_rule
- 还原 entry_condition_rules + condition_items
- 还原 time_limit_rules
- 还原 automation_rules
"""
from __future__ import annotations

import logging
from copy import deepcopy
from typing import List

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@transaction.atomic
def apply_template_to_process(template, name: str, code: str, actor=None):
    """从模板创建流程"""
    from apps.entry_condition.models import (
        ConditionItem,
        EntryConditionRule,
    )
    from apps.time_limit.models import TimeLimitRule
    from apps.automation.models import AutomationRule

    from .models import (
        ProcessStageLink,
        RecruitmentProcess,
        StageRule,
    )

    snapshot = template.snapshot or {}
    stages_data = snapshot.get('stages', [])
    rules_data = snapshot.get('rules', {})
    if not stages_data:
        raise ValueError('模板快照为空，无法应用')

    # 1. 创建流程
    process = RecruitmentProcess.objects.create(
        code=code,
        name=name,
        current_version='V1.0',
        applicable_scope=deepcopy(snapshot.get('applicable_scope', {})),
        is_template=False,
        template_code=template.code,
        is_enabled=True,
        validate_resume_score=snapshot.get('validate_resume_score', True),
        description=f'从模板「{template.name}」创建',
        status='ENABLED',
        created_by=actor,
        updated_by=actor,
    )

    # 2. 遍历 stage_data 创建 link + rule
    for stage_data in stages_data:
        stage_id = stage_data.get('stage_id')
        if not stage_id:
            continue

        link = ProcessStageLink.objects.create(
            process=process,
            stage_id=stage_id,
            order=stage_data.get('order', 0),
            is_required=stage_data.get('is_required', True),
            entry_rule_expression=stage_data.get('entry_rule_expression', ''),
            created_by=actor,
            updated_by=actor,
        )

        # 3. 创建 stage_rule
        rule_data = stage_data.get('stage_rule')
        if rule_data:
            StageRule.objects.create(
                link=link,
                data_source=rule_data.get('data_source', ''),
                data_field=rule_data.get('data_field', ''),
                processing_rule=rule_data.get('processing_rule', 'DIRECT'),
                processor_order=rule_data.get('processor_order', []),
                auto_skip_n_plus_two=rule_data.get('auto_skip_n_plus_two', False),
                inherit_prior_consensus=rule_data.get('inherit_prior_consensus', False),
                is_grab_mode=rule_data.get('is_grab_mode', False),
                grab_threshold=rule_data.get('grab_threshold', 30),
                interview_rounds=rule_data.get('interview_rounds', 1),
                interview_format=rule_data.get('interview_format', ''),
                created_by=actor,
                updated_by=actor,
            )

        # 4. 创建 entry_condition_rules
        for ec_data in stage_data.get('entry_condition_rules', []):
            ec_rule = EntryConditionRule.objects.create(
                link=link,
                process_id=process.id,
                workflow_version=process.current_version,
                rule_name=ec_data.get('rule_name', ''),
                rule_seq=ec_data.get('rule_seq', 1),
                status=ec_data.get('status', 'ENABLED'),
                expression=ec_data.get('expression', '1'),
                reject_message=ec_data.get('reject_message', ''),
                created_by=actor,
                updated_by=actor,
            )
            for ci_data in ec_data.get('items', []):
                ConditionItem.objects.create(
                    rule=ec_rule,
                    item_seq=ci_data.get('item_seq', 1),
                    condition_type=ci_data.get('condition_type', 'CANDIDATE'),
                    field=ci_data.get('field', ''),
                    stage_name=ci_data.get('stage_name', ''),
                    stage_statuses=ci_data.get('stage_statuses', []),
                    operator=ci_data.get('operator', 'EQ'),
                    value=ci_data.get('value'),
                    auto_filter_inactive_users=ci_data.get('auto_filter_inactive_users', False),
                )

    # 5. 创建 time_limit_rules
    for tl_data in rules_data.get('time_limit_rules', []):
        link_id = tl_data.get('link_id')  # 可能是模板里的占位 id
        # 真实 link 可能是按顺序匹配第一个匹配的 stage
        # 这里简化：按 stage_name 匹配
        stage_name = tl_data.get('stage_name')
        if not stage_name:
            continue
        link = ProcessStageLink.objects.filter(
            process=process, stage__name=stage_name,
        ).first()
        if not link:
            continue
        TimeLimitRule.objects.create(
            link=link,
            process_id=process.id,
            workflow_version=process.current_version,
            rule_name=tl_data.get('rule_name', ''),
            conditions=tl_data.get('conditions', []),
            lock_duration=tl_data.get('lock_duration', 30),
            extension_per_person=tl_data.get('extension_per_person', 0),
            effective_scope=tl_data.get('effective_scope', 'NEW_ONLY'),
            priority=tl_data.get('priority', 0),
            enabled=tl_data.get('enabled', True),
            created_by=actor,
            updated_by=actor,
        )

    # 6. 创建 automation_rules
    for au_data in rules_data.get('automation_rules', []):
        stage_name = au_data.get('stage_name')
        if not stage_name:
            continue
        link = ProcessStageLink.objects.filter(
            process=process, stage__name=stage_name,
        ).first()
        if not link:
            continue
        next_stage_name = au_data.get('next_stage_name')
        next_stage = None
        if next_stage_name:
            from .models import RecruitmentStage
            next_stage = RecruitmentStage.objects.filter(name=next_stage_name).first()
        AutomationRule.objects.create(
            name=au_data.get('name', ''),
            process=process,
            stage=link.stage,
            trigger_type=au_data.get('trigger_type', 'STAGE_ENTERED'),
            trigger_timing=au_data.get('trigger_timing', 'IMMEDIATE'),
            trigger_delay_hours=au_data.get('trigger_delay_hours'),
            condition_logic=au_data.get('condition_logic', 'ALL'),
            condition_json=au_data.get('condition_json', []),
            action_type=au_data.get('action_type', 'AUTO_ADVANCE'),
            next_stage=next_stage,
            skip_check=au_data.get('skip_check', False),
            scope_json=au_data.get('scope_json', {}),
            priority=au_data.get('priority', 'P1'),
            enabled=au_data.get('enabled', True),
            failure_rate_threshold=au_data.get('failure_rate_threshold', 0.5),
            created_by=actor,
            updated_by=actor,
        )

    logger.info('Template %s applied to new process %s', template.code, process.id)
    return process


def export_process_to_template_snapshot(process) -> dict:
    """把现有流程导出为模板快照（用于"另存为模板"）"""
    from apps.entry_condition.models import (
        ConditionItem,
        EntryConditionRule,
    )
    from apps.time_limit.models import TimeLimitRule
    from apps.automation.models import AutomationRule

    stages = []
    for link in process.stage_links.filter(deleted_at__isnull=True).order_by('order'):
        stage_data = {
            'stage_id': link.stage_id,
            'order': link.order,
            'is_required': link.is_required,
            'entry_rule_expression': link.entry_rule_expression,
        }
        if hasattr(link, 'stage_rule'):
            r = link.stage_rule
            stage_data['stage_rule'] = {
                'data_source': r.data_source,
                'data_field': r.data_field,
                'processing_rule': r.processing_rule,
                'processor_order': r.processor_order,
                'auto_skip_n_plus_two': r.auto_skip_n_plus_two,
                'inherit_prior_consensus': r.inherit_prior_consensus,
                'is_grab_mode': r.is_grab_mode,
                'grab_threshold': r.grab_threshold,
                'interview_rounds': r.interview_rounds,
                'interview_format': r.interview_format,
            }
        # 进入条件
        stage_data['entry_condition_rules'] = []
        for ec in link.entry_condition_rules.filter(deleted_at__isnull=True):
            items = []
            for ci in ec.items.all():
                items.append({
                    'item_seq': ci.item_seq,
                    'condition_type': ci.condition_type,
                    'field': ci.field,
                    'stage_name': ci.stage_name,
                    'stage_statuses': ci.stage_statuses,
                    'operator': ci.operator,
                    'value': ci.value,
                    'auto_filter_inactive_users': ci.auto_filter_inactive_users,
                })
            stage_data['entry_condition_rules'].append({
                'rule_name': ec.rule_name,
                'rule_seq': ec.rule_seq,
                'status': ec.status,
                'expression': ec.expression,
                'reject_message': ec.reject_message,
                'items': items,
            })
        stages.append(stage_data)

    time_limits = []
    for tl in TimeLimitRule.objects.filter(process_id=process.id, deleted_at__isnull=True):
        time_limits.append({
            'stage_name': tl.link.stage.name if tl.link_id else None,
            'rule_name': tl.rule_name,
            'conditions': tl.conditions,
            'lock_duration': tl.lock_duration,
            'extension_per_person': tl.extension_per_person,
            'effective_scope': tl.effective_scope,
            'priority': tl.priority,
            'enabled': tl.enabled,
        })

    automations = []
    for au in AutomationRule.objects.filter(process=process, deleted_at__isnull=True):
        automations.append({
            'stage_name': au.stage.name,
            'name': au.name,
            'trigger_type': au.trigger_type,
            'trigger_timing': au.trigger_timing,
            'trigger_delay_hours': au.trigger_delay_hours,
            'condition_logic': au.condition_logic,
            'condition_json': au.condition_json,
            'action_type': au.action_type,
            'next_stage_name': au.next_stage.name if au.next_stage_id else None,
            'skip_check': au.skip_check,
            'scope_json': au.scope_json,
            'priority': au.priority,
            'enabled': au.enabled,
        })

    return {
        'applicable_scope': process.applicable_scope,
        'validate_resume_score': process.validate_resume_score,
        'stages': stages,
        'rules': {
            'time_limit_rules': time_limits,
            'automation_rules': automations,
        }
    }
