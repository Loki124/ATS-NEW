"""流程版本管理服务（PRD v4 §9.2 BR-101~BR-105）

业务规则：
- BR-101: 流程被至少一个职位需求引用后，配置修改将生成新版本
- BR-102: 已在跑的候选人走创建时的版本
- BR-103: 历史版本只读
- BR-104: 支持历史候选人"升版本"到最新版本
- BR-105: 流程无草稿态，配置即时生效
- BR-106: 流程无停用态，只能归档
"""
from __future__ import annotations

import logging
from copy import deepcopy
from typing import List, Tuple

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def is_process_referenced(process) -> bool:
    """判断流程是否被职位需求引用"""
    return process.demands.filter(deleted_at__isnull=True).exists()


@transaction.atomic
def archive_process(process, actor=None) -> dict:
    """归档流程（替代停用）

    Returns:
        {'archived': True, 'reference_count': int}
    """
    if process.status == 'ARCHIVED':
        return {'archived': True, 'reference_count': is_process_referenced(process)}

    process.status = 'ARCHIVED'
    process.archived_at = timezone.now()
    process.save(update_fields=['status', 'archived_at', 'updated_at'])

    logger.info('Process %s archived by %s', process.id, actor)

    return {
        'archived': True,
        'reference_count': process.reference_count,
        'archived_at': process.archived_at.isoformat(),
    }


@transaction.atomic
def bump_version(process, new_version: str = None) -> str:
    """生成新版本号

    Args:
        process: RecruitmentProcess 实例
        new_version: 自定义版本号，默认 V{N+1}.0

    Returns:
        新版本字符串
    """
    if new_version is None:
        # 解析当前版本如 "V1.2" → "V1.3"
        cur = process.current_version or 'V1.0'
        if cur.startswith('V') and '.' in cur:
            major, minor = cur[1:].split('.', 1)
            new_version = f'V{major}.{int(minor) + 1}'
        else:
            new_version = f'{cur}+1'

    process.current_version = new_version
    process.save(update_fields=['current_version', 'updated_at'])
    logger.info('Process %s version bumped to %s', process.id, new_version)
    return new_version


@transaction.atomic
def clone_process_with_new_version(
    process,
    new_name: str = None,
    actor=None,
) -> 'RecruitmentProcess':
    """克隆流程并生成新版本（深拷贝所有 stage_links 和 stage_rules）

    用于：
    - 引用中流程的配置修改（PRD BR-101）
    - 历史候选人"升版本"（BR-104）
    """
    from .models import (
        ProcessStageLink,
        RecruitmentProcess,
        StageRule,
    )

    new_version = bump_version(process)

    # 创建新流程
    new_process = RecruitmentProcess.objects.create(
        code=process.code,  # 编号不变，新版本是同一流程
        name=new_name or f'{process.name} ({new_version})',
        current_version=new_version,
        applicable_scope=deepcopy(process.applicable_scope),
        is_template=process.is_template,
        template_code=process.template_code,
        is_enabled=process.is_enabled,
        validate_resume_score=process.validate_resume_score,
        description=process.description,
        status='ENABLED',
        created_by=actor,
        updated_by=actor,
    )

    # 克隆所有 stage_links
    for link in process.stage_links.all():
        new_link = ProcessStageLink.objects.create(
            process=new_process,
            stage=link.stage,
            order=link.order,
            is_required=link.is_required,
            entry_rule_expression=link.entry_rule_expression,
            created_by=actor,
            updated_by=actor,
        )
        # 克隆 stage_rule
        if hasattr(link, 'stage_rule'):
            old_rule = link.stage_rule
            StageRule.objects.create(
                link=new_link,
                data_source=old_rule.data_source,
                data_field=old_rule.data_field,
                processing_rule=old_rule.processing_rule,
                processor_order=deepcopy(old_rule.processor_order),
                current_processor_index=old_rule.current_processor_index,
                auto_skip_n_plus_two=old_rule.auto_skip_n_plus_two,
                inherit_prior_consensus=old_rule.inherit_prior_consensus,
                is_grab_mode=old_rule.is_grab_mode,
                grab_threshold=old_rule.grab_threshold,
                interview_rounds=old_rule.interview_rounds,
                interview_format=old_rule.interview_format,
                created_by=actor,
                updated_by=actor,
            )

    logger.info('Process %s cloned to new version %s by %s', process.id, new_version, actor)
    return new_process


def list_process_versions(process_code: str) -> List[dict]:
    """列出某流程编号的所有历史版本（按版本号排序）"""
    from .models import RecruitmentProcess

    versions = RecruitmentProcess.objects.filter(code=process_code).order_by('current_version')
    return [
        {
            'id': p.id,
            'version': p.current_version,
            'name': p.name,
            'status': p.status,
            'created_at': p.created_at.isoformat() if p.created_at else None,
            'reference_count': p.reference_count,
        }
        for p in versions
    ]


@transaction.atomic
def upgrade_application_to_latest_version(application, target_process, actor=None) -> dict:
    """把历史候选人"升版本"到指定流程版本（PRD BR-104）

    Args:
        application: Application 实例（含 workflow_version）
        target_process: 目标 RecruitmentProcess 实例

    Returns:
        {'upgraded': True, 'from_version': str, 'to_version': str}
    """
    if application.process_id == target_process.id:
        return {
            'upgraded': False,
            'reason': 'application already on this process version',
        }

    # 冻结旧版本的 stage_records（不再写）
    application.workflow_version = target_process.current_version
    application.process = target_process
    application.save(update_fields=['workflow_version', 'process', 'updated_at'])

    logger.info(
        'Application %s upgraded to %s by %s',
        application.id, target_process.current_version, actor,
    )
    return {
        'upgraded': True,
        'from_version': application.workflow_version,
        'to_version': target_process.current_version,
    }
