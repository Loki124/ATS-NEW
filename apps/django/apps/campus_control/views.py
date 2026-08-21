"""人员比例管控系统 v2.1 — 视图与 API 端点（均挂在 /api/v1/campus/ 下）。

端点：
  GET    /dimensions/              维度列表
  POST   /dimensions/              新建维度
  GET/PUT/DELETE /dimensions/{id}/
  GET    /indicators/?dimension=   指标列表（可按维度过滤）
  POST   /indicators/              新建指标
  GET/PUT/DELETE /indicators/{id}/
  GET    /rules/?bu=&position=&level=       规则列表（按适用范围过滤）
  POST   /rules/                   新建规则（单条仅拦溢出）
  PUT/DELETE /rules/{id}/
  GET    /rules/ratio/?bu=&position=&level=       实时看板（适用范围过滤）
  GET    /rules/plan/?bu=&position=&level=&year=&month=   人数规划
  POST   /rules/validate/?year=    录入校验（draft 含 bu/position/level）
  POST   /rules/batch/             批量保存某适用范围+维度的全部规则（100% 硬校验）
  GET    /headcounts/?bu=&position=&level=&year=  人数目标列表
  POST   /headcounts/              新建/编辑人数目标
  GET/PUT/DELETE /headcounts/{id}/
  GET    /persons/                 人员主数据
  POST/PUT/DELETE /persons/{id}/
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db import IntegrityError, transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination

from .calc import compute_ratio, compute_count, kpi, simulate, check_dimension_sums, distinct_scope_keys
from .constants import STRENGTH
from .models import (
    ControlDimension, ControlIndicator, ControlRule, ControlHeadcount, Person,
)
from .serializers import (
    ControlDimensionSerializer, ControlIndicatorSerializer,
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


def _rule_to_dict(r):
    return {
        'bu': r.bu or '',
        'position': r.position or '',
        'level': r.level or '',
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
        'bu': h.bu or '',
        'position': h.position or '',
        'level': h.level or '',
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
        bu = self.request.query_params.get('bu')
        position = self.request.query_params.get('position')
        level = self.request.query_params.get('level')
        if bu is not None:
            qs = qs.filter(bu=bu)
        if position is not None:
            qs = qs.filter(position=position)
        if level is not None:
            qs = qs.filter(level=level)
        return qs

    @action(detail=False, methods=['get'], url_path='ratio')
    def ratio(self, request):
        """实时看板：展示全部规则（每条按自身适用范围独立计算）+ 各适用范围的 100% 加和。"""
        rules = [_rule_to_dict(r) for r in ControlRule.objects.all()]
        persons = [_person_to_dict(p) for p in Person.objects.all()]
        result = compute_ratio(persons, rules)
        sums = []
        for sk in distinct_scope_keys(rules):
            for s in check_dimension_sums(rules, sk):
                sums.append({'bu': sk[0], 'position': sk[1], 'level': sk[2], **s})
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
        """人数规划：展示全部目标（每条按自身适用范围独立计算）。"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        if not month:
            return Response({'success': False, 'detail': '缺少 month 参数'}, status=400)
        rules = [_rule_to_dict(r) for r in ControlRule.objects.all()]
        persons = [_person_to_dict(p) for p in Person.objects.all()]
        headcounts = [_headcount_to_dict(h) for h in ControlHeadcount.objects.all()]
        year = int(year) if year else 2026
        rows = compute_count(persons, rules, headcounts, year, month)
        k = kpi(persons, rules, headcounts, year, month)
        return Response({
            'success': True,
            'data': {'rows': _jsonify(rows), 'kpi': _jsonify(k), 'year': year},
        })

    @action(detail=False, methods=['post'], url_path='validate')
    def validate(self, request):
        draft = request.data or {}
        required = ['bu', 'school', 'sex', 'major']
        missing = [k for k in required if not draft.get(k)]
        if missing:
            return Response({'success': False, 'detail': f'缺少字段：{",".join(missing)}'}, status=400)
        rules = [_rule_to_dict(r) for r in ControlRule.objects.all()]
        persons = [_person_to_dict(p) for p in Person.objects.all()]
        headcounts = [_headcount_to_dict(h) for h in ControlHeadcount.objects.all()]
        year = request.query_params.get('year')
        year = int(year) if year else 2026
        result = simulate(draft, rules, persons, headcounts, year, month=draft.get('month'))
        return Response({'success': True, 'data': _jsonify(result)})

    @action(detail=False, methods=['post'], url_path='batch')
    def batch(self, request):
        """批量保存某 (bu, position, level, dimension) 下全部规则（原子替换）。

        硬校验「目标占比加和 == 100%」，不等于 100% 直接 400；通过则事务内删除旧规则重建。
        """
        bu = request.data.get('bu', '') or ''
        position = request.data.get('position', '') or ''
        level = request.data.get('level', '') or ''
        dimension_id = request.data.get('dimension')
        rules = request.data.get('rules')
        if not dimension_id:
            return Response({'success': False, 'detail': '缺少 dimension 参数'}, status=400)
        dimension = ControlDimension.objects.filter(pk=dimension_id).first()
        if not dimension:
            return Response({'success': False, 'detail': '维度不存在'}, status=404)
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
                'detail': f'该适用范围下此维度指标目标占比之和须为 100%，当前为 {pct}%',
            }, status=400)

        with transaction.atomic():
            ControlRule.objects.filter(bu=bu, position=position, level=level, dimension=dimension).delete()
            for indicator, target, lo, hi, strength in prepared:
                ControlRule.objects.create(
                    bu=bu, position=position, level=level, dimension=dimension, indicator=indicator,
                    target=target, lo=lo, hi=hi, strength=strength,
                    created_by=request.user, updated_by=request.user,
                )
        return Response({'success': True, 'data': {'saved': len(prepared)}})

    @action(detail=False, methods=['post'], url_path='with-targets')
    def with_targets(self, request):
        """批量配置规则 + 人数目标（一次性原子操作）。

        入参: { bu, position, level, dimension, year, totalTarget, rules: [{indicator, target, lo, hi, strength}] }
        行为:
          - 校验 100% 加和 + 0<=lo<=target<=hi<=1 + indicator∈dimension
          - 事务内: 删除该(适用范围, 维度)旧规则 → 创建新规则
          - 为每条规则 upsert headcount(annual=round(totalTarget×target), monthly 留 0，保留 created_by)
        """
        bu = request.data.get('bu', '') or ''
        position = request.data.get('position', '') or ''
        level = request.data.get('level', '') or ''
        dimension_id = request.data.get('dimension')
        year_in = request.data.get('year')
        total_target_in = request.data.get('total_target')
        rules_in = request.data.get('rules')

        if not dimension_id:
            return Response({'success': False, 'detail': '缺少 dimension 参数'}, status=400)
        dimension = ControlDimension.objects.filter(pk=dimension_id).first()
        if not dimension:
            return Response({'success': False, 'detail': '维度不存在'}, status=404)
        try:
            year = int(year_in)
        except (TypeError, ValueError):
            return Response({'success': False, 'detail': 'year 必填且为整数'}, status=400)
        try:
            total_target = int(total_target_in)
        except (TypeError, ValueError):
            return Response({'success': False, 'detail': 'totalTarget 必填且为非负整数'}, status=400)
        if total_target < 0:
            return Response({'success': False, 'detail': 'totalTarget 不能为负数'}, status=400)
        if not isinstance(rules_in, list) or not rules_in:
            return Response({'success': False, 'detail': 'rules 不能为空'}, status=400)

        total = Decimal('0')
        prepared = []
        seen = set()
        for r in rules_in:
            if not isinstance(r, dict):
                return Response({'success': False, 'detail': 'rules 项须为对象'}, status=400)
            indicator_id = r.get('indicator')
            if indicator_id in seen:
                return Response({'success': False, 'detail': f'指标 {indicator_id} 重复提交'}, status=400)
            seen.add(indicator_id)
            indicator = ControlIndicator.objects.filter(pk=indicator_id, dimension_id=dimension_id).first()
            if not indicator:
                return Response({'success': False, 'detail': f'指标 {indicator_id} 不属于该维度'}, status=400)
            target = _to_decimal(r.get('target'))
            lo = _to_decimal(r.get('lo'))
            hi = _to_decimal(r.get('hi'))
            strength = r.get('strength', '硬约束')
            if None in (target, lo, hi):
                return Response({'success': False, 'detail': f'指标 {indicator.name} 目标/下限/上限必填且为数值'}, status=400)
            if not (Decimal('0') <= lo <= target <= hi <= Decimal('1')):
                return Response({'success': False, 'detail': f'指标 {indicator.name} 需满足 0<=下限<=目标<=上限<=1'}, status=400)
            if strength not in STRENGTH:
                return Response({'success': False, 'detail': f'指标 {indicator.name} 控制强度非法'}, status=400)
            total += target
            prepared.append((indicator, target, lo, hi, strength))

        if abs(total - Decimal('1')) > Decimal('0.0001'):
            pct = (total * 100).quantize(Decimal('0.01'))
            return Response({
                'success': False,
                'detail': f'该维度下所有指标目标占比之和须为 100%，当前为 {pct}%',
            }, status=400)

        with transaction.atomic():
            # 删除该 (适用范围, 维度) 旧规则
            ControlRule.objects.filter(bu=bu, position=position, level=level, dimension=dimension).delete()
            indicator_ids = []
            for indicator, target, lo, hi, strength in prepared:
                ControlRule.objects.create(
                    bu=bu, position=position, level=level, dimension=dimension, indicator=indicator,
                    target=target, lo=lo, hi=hi, strength=strength,
                    created_by=request.user, updated_by=request.user,
                )
                indicator_ids.append(indicator.id)
            # upsert headcount (annual = totalTarget * target，monthly 留 0，保留 created_by)
            existing_hcs = {
                (h.indicator_id, h.year): h for h in ControlHeadcount.objects.filter(
                    bu=bu, position=position, level=level, indicator_id__in=indicator_ids, year=year,
                )
            }
            for indicator, target, lo, hi, strength in prepared:
                annual = int((Decimal(str(total_target)) * target).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
                key = (indicator.id, year)
                if key in existing_hcs:
                    hc = existing_hcs[key]
                    hc.annual_target = annual
                    hc.monthly_targets = [0]*12
                    hc.updated_by = request.user
                    hc.save()
                else:
                    ControlHeadcount.objects.create(
                        bu=bu, position=position, level=level, indicator=indicator, year=year,
                        annual_target=annual, monthly_targets=[0]*12,
                        created_by=request.user, updated_by=request.user,
                    )
        return Response({
            'success': True,
            'data': {'saved': len(prepared), 'totalTarget': total_target, 'year': year},
        })


class ControlHeadcountViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlHeadcount.objects.all()
    serializer_class = ControlHeadcountSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ControlHeadcount.objects.all()
        bu = self.request.query_params.get('bu')
        position = self.request.query_params.get('position')
        level = self.request.query_params.get('level')
        year = self.request.query_params.get('year')
        if bu is not None:
            qs = qs.filter(bu=bu)
        if position is not None:
            qs = qs.filter(position=position)
        if level is not None:
            qs = qs.filter(level=level)
        if year:
            qs = qs.filter(year=year)
        return qs


class PersonViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    """人员主数据 CRUD（全局主数据，一行一人；counted 控制是否计入核算）。"""

    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
