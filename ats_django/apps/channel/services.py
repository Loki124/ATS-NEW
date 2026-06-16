"""Channel Services (PRD v4 §14.5 渠道)"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal

from django.db.models import Sum

from apps.common.exceptions import NotFound

from .models import Channel, ChannelCost

logger = logging.getLogger(__name__)


@dataclass
class ChannelCreateData:
    name: str
    code: str
    category: str
    cost_per_resume: Decimal = 0
    cost_per_hire: Decimal = 0
    contact_name: str = ''
    contact_phone: str = ''


class ChannelService:
    @staticmethod
    def create_channel(data: ChannelCreateData) -> Channel:
        channel = Channel.objects.create(
            name=data.name,
            code=data.code,
            category=data.category,
            cost_per_resume=data.cost_per_resume,
            cost_per_hire=data.cost_per_hire,
            contact_name=data.contact_name,
            contact_phone=data.contact_phone,
        )
        return channel

    @staticmethod
    def add_cost(
        channel_id: str,
        amount: Decimal,
        cost_type: str,
        description: str,
        incurred_at: str,
    ) -> ChannelCost:
        try:
            channel = Channel.objects.get(id=channel_id)
        except Channel.DoesNotExist as e:
            raise NotFound(f'渠道 {channel_id} 不存在') from e

        cost = ChannelCost.objects.create(
            channel=channel,
            amount=amount,
            cost_type=cost_type,
            description=description,
            incurred_at=incurred_at,
        )
        # 更新渠道总成本
        total = channel.costs.aggregate(s=Sum('amount'))['s'] or 0
        channel.total_cost = total
        channel.save(update_fields=['total_cost'])
        return cost

    @staticmethod
    def get_roi(channel_id: str) -> dict:
        """计算渠道 ROI：投递人数 / 入职人数 / 总成本 / 单入职成本"""
        from apps.candidate.models import Candidate
        try:
            channel = Channel.objects.get(id=channel_id)
        except Channel.DoesNotExist as e:
            raise NotFound(f'渠道 {channel_id} 不存在') from e

        candidates_count = Candidate.objects.filter(
            source_channel_id=channel_id, deleted_at__isnull=True,
        ).count()
        hired_count = Candidate.objects.filter(
            source_channel_id=channel_id,
            current_state='ONBOARDED',
            deleted_at__isnull=True,
        ).count()
        total_cost = channel.total_cost
        cost_per_hire = (total_cost / hired_count) if hired_count > 0 else 0
        return {
            'channel_id': channel_id,
            'channel_name': channel.name,
            'candidates_count': candidates_count,
            'hired_count': hired_count,
            'total_cost': float(total_cost),
            'cost_per_hire': float(cost_per_hire),
            'roi': float(hired_count) / float(total_cost) if total_cost > 0 else 0,
        }
