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
from django.db.models import Max
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


def _compute_next_version_seq(process) -> int:
    """纯计算：给出 ``process`` 所在流程线（同 ``code``）的下一个 ``version_seq``。

    ⚠️ **刻意不过滤软删**：C1 ``uniq_process_code_version_seq`` 是无条件唯一约束，
    软删行同样占位。若这里只统计 live 行，克隆一条曾被软删过版本的流程线会算出已被
    占用的 seq，直接撞 C1 抛 ``IntegrityError``。

    ⚠️ **取全线 MAX 而非 ``process.version_seq + 1``**：允许从任意历史版本发起克隆
    （例如线上已有 seq=1/2，从 seq=1 那行克隆）。用 ``+1`` 会算出 2 → 撞 C1；
    取 MAX+1 得 3，才是「追加一个新版本」的正确语义。
    ``max(..., process.version_seq)`` 兜底传入的是尚未落库的内存实例的情形。

    并发下两个 clone 可能算出同一个 seq：这不会静默腐化——C1 会让后到者
    ``IntegrityError``（响亮失败），与 C3' 的兜底策略一致。

    Args:
        process: 当前（待被克隆的）RecruitmentProcess 实例。

    Returns:
        下一个可用的版本序号（整数，>= 2）。
    """
    from ..models import RecruitmentProcess

    max_seq = RecruitmentProcess.objects.filter(code=process.code).aggregate(
        max_seq=Max('version_seq'),
    )['max_seq'] or 0
    return max(max_seq, process.version_seq or 0) + 1


def _compute_next_version(process, seq: int = None) -> str:
    """纯计算：给出 ``process`` 所在流程线的下一个版本号字符串，**不写库**。

    T2 之前这里叫 ``bump_version``，既算版本号又 ``process.save()`` 原地改写**老行**的
    ``current_version``——那是 V2/V3/V4 三个缺陷的共同根因：

    - V2：克隆时改写老行版本号，违反 BR-103「历史版本只读」；实测把 ``'1.0'``
      反复写成 ``'1.0+1+1+1'``（数据损坏）。
    - V3：老 default 是 ``'1.0'``（无 ``V`` 前缀），进不了 ``startswith('V')`` 分支，
      直接掉进 ``f'{cur}+1'`` 兜底，垃圾版本号经 ``__str__`` 直达 UI。
    - V4：从字符串反解 major/minor 本身不可靠，污染串一旦产生便不可恢复。

    改法：版本号的唯一权威来源是整数 ``version_seq``（DB 侧由
    ``uniq_process_code_version_seq`` 兜底），不再解析字符串、不再触碰老行。
    落库由调用方在**新建行**时完成，本函数零副作用。

    Args:
        process: 当前（待被克隆的）RecruitmentProcess 实例。
        seq: 已算好的目标版本序号；省略时内部调用 :func:`_compute_next_version_seq`。
            调用方若同时需要 seq 与版本串，应先算 seq 再传入，避免两次聚合查询
            之间取到不一致的结果。

    Returns:
        新版本字符串，形如 ``'V2.0'``。
    """
    if seq is None:
        seq = _compute_next_version_seq(process)
    return f'V{seq}.0'


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

    **老行只读**：本函数不再改写老行的 ``current_version`` / ``version_seq``
    （BR-103），唯一会被写的老行字段是 ``is_latest``——降级让位给新行。

    **按 Q4 裁定，克隆不改指任何 Demand/Position/Application（有意为之）**：
    在跑的候选人继续走创建时的版本（BR-102），改指必须由显式的升版本动作发起。
    """
    from ..models import (
        ProcessStageLink,
        RecruitmentProcess,
        StageRule,
    )

    # 先算 seq 再由它派生版本串，保证 version_seq 与 current_version 永远同源，
    # 不会出现 C1 通过而 C2 撞车（或反之）这种半截状态。
    new_seq = _compute_next_version_seq(process)
    new_version = _compute_next_version(process, seq=new_seq)

    # 创建新流程
    new_process = RecruitmentProcess.objects.create(
        code=process.code,  # 编号不变，新版本是同一流程
        name=new_name or f'{process.name} ({new_version})',
        current_version=new_version,
        version_seq=new_seq,
        # 新行先落为非 latest：翻转必须「先降后升」，此处若直接 True 会与老行瞬时
        # 并存两个 latest → C3' 立即 IntegrityError。
        is_latest=False,
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

    # ============================================================
    # is_latest 原子翻转 —— **顺序是硬约束：必须先降后升**
    # 双库实测：先升后降在 ① 执行瞬间同 code 存在 2 行 is_latest=True
    # → C3'（uniq_one_latest_per_code）立即抛 IntegrityError，克隆整体回滚。
    # ============================================================
    # ① 先降级：filter(code=...) 刻意不过滤软删，一并降级软删行（自愈，见 C3' soft_delete 条）
    RecruitmentProcess.objects.filter(code=new_process.code).exclude(id=new_process.id).update(is_latest=False)
    # ② 后升级
    new_process.is_latest = True
    new_process.save(update_fields=['is_latest'])

    logger.info('Process %s cloned to new version %s by %s', process.id, new_version, actor)
    return new_process


def list_process_versions(process_code: str) -> List[dict]:
    """列出某流程编号的所有历史版本（按版本号排序）"""
    from ..models import RecruitmentProcess

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
