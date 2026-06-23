"""查重服务

PRD v2 §5.2 - 查重阶段
扩展 apps.candidate.services.CandidateService._find_duplicate，
新增 occupied 判定（基于 Application 活动状态）。

5 种判定：
1. Moka ID 命中
2. ID card 命中
3. 手机号命中
4. 邮箱命中
5. 全无命中 → clean

命中后判定 occupied vs unocc：
- 有 active application → occupied
- 无 active application → unocc
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from apps.application.models import ApplicationState
from apps.candidate.models import Candidate
from apps.candidate.services import CandidateService

logger = logging.getLogger(__name__)


# ===== 枚举 =====
class DuplicateStatus(str, Enum):
    """查重状态"""
    CLEAN = 'clean'        # 无重复
    UNOCC = 'unocc'        # 重复但无活动申请
    OCCUPIED = 'occupied'  # 重复且有活动申请


# ===== 活动状态定义 =====
# 占用判定：application 处于这些状态中任一即视为"被占用"
ACTIVE_STATES = (
    ApplicationState.PENDING,
    ApplicationState.ACTIVE,
    ApplicationState.PAUSED,
    ApplicationState.OFFER_SENT,
    ApplicationState.OFFER_ACCEPTED,
)


# ===== Data Class =====
@dataclass
class DuplicateInfo:
    """查重结果"""
    status: DuplicateStatus
    matched_candidate: Optional[Candidate]
    active_application_id: Optional[str] = None
    # 便于前端展示的字段
    history: str = ''
    cur_status_label: str = ''

    def to_dict(self) -> dict:
        """转 dict 给前端"""
        return {
            'status': self.status.value,
            'existing_resume_id': (
                self.matched_candidate.moka_candidate_id
                or str(self.matched_candidate.id)
            ) if self.matched_candidate else None,
            'created_at': (
                self.matched_candidate.created_at.isoformat()
                if self.matched_candidate else None
            ),
            'history': self.history,
            'cur_status_label': self.cur_status_label,
            'active_application_id': self.active_application_id,
        }


# ===== Service =====
class DuplicateCheckService:
    """查重服务"""

    @classmethod
    def find(
        cls,
        phone: Optional[str],
        email: Optional[str],
        id_card: Optional[str],
        moka_id: Optional[str],
    ) -> DuplicateInfo:
        """查重，返回 DuplicateInfo"""
        # 复用现有 _find_duplicate 找候选人
        matched = CandidateService._find_duplicate(
            phone=phone or '',
            email=email,
            id_card=id_card,
            moka_id=moka_id,
        )

        if matched is None:
            return DuplicateInfo(
                status=DuplicateStatus.CLEAN,
                matched_candidate=None,
            )

        # 判定 occupied vs unocc
        active_app = matched.applications.filter(
            state__in=ACTIVE_STATES,
            deleted_at__isnull=True,
        ).order_by('-created_at').first()

        if active_app:
            return DuplicateInfo(
                status=DuplicateStatus.OCCUPIED,
                matched_candidate=matched,
                active_application_id=str(active_app.id),
                history=cls._build_history(matched),
                cur_status_label='已占用 · 面试中，不可合并',
            )

        return DuplicateInfo(
            status=DuplicateStatus.UNOCC,
            matched_candidate=matched,
            active_application_id=None,
            history=cls._build_history(matched),
            cur_status_label='未占用 · 可安全合并',
        )

    @classmethod
    def _build_history(cls, candidate: Candidate) -> str:
        """生成「历史应聘」文案"""
        from apps.position.models import Position
        last_app = candidate.applications.filter(
            deleted_at__isnull=True,
        ).order_by('-created_at').first()
        if last_app is None:
            return '无历史应聘记录'
        position = last_app.position
        position_title = position.title if position else '未知职位'
        date_str = last_app.created_at.strftime('%Y-%m')
        state_label = cls._state_label(last_app.state)
        return f'{position_title}（{date_str}）· {state_label}'

    @classmethod
    def _state_label(cls, state) -> str:
        """Application.state → 中文文案"""
        mapping = {
            ApplicationState.PENDING: '待处理',
            ApplicationState.ACTIVE: '面试中',
            ApplicationState.PAUSED: '已暂停',
            ApplicationState.OFFER_SENT: '已发offer',
            ApplicationState.OFFER_ACCEPTED: '已接受offer',
            ApplicationState.ONBOARDED: '已入职',
            ApplicationState.REJECTED: '已拒绝',
            ApplicationState.WITHDRAWN: '已撤回',
            ApplicationState.TIMEOUT: '已超时',
        }
        return mapping.get(state, '未知状态')