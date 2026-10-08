"""全局统一搜索端点 (Plan P) — GET /api/v1/search/

前端 ``web/app/src/components/common/GlobalSearch.vue`` 与
``web/app/src/api/search.ts`` 调用的全局搜索后端实现。此前后端缺失
(前端 ``GET /search/`` 一直 404)，本视图补齐，让全局搜索真正可用。

契约要点 (已与前端 GlobalSearch 核对):
- 鉴权: ``IsAuthenticated``
- 入参 (query params): ``q``(必填), ``types``(可选, 逗号分隔子集,
  candidate/demand/position/interview/offer/referral), ``limit``(默认 5)
- 响应: 裸 JSON (无项目标准 envelope)。全局 ``CamelCaseJSONRenderer`` 会把
  snake_case 字典键自动转驼峰 (``total_groups``→``totalGroups``、
  ``scheduled_at``→``scheduledAt``、``candidate_name``→``candidateName``、
  ``real_name``→``realName`` 等)。本模块直接返回 snake_case，渲染交给框架。

字段映射 (模型字段 → 输出字段):
- demand / position / offer 的模型状态字段叫 ``state`` (FSM)，输出时映射为 ``status``
- position 模型字段 ``title`` 输出为 ``name``
- referral 无 ``candidate_name`` 字段，用 ``obj.candidate.name`` 输出
- referral.referrer (User) 无 ``real_name`` 字段，用 ``obj.referrer.full_name`` 输出
- candidate.phone 经 ``mask_phone`` 脱敏
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from django.db.models import Q
from django.db.models.query import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.candidate.models import Candidate
from apps.common.masking import mask_phone
from apps.common.response import success_response
from apps.demand.models import Demand
from apps.interview.models import Interview
from apps.offer.models import Offer
from apps.position.models import Position
from apps.referral.models import Referral


# ---------------------------------------------------------------------------
# 序列化辅助函数 (每个实体一个)
# 输出契约要求的字段；关联对象缺失时用 None (前端有 ?. 保护)。
# ---------------------------------------------------------------------------
def _serialize_candidate(obj: Candidate) -> Dict[str, Any]:
    """候选人: id, name, phone(脱敏), position:{name}."""
    application = obj.applications.first()
    position = application.position if application else None
    return {
        'id': str(obj.id),
        'name': obj.name,
        'phone': mask_phone(obj.phone),
        'position': {'name': position.title if position else None},
    }


def _serialize_demand(obj: Demand) -> Dict[str, Any]:
    """招聘需求: id, title, status(来自 state), department:{name}."""
    return {
        'id': str(obj.id),
        'title': obj.title,
        'status': obj.state,  # 模型字段 state (FSM) → 输出 status
        'department': {'name': obj.department.name if obj.department else None},
    }


def _serialize_position(obj: Position) -> Dict[str, Any]:
    """职位: id, name(来自 title), status(来自 state), department:{name}."""
    return {
        'id': str(obj.id),
        'name': obj.title,  # 模型字段 title → 输出 name
        'status': obj.state,  # 模型字段 state → 输出 status
        'department': {'name': obj.department.name if obj.department else None},
    }


def _serialize_interview(obj: Interview) -> Dict[str, Any]:
    """面试: id, scheduledAt(ISO, 来自 scheduled_at), candidate:{name}, position:{name}."""
    application = obj.application
    candidate = application.candidate if application else None
    position = application.position if application else None
    return {
        'id': str(obj.id),
        'scheduled_at': obj.scheduled_at.isoformat() if obj.scheduled_at else None,
        'candidate': {'name': candidate.name if candidate else None},
        'position': {'name': position.title if position else None},
    }


def _serialize_offer(obj: Offer) -> Dict[str, Any]:
    """Offer: id, status(来自 state), candidate:{name}, position:{name}."""
    return {
        'id': str(obj.id),
        'status': obj.state,  # 模型字段 state → 输出 status
        'candidate': {'name': obj.candidate.name if obj.candidate else None},
        'position': {'name': obj.position.title if obj.position else None},
    }


def _serialize_referral(obj: Referral) -> Dict[str, Any]:
    """推荐: id, candidateName(来自 candidate.name), referrer:{realName}(来自 referrer.full_name)."""
    return {
        'id': str(obj.id),
        # referral 无 candidate_name 字段, 用 obj.candidate.name
        'candidate_name': obj.candidate.name if obj.candidate else None,
        # User 模型无 real_name 字段, 用 obj.referrer.full_name 输出为 real_name
        'referrer': {
            'real_name': obj.referrer.full_name if obj.referrer else None,
        },
    }


# ---------------------------------------------------------------------------
# 每个实体的查询构造 (软删过滤 deleted_at__isnull=True + 关联预取避免 N+1)
# 与 Q 过滤 (icontains OR 组合)
# ---------------------------------------------------------------------------
def _candidate_queryset() -> QuerySet[Candidate]:
    return Candidate.objects.filter(
        deleted_at__isnull=True
    ).prefetch_related('applications__position')


def _demand_queryset() -> QuerySet[Demand]:
    return Demand.objects.filter(
        deleted_at__isnull=True
    ).select_related('department')


def _position_queryset() -> QuerySet[Position]:
    return Position.objects.filter(
        deleted_at__isnull=True
    ).select_related('department')


def _interview_queryset() -> QuerySet[Interview]:
    return Interview.objects.filter(
        deleted_at__isnull=True
    ).select_related('application__candidate', 'application__position')


def _offer_queryset() -> QuerySet[Offer]:
    return Offer.objects.filter(
        deleted_at__isnull=True
    ).select_related('candidate', 'position')


def _referral_queryset() -> QuerySet[Referral]:
    return Referral.objects.filter(
        deleted_at__isnull=True
    ).select_related('candidate', 'referrer', 'position')


def _candidate_filter(q: str) -> Q:
    return (
        Q(name__icontains=q)
        | Q(phone__icontains=q)
        | Q(email__icontains=q)
        | Q(current_position__icontains=q)
    )


def _demand_filter(q: str) -> Q:
    return (
        Q(title__icontains=q)
        | Q(position_title__icontains=q)
        | Q(department__name__icontains=q)
    )


def _position_filter(q: str) -> Q:
    return (
        Q(title__icontains=q)
        | Q(position_title__icontains=q)
        | Q(department__name__icontains=q)
    )


def _interview_filter(q: str) -> Q:
    return (
        Q(application__candidate__name__icontains=q)
        | Q(application__position__title__icontains=q)
        | Q(code__icontains=q)
    )


def _offer_filter(q: str) -> Q:
    return (
        Q(candidate__name__icontains=q)
        | Q(position__title__icontains=q)
        | Q(position_title__icontains=q)
    )


def _referral_filter(q: str) -> Q:
    return (
        Q(candidate__name__icontains=q)
        | Q(referrer__username__icontains=q)
    )


# 搜索配置表: 每项含 type / queryset_builder / q_filter_builder / serialize_fn
SEARCHERS: List[Dict[str, Any]] = [
    {
        'type': 'candidate',
        'queryset': _candidate_queryset,
        'filter': _candidate_filter,
        'serialize': _serialize_candidate,
    },
    {
        'type': 'demand',
        'queryset': _demand_queryset,
        'filter': _demand_filter,
        'serialize': _serialize_demand,
    },
    {
        'type': 'position',
        'queryset': _position_queryset,
        'filter': _position_filter,
        'serialize': _serialize_position,
    },
    {
        'type': 'interview',
        'queryset': _interview_queryset,
        'filter': _interview_filter,
        'serialize': _serialize_interview,
    },
    {
        'type': 'offer',
        'queryset': _offer_queryset,
        'filter': _offer_filter,
        'serialize': _serialize_offer,
    },
    {
        'type': 'referral',
        'queryset': _referral_queryset,
        'filter': _referral_filter,
        'serialize': _serialize_referral,
    },
]

VALID_TYPES: set = {s['type'] for s in SEARCHERS}


class SearchAPIView(APIView):
    """全局统一搜索.

    GET /api/v1/search/?q=<query>&types=candidate,demand&limit=5

    响应 (裸 JSON, 无 envelope):
    {
      "query": "<原 q>",
      "took": <毫秒整数>,
      "totalGroups": <有结果的组数>,
      "groups": [ { "type": ..., "total": <匹配总数>, "items": [...] }, ... ]
    }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs) -> Response:
        start = time.perf_counter()
        raw_q = request.query_params.get('q') or ''
        q = raw_q.strip()

        # 空 query 直接返回空结果 (took 记为 0); query 回显原始值
        if not q:
            return success_response({
                'query': raw_q,
                'took': 0,
                'total_groups': 0,
                'groups': [],
            })

        # 解析 types 子集 (可选, 只保留合法值)
        raw_types = request.query_params.get('types')
        if raw_types:
            requested = [t.strip() for t in raw_types.split(',') if t.strip()]
            requested = [t for t in requested if t in VALID_TYPES]
            searchers = [s for s in SEARCHERS if s['type'] in requested]
        else:
            searchers = list(SEARCHERS)

        # 解析 limit (默认 5, 非法/负数回落 5)
        try:
            limit = int(request.query_params.get('limit', 5))
        except (TypeError, ValueError):
            limit = 5
        if limit <= 0:
            limit = 5

        groups: List[Dict[str, Any]] = []
        for s in searchers:
            qs = s['queryset']().filter(s['filter'](q))
            total = qs.count()  # 未截断的匹配总数
            items = [s['serialize'](obj) for obj in qs[:limit]]  # 截断到 limit
            groups.append({
                'type': s['type'],
                'total': total,
                'items': items,
            })

        # totalGroups = 有结果 (items 非空) 的组数
        total_groups = sum(1 for g in groups if g['items'])
        took = int((time.perf_counter() - start) * 1000)

        return success_response({
            'query': raw_q,
            'took': took,
            'total_groups': total_groups,
            'groups': groups,
        })
