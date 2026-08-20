"""人员比例管控系统 v2 — 视图与 API 端点（均挂在 /api/v1/campus/ 下）。

端点：
  GET    /scopes/                  适用范围列表
  POST   /scopes/                  新建适用范围
  GET/PUT/DELETE /scopes/{id}/
  GET    /dimensions/              维度列表
  POST   /dimensions/              新建维度
  GET/PUT/DELETE /dimensions/{id}/
  GET    /indicators/?dimension=   指标列表（可按维度过滤）
  POST   /indicators/              新建指标
  GET/PUT/DELETE /indicators/{id}/
  GET    /rules/?scope=            规则列表（按适用范围）
  POST   /rules/                   新建规则（含 100% 硬校验）
  GET/PUT/DELETE /rules/{id}/
  GET    /rules/ratio/?scope=      实时看板比例（compute_ratio，scope 感知）
  GET    /rules/plan/?scope=&year=&month=   人数规划 + KPI
  POST   /rules/validate/?scope=&year=       录入校验（simulate，服务端重算）
  GET    /headcounts/?scope=&year= 人数目标列表（指标层）
  POST   /headcounts/              新建/编辑人数目标
  GET/PUT/DELETE /headcounts/{id}/
"""
from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination

from .calc import compute_ratio, compute_count, kpi, simulate, check_dimension_sums
from .constants import STRENGTH
from .models import (
    ControlScope, ControlDimension, ControlIndicator, ControlRule, ControlHeadcount, Person,
)
from .serializers import (
    ControlScopeSerializer, ControlDimensionSerializer, ControlIndicatorSerializer,
    ControlRuleSerializer, ControlHeadcountSerializer, PersonSerializer, _to_decimal,
)


def _jsonify(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


def _scope_to_dict(s):
    return {'bu': s.bu, 'position': s.position or '', 'level': s.level or ''}


def _rule_to_dict(r):
    return {
        'scope_id': r.scope_id,
        'dimension': r.dimension.name,
        'indicator': r.indicator.name,
        'target': float(r.target),
        'lo': float(r.lo),
        'hi': float(r.hi),
        'strength': r.strength,
    }


def _person_to_dict(p):
    return {
        'bu': p.bu,
        'school': p.school,
        'sex': p.sex,
        'major': p.major,
        'month': p.month,
        'status': p.status,
        'counted': p.counted,
        'position': p.position or '',
        'level': p.level or '',
    }


def _headcount_to_dict(h):
    return {
        'scope_id': h.scope_id,
        'indicator': h.indicator.name,
        'dimension': h.indicator.dimension.name,
        'year': h.year,
        'annual_target': h.annual_target,
        'monthly_targets': list(h.monthly_targets) if isinstance(h.monthly_targets, (list, tuple)) else [0] * 12,
    }


class CampusCRUDMixin:
    """写操作统一兜底：带入当前用户；硬删（instance.delete）。"""

    def perform_create(self, serializer):
        try:
            serializer.save(created_by=self.request.user, updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})

    def perform_update(self, serializer):
        try:
            serializer.save(updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})

    def perform_destroy(self, instance):
        instance.delete()


class ControlScopeViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlScope.objects.all()
    serializer_class = ControlScopeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination


class ControlDimensionViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlDimension.objects.all()
    serializer_class = ControlDimensionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination


class ControlIndicatorViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlIndicator.objects.all()
    serializer_class = ControlIndicatorSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ControlIndicator.objects.all()
        dim = self.request.query_params.get('dimension')
        if dim:
            qs = qs.filter(dimension_id=dim)
        return qs


class ControlRuleViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlRule.objects.all()
    serializer_class = ControlRuleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ControlRule.objects.all()
        scope = self.request.query_params.get('scope')
        if scope:
            qs = qs.filter(scope_id=scope)
        return qs

    def _load_scope(self, scope_id):
        scope = ControlScope.objects.filter(pk=scope_id).first()
        if not scope:
            return None
        rules = [_rule_to_dict(r) for r in ControlRule.objects.filter(scope_id=scope_id)]
        persons = [_person_to_dict(p) for p in Person.objects.filter()]
        headcounts = [_headcount_to_dict(h) for h in ControlHeadcount.objects.filter(scope_id=scope_id)]
        return scope, rules, persons, headcounts

    @action(detail=False, methods=['get'], url_path='ratio')
    def ratio(self, request):
        scope_id = request.query_params.get('scope')
        if not scope_id:
            return Response({'success': False, 'detail': '缺少 scope 参数'}, status=400)
        scope = ControlScope.objects.filter(pk=scope_id).first()
        if not scope:
            return Response({'success': False, 'detail': '适用范围不存在'}, status=404)
        rules = [_rule_to_dict(r) for r in ControlRule.objects.filter(scope_id=scope_id)]
        persons = [_person_to_dict(p) for p in Person.objects.filter()]
        result = compute_ratio(persons, rules, _scope_to_dict(scope))
        # 100% 加和校验概览
        sums = check_dimension_sums(rules, scope_id)
        return Response({
            'success': True,
            'data': {
                'total': result['total'],
                'rows': _jsonify(result['rows']),
                'sumChecks': _jsonify(sums),
            },
        })

    @action(detail=False, methods=['get'], url_path='plan')
    def plan(self, request):
        scope_id = request.query_params.get('scope')
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        if not scope_id:
            return Response({'success': False, 'detail': '缺少 scope 参数'}, status=400)
        if not month:
            return Response({'success': False, 'detail': '缺少 month 参数'}, status=400)
        scope = ControlScope.objects.filter(pk=scope_id).first()
        if not scope:
            return Response({'success': False, 'detail': '适用范围不存在'}, status=404)
        rules = [_rule_to_dict(r) for r in ControlRule.objects.filter(scope_id=scope_id)]
        persons = [_person_to_dict(p) for p in Person.objects.filter()]
        headcounts = [_headcount_to_dict(h) for h in ControlHeadcount.objects.filter(scope_id=scope_id)]
        if not year:
            year = headcounts[0]['year'] if headcounts else None
        year = int(year) if year else 2026
        rows = compute_count(persons, rules, headcounts, _scope_to_dict(scope), year, month)
        k = kpi(persons, rules, headcounts, _scope_to_dict(scope), year, month)
        return Response({
            'success': True,
            'data': {'rows': _jsonify(rows), 'kpi': _jsonify(k), 'year': year},
        })

    @action(detail=False, methods=['post'], url_path='validate')
    def validate(self, request):
        scope_id = request.query_params.get('scope')
        year = request.query_params.get('year')
        if not scope_id:
            return Response({'success': False, 'detail': '缺少 scope 参数'}, status=400)
        scope = ControlScope.objects.filter(pk=scope_id).first()
        if not scope:
            return Response({'success': False, 'detail': '适用范围不存在'}, status=404)
        draft = request.data or {}
        required = ['school', 'sex', 'major']
        missing = [k for k in required if not draft.get(k)]
        if missing:
            return Response({'success': False, 'detail': f'缺少字段：{",".join(missing)}'}, status=400)
        rules = [_rule_to_dict(r) for r in ControlRule.objects.filter(scope_id=scope_id)]
        persons = [_person_to_dict(p) for p in Person.objects.filter()]
        headcounts = [_headcount_to_dict(h) for h in ControlHeadcount.objects.filter(scope_id=scope_id)]
        if not year:
            year = headcounts[0]['year'] if headcounts else 2026
        year = int(year) if year else 2026
        result = simulate(draft, rules, persons, headcounts, _scope_to_dict(scope), year, month=draft.get('month'))
        return Response({'success': True, 'data': _jsonify(result)})

    @action(detail=False, methods=['post'], url_path='batch')
    def batch(self, request):
        """批量保存某 (scope, dimension) 下全部规则（原子替换）。

        语义（q-2 / q-3）：一次提交该维度的完整指标集合，硬校验「目标占比加和 == 100%」，
        不等于 100% 直接 400 拦截；通过则在事务内删除旧规则并重建。
        """
        scope_id = request.data.get('scope')
        dimension_id = request.data.get('dimension')
        rules = request.data.get('rules')
        if not scope_id or not dimension_id:
            return Response({'success': False, 'detail': '缺少 scope/dimension 参数'}, status=400)
        scope = ControlScope.objects.filter(pk=scope_id).first()
        dimension = ControlDimension.objects.filter(pk=dimension_id).first()
        if not scope or not dimension:
            return Response({'success': False, 'detail': '适用范围或维度不存在'}, status=404)
        if not isinstance(rules, list) or not rules:
            return Response({'success': False, 'detail': 'rules 不能为空'}, status=400)

        total = Decimal('0')
        prepared = []
        seen = set()
        for r in rules:
            if not isinstance(r, dict):
                return Response({'success': False, 'detail': 'rules 项须为对象'}, status=400)
            indicator_id = r.get('indicator')
            indicator = ControlIndicator.objects.filter(pk=indicator_id, dimension_id=dimension_id).first()
            if not indicator:
                return Response({'success': False, 'detail': f'指标 {indicator_id} 不属于该维度'}, status=400)
            if indicator_id in seen:
                return Response({'success': False, 'detail': f'指标 {indicator.name} 重复提交'}, status=400)
            target = _to_decimal(r.get('target'))
            lo = _to_decimal(r.get('lo'))
            hi = _to_decimal(r.get('hi'))
            strength = r.get('strength', '硬约束')
            if None in (target, lo, hi):
                return Response({'success': False, 'detail': f'指标 {indicator.name} 目标/下限/上限必填且为数值'}, status=400)
            if not (Decimal('0') <= lo <= target <= hi <= Decimal('1')):
                return Response({'success': False, 'detail': f'指标 {indicator.name} 需满足 0<=下限<=目标<=上限<=1'}, status=400)
            if strength not in STRENGTH:
                return Response({'success': False, 'detail': f'控制强度非法：{strength}'}, status=400)
            total += target
            prepared.append((indicator, target, lo, hi, strength))
            seen.add(indicator_id)

        if abs(total - Decimal('1')) > Decimal('0.0001'):
            pct = (total * 100).quantize(Decimal('0.01'))
            return Response({
                'success': False,
                'detail': f'该维度下所有指标目标占比之和须为 100%，当前为 {pct}%',
            }, status=400)

        with transaction.atomic():
            ControlRule.objects.filter(scope=scope, dimension=dimension).delete()
            for indicator, target, lo, hi, strength in prepared:
                ControlRule.objects.create(
                    scope=scope, dimension=dimension, indicator=indicator,
                    target=target, lo=lo, hi=hi, strength=strength,
                    created_by=request.user, updated_by=request.user,
                )
        return Response({'success': True, 'data': {'saved': len(prepared)}})


class ControlHeadcountViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlHeadcount.objects.all()
    serializer_class = ControlHeadcountSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ControlHeadcount.objects.all()
        scope = self.request.query_params.get('scope')
        year = self.request.query_params.get('year')
        if scope:
            qs = qs.filter(scope_id=scope)
        if year:
            qs = qs.filter(year=year)
        return qs


class PersonViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    """人员主数据 CRUD（全局主数据，一行一人；counted 控制是否计入核算）。"""

    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
