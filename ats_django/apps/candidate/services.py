"""Candidate Lifecycle Services (PRD v4 §14.3)

候选人生命周期服务：
- 创建候选人（含幂等查重：手机/邮箱/身份证/Moka ID）
- 启动流程 → 进入 IN_PROCESS
- 撤回 → WITHDRAWN
- 入人才库 → TALENT_POOL
- 黑名单
- 合并重复候选人
- 与摩卡集成（Moka）同步

所有写操作均通过 audit middleware 自动记录，并在 `CandidateHistory` 写明细。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.common.exceptions import NotFound, StateTransitionError
from apps.core.models import User

from .models import Candidate, CandidateHistory, CandidateState

logger = logging.getLogger(__name__)


# ============================================================
# 数据类
# ============================================================
@dataclass
class CandidateCreateData:
    """创建候选人入参"""
    name: str
    phone: str
    email: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    birth_date: Optional[Any] = None  # date
    highest_education: Optional[str] = None
    work_years: Optional[float] = None
    current_city: Optional[str] = None
    expected_city: Optional[str] = None
    current_company: Optional[str] = None
    current_position: Optional[str] = None
    expected_salary: Optional[float] = None
    resume_file_url: Optional[str] = None
    resume_text: Optional[str] = None
    id_card_no: Optional[str] = None
    source_channel_id: Optional[str] = None
    referrer_id: Optional[str] = None
    referral_type: Optional[str] = None
    tags: Optional[List[str]] = None
    moka_candidate_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class CandidateMergeResult:
    """合并结果"""
    primary: Candidate
    duplicates: List[Candidate]
    merged_fields: List[str]


# ============================================================
# 工具函数
# ============================================================
PHONE_RE = re.compile(r'^\+?1?\d{10,15}$')
EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
ID_CARD_RE = re.compile(r'^\d{17}[\dXx]$')


def normalize_phone(phone: str) -> str:
    """手机号归一化：去空格/横线/国际前缀"""
    if not phone:
        return ''
    p = re.sub(r'[\s\-()]', '', phone)
    if p.startswith('+86'):
        p = p[3:]
    elif p.startswith('86') and len(p) == 13:
        p = p[2:]
    if p.startswith('1') and len(p) == 11:
        return p
    return p


def validate_phone(phone: str) -> str:
    """校验手机号格式"""
    p = normalize_phone(phone)
    if not PHONE_RE.match(p):
        raise ValueError(f'Invalid phone number: {phone}')
    return p


def validate_email(email: str) -> str:
    """校验邮箱"""
    if not email:
        return email
    if not EMAIL_RE.match(email):
        raise ValueError(f'Invalid email: {email}')
    return email.lower()


def validate_id_card(id_card: str) -> str:
    """校验身份证号 + 校验码"""
    if not id_card:
        return id_card
    id_card = id_card.upper()
    if not ID_CARD_RE.match(id_card):
        raise ValueError(f'Invalid ID card format: {id_card}')
    # 校验码
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_codes = '10X98765432'
    try:
        s = sum(int(id_card[i]) * weights[i] for i in range(17))
        if check_codes[s % 11] != id_card[17]:
            raise ValueError(f'Invalid ID card checksum: {id_card}')
    except (ValueError, IndexError) as e:
        raise ValueError(f'Invalid ID card: {id_card}') from e
    return id_card


# ============================================================
# 候选人服务
# ============================================================
class CandidateService:
    """候选人服务"""

    @staticmethod
    @transaction.atomic
    def create_candidate(data: CandidateCreateData, actor: Optional[User] = None) -> Candidate:
        """创建候选人（含幂等查重）

        重复检测优先级：Moka ID > 身份证 > 手机 > 邮箱
        """
        # 字段校验
        if not data.name or not data.name.strip():
            raise ValueError('name is required')
        phone = validate_phone(data.phone)
        email = validate_email(data.email) if data.email else None
        id_card = validate_id_card(data.id_card_no) if data.id_card_no else None

        # 查重
        existing = CandidateService._find_duplicate(
            phone=phone, email=email, id_card=id_card, moka_id=data.moka_candidate_id,
        )
        if existing:
            logger.info('Candidate duplicate found: %s, returning existing', existing.id)
            return existing

        # 创建
        candidate = Candidate.objects.create(
            name=data.name.strip(),
            phone=phone,
            email=email,
            gender=data.gender or '',
            age=data.age,
            birth_date=data.birth_date,
            highest_education=data.highest_education or '',
            work_years=data.work_years,
            current_city=data.current_city or '',
            expected_city=data.expected_city or '',
            current_company=data.current_company or '',
            current_position=data.current_position or '',
            expected_salary=data.expected_salary,
            resume_file_url=data.resume_file_url,
            resume_text=data.resume_text or '',
            id_card_no=id_card,
            source_channel_id=data.source_channel_id,
            referrer_id=data.referrer_id,
            referral_type=data.referral_type or '',
            tags=data.tags or [],
            moka_candidate_id=data.moka_candidate_id,
        )

        # 写历史
        CandidateHistory.objects.create(
            candidate=candidate,
            action='CREATED',
            detail={
                'source': 'manual' if not data.moka_candidate_id else 'moka_sync',
                'has_referrer': bool(data.referrer_id),
                'extra': data.extra or {},
            },
            operator=actor,
        )

        logger.info('Candidate created: %s (%s)', candidate.id, candidate.name)
        return candidate

    @staticmethod
    def _find_duplicate(phone: str, email: Optional[str], id_card: Optional[str],
                        moka_id: Optional[str]) -> Optional[Candidate]:
        """查找重复候选人"""
        qs = Candidate.objects.filter(deleted_at__isnull=True)
        if moka_id:
            found = qs.filter(moka_candidate_id=moka_id).first()
            if found:
                return found
        if id_card:
            found = qs.filter(id_card_no=id_card).first()
            if found:
                return found
        if phone:
            found = qs.filter(phone=phone).first()
            if found:
                return found
        if email:
            found = qs.filter(email=email).first()
            if found:
                return found
        return None

    # ----------------------------------------------------------
    # 状态机转换（PRD v4 §14.3）
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def enter_process(candidate: Candidate, actor: Optional[User] = None,
                      application_id: Optional[str] = None) -> Candidate:
        """APPLIED → IN_PROCESS

        触发条件：候选人首次创建申请
        """
        if candidate.current_state not in (CandidateState.APPLIED, CandidateState.TALENT_POOL):
            raise StateTransitionError(
                f'Cannot enter process from state {candidate.current_state}',
            )
        try:
            candidate.enter_process()
        except Exception as e:
            raise StateTransitionError(str(e)) from e
        candidate.save()

        CandidateHistory.objects.create(
            candidate=candidate,
            action='ENTER_PROCESS',
            detail={'application_id': application_id} if application_id else {},
            operator=actor,
        )
        return candidate

    @staticmethod
    @transaction.atomic
    def send_offer(candidate: Candidate, offer_id: str, actor: Optional[User] = None) -> Candidate:
        """IN_PROCESS → OFFER_SENT

        触发：发出 Offer
        """
        if candidate.current_state != CandidateState.IN_PROCESS:
            raise StateTransitionError(
                f'Cannot send offer from state {candidate.current_state}',
            )
        try:
            candidate.send_offer()
        except Exception as e:
            raise StateTransitionError(str(e)) from e
        candidate.save()

        CandidateHistory.objects.create(
            candidate=candidate,
            action='OFFER_SENT',
            detail={'offer_id': offer_id},
            operator=actor,
        )
        return candidate

    @staticmethod
    @transaction.atomic
    def mark_onboarded(candidate: Candidate, actor: Optional[User] = None,
                        onboarding_id: Optional[str] = None) -> Candidate:
        """OFFER_SENT → ONBOARDED

        触发：完成入职流程
        """
        if candidate.current_state not in (
            CandidateState.OFFER_SENT,
            CandidateState.PENDING_ONBOARDING,
        ):
            raise StateTransitionError(
                f'Cannot mark onboarded from state {candidate.current_state}',
            )
        # 直接设置（FSM 模型上没标 transition 方法，兼容）
        candidate.current_state = CandidateState.ONBOARDED
        candidate.save()

        CandidateHistory.objects.create(
            candidate=candidate,
            action='ONBOARDED',
            detail={'onboarding_id': onboarding_id} if onboarding_id else {},
            operator=actor,
        )
        return candidate

    @staticmethod
    @transaction.atomic
    def withdraw(candidate: Candidate, reason: str, actor: Optional[User] = None) -> Candidate:
        """任意非终态 → WITHDRAWN（候选人主动撤回）

        终态：ONBOARDED / WITHDRAWN / PROCESS_FAILED
        """
        terminal_states = {
            CandidateState.ONBOARDED,
            CandidateState.WITHDRAWN,
        }
        if candidate.current_state in terminal_states:
            raise StateTransitionError(
                f'Cannot withdraw from terminal state {candidate.current_state}',
            )
        old_state = candidate.current_state
        candidate.current_state = CandidateState.WITHDRAWN
        candidate.save()

        CandidateHistory.objects.create(
            candidate=candidate,
            action='WITHDRAWN',
            detail={'reason': reason, 'from_state': old_state},
            operator=actor,
        )
        return candidate

    @staticmethod
    @transaction.atomic
    def move_to_talent_pool(candidate: Candidate, entry_source: str, reason: str,
                            actor: Optional[User] = None) -> Candidate:
        """任意非终态 → TALENT_POOL

        调用方确保已经创建对应的 TalentPool 记录（talent_pool.services）
        """
        terminal_states = {
            CandidateState.ONBOARDED,
            CandidateState.WITHDRAWN,
            CandidateState.TALENT_POOL,
        }
        if candidate.current_state in terminal_states:
            raise StateTransitionError(
                f'Cannot move to talent pool from state {candidate.current_state}',
            )
        old_state = candidate.current_state
        try:
            candidate.move_to_pool(reason=entry_source)
        except Exception as e:
            raise StateTransitionError(str(e)) from e
        candidate.save()

        CandidateHistory.objects.create(
            candidate=candidate,
            action='TO_TALENT_POOL',
            detail={'entry_source': entry_source, 'reason': reason, 'from_state': old_state},
            operator=actor,
        )
        return candidate

    @staticmethod
    @transaction.atomic
    def mark_process_failed(candidate: Candidate, reason: str,
                            actor: Optional[User] = None) -> Candidate:
        """IN_PROCESS / OFFER_SENT → PROCESS_FAILED

        终态：本流程未通过
        """
        if candidate.current_state not in (
            CandidateState.IN_PROCESS,
            CandidateState.OFFER_SENT,
            CandidateState.APPLIED,
        ):
            raise StateTransitionError(
                f'Cannot mark process failed from state {candidate.current_state}',
            )
        old_state = candidate.current_state
        candidate.current_state = CandidateState.PROCESS_FAILED
        candidate.save()

        CandidateHistory.objects.create(
            candidate=candidate,
            action='PROCESS_FAILED',
            detail={'reason': reason, 'from_state': old_state},
            operator=actor,
        )
        return candidate

    @staticmethod
    @transaction.atomic
    def pause_process(candidate: Candidate, reason: str,
                      actor: Optional[User] = None) -> Candidate:
        """IN_PROCESS → PROCESS_PAUSED"""
        if candidate.current_state != CandidateState.IN_PROCESS:
            raise StateTransitionError(
                f'Cannot pause from state {candidate.current_state}',
            )
        candidate.current_state = CandidateState.PROCESS_PAUSED
        candidate.save()

        CandidateHistory.objects.create(
            candidate=candidate,
            action='PAUSED',
            detail={'reason': reason},
            operator=actor,
        )
        return candidate

    @staticmethod
    @transaction.atomic
    def resume_process(candidate: Candidate, actor: Optional[User] = None) -> Candidate:
        """PROCESS_PAUSED → IN_PROCESS"""
        if candidate.current_state != CandidateState.PROCESS_PAUSED:
            raise StateTransitionError(
                f'Cannot resume from state {candidate.current_state}',
            )
        candidate.current_state = CandidateState.IN_PROCESS
        candidate.save()

        CandidateHistory.objects.create(
            candidate=candidate,
            action='RESUMED',
            detail={},
            operator=actor,
        )
        return candidate

    # ----------------------------------------------------------
    # 候选人查询
    # ----------------------------------------------------------
    @staticmethod
    def search_candidates(keyword: Optional[str] = None,
                          state: Optional[str] = None,
                          source_channel_id: Optional[str] = None,
                          referrer_id: Optional[str] = None,
                          tag: Optional[str] = None,
                          created_from: Optional[datetime] = None,
                          created_to: Optional[datetime] = None,
                          limit: int = 50,
                          offset: int = 0) -> List[Candidate]:
        """候选人搜索"""
        qs = Candidate.objects.filter(deleted_at__isnull=True)
        if keyword:
            qs = qs.filter(
                Q(name__icontains=keyword) |
                Q(phone__icontains=keyword) |
                Q(email__icontains=keyword) |
                Q(current_company__icontains=keyword),
            )
        if state:
            qs = qs.filter(current_state=state)
        if source_channel_id:
            qs = qs.filter(source_channel_id=source_channel_id)
        if referrer_id:
            qs = qs.filter(referrer_id=referrer_id)
        if tag:
            qs = qs.filter(tags__contains=[tag])
        if created_from:
            qs = qs.filter(created_at__gte=created_from)
        if created_to:
            qs = qs.filter(created_at__lte=created_to)
        return list(qs.order_by('-created_at')[offset:offset + limit])

    @staticmethod
    def get_or_create_by_phone(phone: str, defaults: Optional[Dict[str, Any]] = None,
                               actor: Optional[User] = None) -> Candidate:
        """按手机号获取或创建（用于快速导入）"""
        phone = validate_phone(phone)
        existing = Candidate.objects.filter(phone=phone, deleted_at__isnull=True).first()
        if existing:
            return existing
        if not defaults:
            raise ValueError('defaults is required for creating new candidate')
        defaults['phone'] = phone
        data = CandidateCreateData(**defaults)
        return CandidateService.create_candidate(data, actor=actor)

    # ----------------------------------------------------------
    # 重复候选人合并
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def merge_candidates(primary_id: str, duplicate_ids: List[str],
                         actor: Optional[User] = None) -> CandidateMergeResult:
        """合并重复候选人

        - 主候选保留
        - 从候选的申请/历史迁移到主候选
        - 从候选软删
        """
        try:
            primary = Candidate.objects.get(id=primary_id, deleted_at__isnull=True)
        except Candidate.DoesNotExist as e:
            raise NotFound(f'Primary candidate {primary_id} not found') from e

        duplicates = []
        merged_fields = []
        for dup_id in duplicate_ids:
            try:
                dup = Candidate.objects.get(id=dup_id, deleted_at__isnull=True)
            except Candidate.DoesNotExist:
                continue
            if dup.id == primary.id:
                continue
            # 迁移申请
            dup.applications.all().update(candidate=primary)
            # 迁移历史 - 实际是迁移 CandidateHistory 的 candidate FK
            dup.histories.all().update(candidate=primary)
            # 合并 tags
            for t in dup.tags or []:
                if t not in (primary.tags or []):
                    primary.tags.append(t)
                    merged_fields.append(f'tag:{t}')
            # 合并字段（空值才补）
            for fld in ('highest_education', 'work_years', 'current_city', 'expected_city',
                        'current_company', 'current_position', 'expected_salary',
                        'resume_file_url', 'resume_text', 'email', 'id_card_no'):
                cur = getattr(primary, fld, None)
                src = getattr(dup, fld, None)
                if not cur and src:
                    setattr(primary, fld, src)
                    merged_fields.append(fld)
            primary.save()
            # 软删
            dup.deleted_at = timezone.now()
            dup.save(update_fields=['deleted_at', 'updated_at'])
            CandidateHistory.objects.create(
                candidate=primary,
                action='MERGED',
                detail={'merged_from': dup.id, 'merged_fields': merged_fields},
                operator=actor,
            )
            duplicates.append(dup)

        return CandidateMergeResult(
            primary=primary, duplicates=duplicates, merged_fields=merged_fields,
        )

    # ----------------------------------------------------------
    # 摩卡同步
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def sync_from_moka(moka_data: Dict[str, Any], actor: Optional[User] = None) -> Candidate:
        """从摩卡同步候选人数据（PRD v4 §14.13 集成）"""
        moka_id = moka_data.get('id')
        if not moka_id:
            raise ValueError('moka_data.id is required')

        # 查重
        existing = Candidate.objects.filter(
            moka_candidate_id=moka_id, deleted_at__isnull=True,
        ).first()
        if not existing and moka_data.get('phone'):
            existing = Candidate.objects.filter(
                phone=validate_phone(moka_data['phone']),
                deleted_at__isnull=True,
            ).first()

        defaults = {
            'name': moka_data.get('name', ''),
            'phone': moka_data.get('phone', ''),
            'email': moka_data.get('email'),
            'gender': moka_data.get('gender'),
            'highest_education': moka_data.get('education'),
            'work_years': moka_data.get('work_years'),
            'current_company': moka_data.get('current_company'),
            'current_position': moka_data.get('current_position'),
            'current_city': moka_data.get('current_city'),
            'resume_file_url': moka_data.get('resume_url'),
            'moka_candidate_id': moka_id,
            'source_channel_id': moka_data.get('source_channel_id'),
        }
        if existing:
            for k, v in defaults.items():
                if v and not getattr(existing, k):
                    setattr(existing, k, v)
            existing.save()
            CandidateHistory.objects.create(
                candidate=existing,
                action='MOKA_SYNCED',
                detail={'moka_id': moka_id, 'updated': True},
                operator=actor,
            )
            return existing

        data = CandidateCreateData(**defaults)
        candidate = CandidateService.create_candidate(data, actor=actor)
        CandidateHistory.objects.create(
            candidate=candidate,
            action='MOKA_SYNCED',
            detail={'moka_id': moka_id, 'updated': False},
            operator=actor,
        )
        return candidate


# ============================================================
# Celery 任务入口
# ============================================================
def create_candidate(data: CandidateCreateData, actor: Optional[User] = None) -> Candidate:
    """便捷函数"""
    return CandidateService.create_candidate(data, actor=actor)


def enter_process(candidate: Candidate, application_id: Optional[str] = None,
                  actor: Optional[User] = None) -> Candidate:
    return CandidateService.enter_process(candidate, actor, application_id)


def withdraw_candidate(candidate: Candidate, reason: str,
                       actor: Optional[User] = None) -> Candidate:
    return CandidateService.withdraw(candidate, reason, actor)
