"""Offer Services (PRD v4 §6.6, §14.5) - Offer 业务逻辑"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.common.exceptions import NotFound
from apps.core.models import User

from .models import Offer, OfferState

logger = logging.getLogger(__name__)


def _mirror_campus_validation(candidate_id, blocks=None, warnings=None):
    """best-effort 把 campus Offer 校验事件镜像进统一 RuleExecutionLog。

    Phase 4（2026-09-01，设计文档 §3.5 / §6）：仅追加可观测日志，异常吞掉，绝不影响
    Offer 主流程。经 RULE_ENGINE_DOUBLE_WRITE 开关控制（默认开）。
    """
    from django.conf import settings
    if not getattr(settings, 'RULE_ENGINE_DOUBLE_WRITE', False):
        return
    try:
        from apps.rule_engine.bridge import mirror_campus_offer_validation
        mirror_campus_offer_validation(
            candidate_id, blocks=blocks, warnings=warnings,
        )
    except Exception:  # noqa: BLE001 — 镜像失败不影响现网
        logger.exception('RULE_ENGINE campus validation mirror failed')


@dataclass
class OfferCreateData:
    application_id: str
    candidate_id: str
    position_id: str
    salary: float
    start_date: str  # ISO date
    expire_date: str
    level: str = ''
    position_title: str = ''
    actor: Optional[User] = None


class OfferService:
    @staticmethod
    @transaction.atomic
    def create_offer(data: OfferCreateData) -> Offer:
        from nanoid import generate as nanoid_generate
        from apps.application.models import Application
        from apps.candidate.models import Candidate
        from apps.position.models import Position

        try:
            application = Application.objects.get(id=data.application_id, deleted_at__isnull=True)
            candidate = Candidate.objects.get(id=data.candidate_id, deleted_at__isnull=True)
            position = Position.objects.get(id=data.position_id, deleted_at__isnull=True)
        except (Application.DoesNotExist, Candidate.DoesNotExist, Position.DoesNotExist) as e:
            raise NotFound(str(e))

        # ── T03：Offer 钩子（人员比例管控）──
        # 硬约束命中 → 抛 DRFValidationError(400)，事务自动回滚，Offer 不落库；
        # 软约束/仅提示命中 → 仅 logger.warning 放行（前端提示为 P1 后续）。
        # start_date 是 ISO 字符串，解析失败则传 None（跳过月度判定）。
        start_date_obj = None
        if data.start_date:
            try:
                start_date_obj = datetime.strptime(data.start_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                start_date_obj = None
        from apps.campus_control.services import (
            validate_offer_against_rules, ControlRuleViolation,
        )
        try:
            hook_result = validate_offer_against_rules(
                candidate=candidate,
                position=position,
                level=data.level,
                position_title=data.position_title,
                start_date=start_date_obj,
            )
            # Phase 4：best-effort 把软约束提示镜像进统一执行日志（纯可观测，不影响主流程）
            _mirror_campus_validation(
                data.candidate_id, warnings=hook_result.get('warnings'),
            )
            for w in hook_result.get('warnings', []):
                logger.warning(
                    'Offer 软约束提示(candidate=%s): 规则 %s %s·%s %s 当前 %s/%s 人',
                    data.candidate_id, w.get('code'), w.get('dimension'), w.get('indicator'),
                    w.get('scope'), w.get('annualActual'), w.get('annualTarget'),
                )
        except ControlRuleViolation as e:
            # 硬约束阻断：事务回滚，向上抛 400（detail 含命中规则明细）
            # Phase 4：best-effort 镜像阻断事件（注：位于同一事务内，回滚时该日志不落库，
            # 属已知边界；阻断本身已通过 400 返回前端，无需依赖日志追溯）。
            _mirror_campus_validation(
                data.candidate_id, blocks=e.blocks, warnings=e.warnings,
            )
            raise DRFValidationError({'detail': e.message})

        code = f'OFR{timezone.now().strftime("%Y%m%d")}{nanoid_generate(size=4).upper()}'
        offer = Offer.objects.create(
            code=code,
            application=application,
            candidate=candidate,
            position=position,
            salary=data.salary,
            start_date=data.start_date,
            expire_date=data.expire_date,
            level=data.level,
            position_title=data.position_title,
            state=OfferState.DRAFT,
            created_by=data.actor,
            updated_by=data.actor,
        )
        return offer

    @staticmethod
    @transaction.atomic
    def submit_approval(offer_id: str, actor: User) -> Offer:
        # 2026-07-02: 加 select_for_update 锁, 防并发双审
        offer = Offer.objects.select_for_update().get(id=offer_id, deleted_at__isnull=True)

        # ── v2.10 T03：Offer 钩子（人员比例管控 — 节点 2 / submit_approval）──
        # 与 create_offer / send_to_candidate 同入口（Q-A10 单一函数）。
        # 钩子必须在 select_for_update 之后、状态机 + save 之前调用：
        #   硬约束命中 → 抛 DRFValidationError(400) → 事务回滚 → offer 状态不变。
        #   软约束命中 → logger.warning 放行。
        from apps.campus_control.services import (
            validate_offer_against_rules, ControlRuleViolation,
        )
        # 解析 offer.start_date：可能是 ISO 字符串或 date 对象；解析失败则传 None（跳过月度判定）
        start_date_obj = None
        if offer.start_date:
            try:
                start_date_obj = datetime.strptime(str(offer.start_date)[:10], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                start_date_obj = None
        try:
            hook_result = validate_offer_against_rules(
                candidate=offer.candidate,
                position=offer.position,
                level=offer.level or '',
                position_title=offer.position_title or '',
                start_date=start_date_obj,
            )
            # Phase 4：best-effort 把软约束提示镜像进统一执行日志（纯可观测，不影响主流程）
            _mirror_campus_validation(
                offer.candidate_id, warnings=hook_result.get('warnings'),
            )
            for w in hook_result.get('warnings', []):
                logger.warning(
                    'Offer.submit_approval 软约束提示(offer=%s): 规则 %s %s·%s %s 当前 %s/%s 人',
                    offer.id, w.get('code'), w.get('dimension'), w.get('indicator'),
                    w.get('scope'), w.get('annualActual'), w.get('annualTarget'),
                )
        except ControlRuleViolation as e:
            # 硬约束阻断：事务回滚，向上抛 400（detail 含命中规则明细）
            _mirror_campus_validation(
                offer.candidate_id, blocks=e.blocks, warnings=e.warnings,
            )
            raise DRFValidationError({'detail': e.message})

        offer.submit_approval()
        offer.save()
        return offer

    @staticmethod
    @transaction.atomic
    def approve(offer_id: str, actor: User) -> Offer:
        offer = Offer.objects.select_for_update().get(id=offer_id, deleted_at__isnull=True)
        offer.approver = actor
        offer.approve()
        offer.save()
        return offer

    @staticmethod
    @transaction.atomic
    def reject(offer_id: str, reason: str, actor: User) -> Offer:
        offer = Offer.objects.select_for_update().get(id=offer_id, deleted_at__isnull=True)
        offer.reject()
        offer.save()
        return offer

    @staticmethod
    @transaction.atomic
    def send_to_candidate(offer_id: str, actor: User) -> Offer:
        offer = Offer.objects.select_for_update().get(id=offer_id, deleted_at__isnull=True)

        # ── v2.10 T03：Offer 钩子（人员比例管控 — 节点 3）──
        # 与 create_offer / submit_approval 同入口（Q-A10 单一函数）。
        from apps.campus_control.services import (
            validate_offer_against_rules, ControlRuleViolation,
        )
        try:
            hook_result = validate_offer_against_rules(
                candidate=offer.candidate,
                position=offer.position,
                level=offer.level or '',
                position_title=offer.position_title or '',
                start_date=offer.start_date,
            )
            _mirror_campus_validation(
                offer.candidate_id, warnings=hook_result.get('warnings'),
            )
            for w in hook_result.get('warnings', []):
                logger.warning(
                    'Offer.send_to_candidate 软约束提示(offer=%s): 规则 %s %s·%s %s 当前 %s/%s 人',
                    offer.id, w.get('code'), w.get('dimension'), w.get('indicator'),
                    w.get('scope'), w.get('annualActual'), w.get('annualTarget'),
                )
        except ControlRuleViolation as e:
            _mirror_campus_validation(
                offer.candidate_id, blocks=e.blocks, warnings=e.warnings,
            )
            raise DRFValidationError({'detail': e.message})

        offer.send()
        offer.save()
        # 触发通知 (2026-07-02: 用模块级便捷函数, 之前 kwargs 错配 → 100% 静默失败)
        try:
            from apps.notification.services import send_notification
            send_notification(
                recipient_id=str(offer.candidate_id) if hasattr(offer, 'candidate_id') else str(actor.id),
                title=f'Offer 已发送',
                content=f'您的 Offer 已生成, 请查收',
                link=f'/offers/{offer.id}',
                source='offer.sent',
                source_id=str(offer.id),
                channel='IN_APP',
                template_code='offer.sent',
                variables={'offer_id': str(offer.id), 'candidate_name': getattr(offer.candidate, 'full_name', '')},
            )
        except Exception:
            logger.exception('Offer notification dispatch failed (offer_id=%s)', offer.id)
        return offer

    @staticmethod
    @transaction.atomic
    def candidate_accept(offer_id: str, actor: User) -> Offer:
        offer = Offer.objects.select_for_update().get(id=offer_id, deleted_at__isnull=True)
        offer.accept()
        offer.save()
        return offer

    @staticmethod
    @transaction.atomic
    def candidate_reject(offer_id: str, reason: str, actor: User) -> Offer:
        offer = Offer.objects.select_for_update().get(id=offer_id, deleted_at__isnull=True)
        offer.candidate_reject(reason=reason)
        offer.save()
        return offer

    @staticmethod
    @transaction.atomic
    def mark_onboarded(offer_id: str, actor: User) -> Offer:
        offer = Offer.objects.select_for_update().get(id=offer_id, deleted_at__isnull=True)
        offer.onboarded()
        offer.save()
        return offer
