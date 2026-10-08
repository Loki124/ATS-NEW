"""批量创建候选人服务

PRD v2 §5.2 (bulk-create endpoint) + §5.5 (3 方向路由)

3 方向：
- pending: 仅创建 Candidate，无 Application
- position: 创建 Candidate + Application(state=ACTIVE, position=position_id)
- talent: 创建 Candidate + TalentPoolEntry(source=DIRECT_IMPORT)

事务一致性：任一 draft 失败 → 全部 rollback
幂等性：按 phone 匹配复用已存在 candidate
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from django.db import transaction

from apps.application.models import Application, ApplicationState
from apps.candidate.models import Candidate, CandidateState
from apps.candidate.services import CandidateService
# 2026-09-25: 简历解析结果结构化落 extra（供指标库派生指标对真实数据取值）
from apps.metrics.services.resume_struct import build_structured_extra
from apps.core.models import User
from apps.talent_pool.models import TalentPoolEntry  # EntrySource 是 TalentPoolEntry 的嵌套类

logger = logging.getLogger(__name__)


# ===== 异常 =====
class BulkCreateError(Exception):
    """批量创建错误"""
    def __init__(self, code: str, message: str, draft_id: Optional[str] = None):
        self.code = code
        self.draft_id = draft_id
        super().__init__(f'{code}: {message} (draft_id={draft_id})' if draft_id else f'{code}: {message}')


# ===== Data Classes =====
@dataclass
class BulkCreateDraft:
    """单个 draft 的创建参数"""
    draft_id: str
    direction: str  # pending | talent | position
    name: str
    phone: str
    email: str
    parsed_data: dict
    position_id: Optional[str] = None
    channel: str = '招聘网站'
    source: str = ''
    provider: str = ''


@dataclass
class BulkCreateResult:
    """批量创建结果"""
    created_candidate_ids: List[str]  # 注意：与 draft_id 一一对应
    route: dict  # {draft_id: 'pending'|'talent'|'position'}


# ===== Service =====
class BulkCreateService:
    """批量创建候选人服务"""

    VALID_DIRECTIONS = ('pending', 'talent', 'position')

    @classmethod
    @transaction.atomic
    def create_batch(
        cls,
        drafts: List[BulkCreateDraft],
        actor: User,
        recruit_type: str = 'social',
    ) -> BulkCreateResult:
        """批量创建候选人

        Raises:
            BulkCreateError: 任一 draft 失败 → 全部 rollback
        """
        if not drafts:
            return BulkCreateResult(created_candidate_ids=[], route={})

        created_ids: List[str] = []
        route: dict = {}

        for draft in drafts:
            try:
                cand_id = cls._create_one(draft, actor, recruit_type)
            except BulkCreateError:
                raise
            except Exception as e:  # noqa: BLE001 — BulkCreate 单条候选人创建未预期异常, 包成 BulkCreateError 让 view 层统一处理
                logger.exception('Unexpected error creating candidate for draft %s', draft.draft_id)
                raise BulkCreateError(
                    'CREATE_FAILED', f'创建失败: {e}', draft.draft_id,
                ) from e

            created_ids.append(cand_id)
            route[draft.draft_id] = draft.direction

        return BulkCreateResult(
            created_candidate_ids=created_ids,
            route=route,
        )

    @classmethod
    def _create_one(cls, draft: BulkCreateDraft, actor: User, recruit_type: str = 'social') -> str:
        """创建单个候选 + 关联记录

        幂等：若 phone 已存在，返回现有 candidate.id
        """
        # 1. 校验
        cls._validate(draft)

        # 2. 幂等查重
        existing = CandidateService._find_duplicate(
            phone=draft.phone,
            email=draft.email or None,
            id_card=None,
            moka_id=None,
        )
        if existing:
            logger.info('Reusing existing candidate %s for draft %s', existing.id, draft.draft_id)
            cand = existing
        else:
            # 3. 创建 Candidate
            cand = Candidate.objects.create(
                name=draft.name,
                phone=draft.phone,
                email=draft.email or None,
                recruit_type=recruit_type,
                current_state=CandidateState.APPLIED,
                extra={
                    'draft_id': draft.draft_id,
                    'created_via': 'add_candidate_v2',
                    'channel': draft.channel,
                    'source': draft.source,
                    'provider': draft.provider,
                    # 工作经历 / 教育经历结构化（空窗期、跳槽频率、最高学历等派生指标的数据源）
                    **build_structured_extra(draft.parsed_data or {}),
                },
            )
            logger.info('Created candidate %s for draft %s', cand.id, draft.draft_id)

        # 4. 按方向创建关联
        if draft.direction == 'pending':
            pass  # 仅 candidate
        elif draft.direction == 'position':
            cls._create_application(cand, draft, actor)
        elif draft.direction == 'talent':
            cls._create_talent_pool_entry(cand, draft, actor)
        else:
            raise BulkCreateError(
                'INVALID_DIRECTION', f'未知方向: {draft.direction}', draft.draft_id,
            )

        return str(cand.id)

    @classmethod
    def _validate(cls, draft: BulkCreateDraft) -> None:
        """校验必填字段"""
        if not draft.name or not draft.name.strip():
            raise BulkCreateError('MISSING_FIELD', 'name 不能为空', draft.draft_id)
        if not draft.phone or not draft.phone.strip():
            raise BulkCreateError('MISSING_FIELD', 'phone 不能为空', draft.draft_id)
        if not draft.email or not draft.email.strip():
            raise BulkCreateError('MISSING_FIELD', 'email 不能为空', draft.draft_id)
        if draft.direction not in cls.VALID_DIRECTIONS:
            raise BulkCreateError(
                'INVALID_DIRECTION', f'方向必须为 {cls.VALID_DIRECTIONS} 之一', draft.draft_id,
            )
        if draft.direction == 'position' and not draft.position_id:
            raise BulkCreateError(
                'MISSING_FIELD', 'position 方向必须提供 position_id', draft.draft_id,
            )

    @classmethod
    def _create_application(
        cls, cand: Candidate, draft: BulkCreateDraft, actor: User,
    ) -> Application:
        """创建 Application（position 方向）"""
        from apps.position.models import Position
        try:
            position = Position.objects.get(id=draft.position_id)
        except Position.DoesNotExist as e:
            raise BulkCreateError(
                'POSITION_NOT_FOUND', f'职位 {draft.position_id} 不存在', draft.draft_id,
            ) from e

        # 注：Application 模型要求 process + workflow_version + code 必填
        # （plan 里的 create() 调用遗漏这三个字段，按模型实际 schema 补齐 — Task 4 lesson）
        # 注：Application 模型没有 channel/source/referrer 字段
        # 这些信息存到 Candidate.extra（V2 流程的统一存储位置）
        return Application.objects.create(
            candidate=cand,
            position=position,
            process=position.process,
            workflow_version=position.process.current_version,
            code=f'APP-{cand.id}-{draft.draft_id}'[:20],
            state=ApplicationState.ACTIVE,
        )

    @classmethod
    def _create_talent_pool_entry(
        cls, cand: Candidate, draft: BulkCreateDraft, actor: User,
    ) -> TalentPoolEntry:
        """创建 TalentPoolEntry（talent 方向）"""
        return TalentPoolEntry.objects.create(
            candidate=cand,
            source=TalentPoolEntry.EntrySource.DIRECT_IMPORT,
            source_detail=f'通过「新增候选人」V2 流程入库（draft_id={draft.draft_id}）',
            tags=[],
            is_active=True,
        )
