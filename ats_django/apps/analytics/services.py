"""Analytics Services (PRD v4 §14.9 数据中心)"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from django.db.models import Count, Q
from django.utils import timezone

from apps.candidate.models import Candidate
from apps.application.models import Application
from apps.demand.models import Demand
from apps.position.models import Position
from apps.offer.models import Offer

logger = logging.getLogger(__name__)


class AnalyticsService:
    """数据中心业务服务"""

    @staticmethod
    def get_funnel_data(department_id: Optional[str] = None, days: int = 30) -> Dict:
        """招聘漏斗数据"""
        from_date = timezone.now() - timedelta(days=days)
        apps_qs = Application.objects.filter(created_at__gte=from_date, deleted_at__isnull=True)
        if department_id:
            apps_qs = apps_qs.filter(position__department_id=department_id)

        total = apps_qs.count()
        active = apps_qs.filter(state='ACTIVE').count()
        passed_interview = apps_qs.filter(state__in=['OFFER_SENT', 'OFFER_ACCEPTED', 'ONBOARDED']).count()
        offer_sent = apps_qs.filter(state__in=['OFFER_SENT', 'OFFER_ACCEPTED']).count()
        onboarded = apps_qs.filter(state='ONBOARDED').count()

        return {
            'period_days': days,
            'total': total,
            'active': active,
            'passed_interview': passed_interview,
            'offer_sent': offer_sent,
            'onboarded': onboarded,
            'conversion_rates': {
                'application_to_active': (active / total * 100) if total > 0 else 0,
                'active_to_offer': (offer_sent / active * 100) if active > 0 else 0,
                'offer_to_onboarded': (onboarded / offer_sent * 100) if offer_sent > 0 else 0,
            }
        }

    @staticmethod
    def get_dashboard_summary() -> Dict:
        """HR 个人看板汇总"""
        return {
            'candidates': {
                'total': Candidate.objects.filter(deleted_at__isnull=True).count(),
                'this_month': Candidate.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=30),
                    deleted_at__isnull=True,
                ).count(),
            },
            'applications': {
                'total': Application.objects.filter(deleted_at__isnull=True).count(),
                'by_state': dict(
                    Application.objects.filter(deleted_at__isnull=True)
                    .values_list('state').annotate(count=Count('id'))
                ),
            },
            'demands': {
                'total': Demand.objects.filter(deleted_at__isnull=True).count(),
                'pending': Demand.objects.filter(state='PENDING', deleted_at__isnull=True).count(),
            },
            'positions': {
                'total': Position.objects.filter(deleted_at__isnull=True).count(),
                'open': Position.objects.filter(
                    state='RECRUITING', deleted_at__isnull=True,
                ).count(),
            },
            'offers': {
                'sent': Offer.objects.filter(state='SENT', deleted_at__isnull=True).count(),
                'accepted': Offer.objects.filter(state='ACCEPTED', deleted_at__isnull=True).count(),
            },
        }

    @staticmethod
    def get_channel_roi() -> List[Dict]:
        """所有渠道 ROI"""
        from apps.channel.models import Channel
        channels = Channel.objects.filter(is_active=True)
        return [
            {
                'channel_id': c.id,
                'channel_name': c.name,
                'total_cost': float(c.total_cost),
                'cost_per_hire': float(c.cost_per_hire),
            }
            for c in channels
        ]

    @staticmethod
    def get_hr_workload() -> List[Dict]:
        """HR 工作量统计"""
        from apps.core.models import User
        hrs = User.objects.filter(
            user_roles__role__code__in=['HR', 'HRBP'],
            is_active=True, deleted_at__isnull=True,
        ).distinct()
        return [
            {
                'hr_id': hr.id,
                'hr_name': hr.username,
                'active_demands': Demand.objects.filter(
                    hr=hr, state__in=['PENDING', 'APPROVED', 'RECRUITING'],
                    deleted_at__isnull=True,
                ).count(),
                'active_positions': Position.objects.filter(
                    owner=hr, state='RECRUITING', deleted_at__isnull=True,
                ).count(),
            }
            for hr in hrs
        ]
